#!/usr/bin/env python

from __future__ import print_function

import time
import os.path as P
import os
import tempfile
import re
import errno
import shutil
import logging
import itertools
from os import makedirs, remove, listdir, chmod
from optparse import OptionParser
from collections import namedtuple
from subprocess import Popen, PIPE
from glob import glob
from BinaryBuilder import get_platform, tweak_path
from tempfile import NamedTemporaryFile

# These are the SONAMES for libs we're allowed to get from the base system
# (most of these are frameworks, and therefore lack a dylib/so)
LIB_SYSTEM_LIST = '''
    AGL
    Accelerate
    AppKit
    ApplicationServices
    Carbon
    Cocoa
    CoreFoundation
    CoreServices
    GLUT
    OpenGL
    QuickTime
    vecLib

    libobjc.A.dylib
    libSystem.B.dylib

    libGL.so.1
    libGLU.so.1
    libICE.so.6
    libSM.so.6
    libX11.so.6
    libXext.so.6
    libXi.so.6
    libXmu.so.6
    libXrandr.so.2
    libXt.so.6
    libc.so.6
    libdl.so.2
    libglut.so.3
    libm.so.6
    libpthread.so.0
    librt.so.1
'''.split()

# prefixes of libs that we always ship
LIB_SHIP_PREFIX = '''
    libstdc++.
    libgcc_s.
'''.split()

logger = None
def setup_logging(level = logging.DEBUG):
    global logger
    logger = logging.getLogger('make-dist')
    logger.setLevel(level)
    ch = logging.StreamHandler()
    ch.setLevel(level)
    #ch.setFormatter(logging.Formatter("MMOO %(message)s"))
    logger.addHandler(ch)

def tarball_name():
    arch = get_platform()
    if opt.version is not None:
        return 'StereoPipeline-%s-%s-%s' % (opt.version, arch.machine, arch.prettyos)
    else:
        return 'StereoPipeline-%s-%s-%s' % (arch.machine, arch.prettyos, time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime()))

def run(*args, **kw):
    need_output = kw.pop('output', False)
    logger.debug('run: [%s]' % ' '.join(args))
    kw['stdout'] = PIPE
    p = Popen(args, **kw)
    ret = p.communicate()[0]
    if p.returncode != 0:
        raise Exception('%s: command returned %d' % (args, p.returncode))
    if need_output and len(ret) == 0:
        raise Exception('%s: failed (no output)' % (args,))
    return ret

def readelf(filename):
    Ret = namedtuple('readelf', 'needed soname rpath')
    r = re.compile(' \((.*?)\).*\[(.*?)\]')
    needed = []
    soname = None
    rpath = []
    for line in run('readelf', '-d', filename, output=True).split('\n'):
        m = r.search(line)
        if m:
            if   m.group(1) == 'NEEDED': needed.append(m.group(2))
            elif m.group(1) == 'SONAME': soname = m.group(2)
            elif m.group(1) == 'RPATH' : rpath  = m.group(2).split(':')
    return Ret(needed, soname, rpath)

def ldd(filename):
    libs = {}
    r = re.compile('^\s*(\S+) => (\S+)')
    for line in run('ldd', filename, output=True).split('\n'):
        m = r.search(line)
        if m:
            libs[m.group(1)] = (None if m.group(2) == 'not' else m.group(2))
    return libs

def otool(filename):
    Ret = namedtuple('otool', 'soname sopath libs')
    r = re.compile('^\s*(\S+)')
    lines = run('otool', '-L', filename, output=True).split('\n')
    libs = {}
    soname = None
    sopath = None
    for i in range(1, len(lines)):
        m = r.search(lines[i])
        if m:
            if i == 1:
                sopath = m.group(1)
                soname = P.basename(sopath)
            else:
                libs[P.basename(m.group(1))] = m.group(1)
    return Ret(soname=soname, sopath=sopath, libs=libs)

def required_libs(filename):
    ''' Returns a dict where the keys are required SONAMEs and the values are proposed full paths. '''
    arch = get_platform()
    def linux():
        soname = set(readelf(filename).needed)
        return dict((k,v) for k,v in ldd(filename).iteritems() if k in soname)
    tool = dict(osx   = lambda: otool(filename).libs,
                linux = linux)
    return tool[arch.os]()

def is_binary(filename):
    ret = run('file', filename, output=True)
    return (ret.find('ELF') != -1) or (ret.find('Mach-O') != -1)

def grep(regex, filename):
    ret = []
    rx = re.compile(regex)
    with file(filename, 'r') as f:
        for line in f:
            m = rx.search(line)
            if m:
                ret.append(m)
    return ret

class Prefix(str):
    def __new__(cls, directory):
        return str.__new__(cls, P.normpath(directory))
    def base(self, *args):
        return P.join(self, *args)
    def __getattr__(self, name):
        def f(*args):
            args = [name] + list(args)
            return self.base(*args)
        return f

def rm_f(filename):
    ''' An rm that doesn't care if the file isn't there '''
    try:
        remove(filename)
    except OSError, o:
        if o.errno != errno.ENOENT: # Don't care if it wasn't there
            raise

def mkdir_f(dirname):
    ''' A mkdir -p that doesn't care if the dir is there '''
    try:
        makedirs(dirname)
    except OSError, o:
        if o.errno == errno.EEXIST and P.isdir(dirname):
            return
        raise

# Keep this in sync with the function in libexec-funcs.sh
def isis_version(isisroot):
    header = P.join(isisroot, 'src/base/objs/Constants/Constants.h')
    m = grep('version\("(.*?)"', header)
    if not m:
        raise Exception('Unable to locate ISIS version header (expected at %s). Perhaps your ISISROOT ($s) is incorrect?' % (header, isisroot))
    return m[0].group(1)

def mergetree(src, dst):
    """Merge one directory into another.

    The destination directory may already exist.
    If exception(s) occur, an Error is raised with a list of reasons.
    """
    if not P.exists(dst):
        makedirs(dst)
    errors = []
    for name in listdir(src):
        srcname = P.join(src, name)
        dstname = P.join(dst, name)
        try:
            if P.isdir(srcname):
                mergetree(srcname, dstname)
            else:
                copy(srcname, dstname)
        except shutil.Error, err:
            errors.extend(err.args[0])
        except EnvironmentError, why:
            errors.append((srcname, dstname, str(why)))
    try:
        shutil.copystat(src, dst)
    except OSError, why:
        errors.extend((src, dst, str(why)))
    if errors:
        raise shutil.Error, errors

INSTALLED = set()
def copy(src, dst):
    if P.isdir(dst):
        dst = P.join(dst, P.basename(src))

    logger.debug('%s -> %s' % (src, dst))

    #if hardlink:
    #    try:
    #        os.link(src, dst)
    #    except OSError, o:
    #        if o.errno != errno.EXDEV: # Invalid cross-device link
    #            raise
    #    else:
    #        assert dst not in INSTALLED, 'Added %s twice!' % dst
    #        INSTALLED.add(dst)
    #        return
    if P.islink(src):
        os.symlink(os.readlink(src), dst)
    else:
        shutil.copy2(src, dst)
    assert dst not in INSTALLED, 'Added %s twice!' % dst
    INSTALLED.add(dst)

def strip(filename):
    flags = None

    def linux(filename):
        typ = run('file', filename, output=True)
        if typ.find('current ar archive') != -1:
            return ['-g']
        elif typ.find('SB executable') != -1 or typ.find('SB shared object') != -1:
            save_elf_debug(filename)
            return ['--strip-unneeded', '-R', '.comment']
        elif typ.find('SB relocatable') != -1:
            return ['--strip-unneeded']
        return None
    def osx(filename):
        return ['-S']

    tool = dict(linux=linux, osx=osx)
    flags = tool[get_platform().os](filename)
    flags.append(filename)
    run('strip', *flags)


def save_elf_debug(filename):
    debug = '%s.debug' % filename
    try:
        run('objcopy', '--only-keep-debug', filename, debug)
        run('objcopy', '--add-gnu-debuglink=%s' % debug, filename)
    except Exception:
        logger.warning('Failed to split debug info for %s' % filename)
        if P.exists(debug):
            os.remove(debug)

def set_rpath(filename, toplevel, searchpath):
    pass
    # Relative path from the file to the top of the dist
    #rel_to_top = P.relpath(toplevel, filename)
    #search_from_top = map(lambda p: P.relpath(p, toplevel))

def bake(filename, toplevel, searchpath):
    set_rpath(filename, toplevel, searchpath)
    strip(filename)

def snap_symlinks(src):
    assert not P.isdir(src), 'Cannot chase symlinks on a directory'
    if not P.islink(src):
        return [src]
    return [src] + snap_symlinks(P.join(P.dirname(src), os.readlink(src)))

def copy_with_links(src, dst):
    assert P.isdir(dst), 'Destination must be a directory'
    for link in snap_symlinks(src):
        copy(link, dst)

def flatten(lol):
    return itertools.chain(*lol)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('--set-version', dest='version',   default=None, help='Set the version number to use for the generated tarball')
    parser.add_option('--coreutils',   dest='coreutils', default=None, help='Bin directory holding GNU coreutils')
    parser.add_option('--prefix',      dest='prefix',    default='/tmp/build/base/install', help='Root of the installed files')
    parser.add_option('--include',     dest='include',   default='./whitelist', help='A file that lists the binaries for the dist')
    parser.add_option('--debug',       dest='loglevel',  default=logging.INFO, action='store_const', const=logging.DEBUG, help='Turn on debug messages')

    global opt
    (opt, args) = parser.parse_args()

    setup_logging(opt.loglevel)

    tweak_path(opt.coreutils)

    BUILDNAME  = tarball_name()
    INSTALLDIR = Prefix(opt.prefix)
    DISTDIR    = Prefix(P.join(tempfile.mkdtemp(), BUILDNAME))
    ISISROOT   = P.join(P.dirname(INSTALLDIR.base()), 'isis') # sibling to INSTALLDIR
    SEARCHPATH = [P.join(ISISROOT, 'lib'), P.join(ISISROOT, '3rdParty', 'lib'), INSTALLDIR.lib()]

    deplist = dict()

    # Make all the output directories
    [makedirs(i) for i in DISTDIR.bin(), DISTDIR.lib(), DISTDIR.libexec()]

    print('Adding requested files')
    copy('libexec-funcs.sh', DISTDIR.libexec()) #XXX Don't depend on cwd
    with file(opt.include, 'r') as f:
        for line in f:
            relglob = line.strip()
            inpaths = glob(INSTALLDIR.base(relglob))
            assert len(inpaths) > 0, 'No matches for include list entry %s' % relglob
            inpaths = flatten([snap_symlinks(inpath) for inpath in inpaths])
            for inpath in inpaths:
                relpath = P.relpath(inpath, INSTALLDIR.base())
                if relpath.startswith('bin/'):
                    assert not P.islink(relpath), 'Cannot deal with sylinks in the bindir'
                    basename = P.basename(relpath)
                    outpath = DISTDIR.libexec(basename)
                    copy('libexec-helper.sh', DISTDIR.bin(basename)) #XXX Don't depend on cwd
                else:
                    outpath = DISTDIR.base(relpath)

                mkdir_f(P.dirname(outpath))
                copy(inpath, outpath)

                if is_binary(outpath):
                    deplist.update(required_libs(outpath))

    print('Adding ISIS version check')
    with file(DISTDIR.libexec('constants.sh'), 'w') as f:
        print('BAKED_ISIS_VERSION="%s"' % isis_version(ISISROOT), file=f)

    print('Adding libraries')
    print('\tRemoving system libs')
    # Remove the libs we definitely want from the system
    [deplist.pop(k, None) for k in LIB_SYSTEM_LIST]

    print('\tAdding forced-ship libraries')
    # Handle the shiplist separately
    for copy_lib in LIB_SHIP_PREFIX:
        found = None
        for soname in deplist.keys():
            if soname.startswith(copy_lib):
                found = soname
                break
        if found:
            copy_with_links(deplist[found], DISTDIR.lib())
            del deplist[found]

    print('\tFinding deps in search path')
    no_such_libs = []
    for lib in deplist:
        # We look for our deps in three places. Every library we need must be
        # in one of these three, or be on the whitelist. If we find it in the
        # install/lib dir, we copy it to the distdir
        for searchdir in SEARCHPATH:
            checklib = P.join(searchdir, lib)
            if P.exists(checklib):
                if searchdir == INSTALLDIR.lib():
                    copy_with_links(checklib, DISTDIR.lib())
                break
        else:
            no_such_libs.append(lib)

    if no_such_libs:
        raise Exception('Failed to find some libs in any of our dirs:\n\t%s' % '\n\t'.join(no_such_libs))

    #XXX Don't depend on cwd
    print('Adding files in dist-add')
    if P.exists('dist-add'): #XXX Don't depend on cwd
        mergetree('dist-add', DISTDIR.base())

    print('Adding docs')
    if P.exists(INSTALLDIR.doc()):
        mergetree(INSTALLDIR.doc(), DISTDIR)

    print('Baking RPATH and stripping binaries')
    for path in INSTALLED:
        if not is_binary(path): continue
        bake(path, DISTDIR, SEARCHPATH)

    print('Removing dotfiles from dist')
    [remove(i) for i in run('find', DISTDIR, '-name', '.*', '-print0').split('\0') if len(i) > 0 and i != '.' and i != '..']

    [chmod(file, 0755) for file in glob(DISTDIR.libexec('*')) + glob(DISTDIR.bin('*'))]

    DIST_PARENT = P.dirname(DISTDIR)

    debuglist = NamedTemporaryFile()

    run('find', BUILDNAME, '-name', '*.debug', '-fprint', debuglist.name, cwd=DIST_PARENT)

    print('Creating tarball %s.tar.gz' % BUILDNAME)
    run('tar', 'czf', '%s.tar.gz' % BUILDNAME, '-X', debuglist.name, '-C', DIST_PARENT, BUILDNAME)

    if P.getsize(debuglist.name) > 0:
        print('Creating debug tarball %s-debug.tar.gz' % BUILDNAME)
        run('tar', 'czf', '%s-debug.tar.gz' % BUILDNAME, '-T', debuglist.name, '-C', DIST_PARENT, BUILDNAME, '--no-recursion')


    #tar = tarfile.open('%s.tar.gz' % BUILDNAME, 'w:gz')
    #tar.add(DISTDIR.base(), exclude = lambda f: f.endswith('.debug'))
    #tar.close()

    #tar = tarfile.open('%s-debug.tar.gz' % BUILDNAME, 'w:gz')
    #tar.add(DISTDIR.base(), exclude = lambda f: not f.endswith('.debug'))
    #has_debug = len(tar.getnames()) > 0
    #tar.close()
    #if not has_debug:
    #    print('Removing debug tarball (no debug info found)')
    #    remove('%s-debug.tar.gz' % BUILDNAME)

