#!/bin/bash

from __future__ import print_function

import time
import os.path as P
import tempfile
import re
import errno
from shutil import copy2, copystat, Error
from os import makedirs, remove, listdir, chmod
from optparse import OptionParser
from collections import namedtuple
from subprocess import Popen, PIPE
from glob import glob
from BinaryBuilder import get_platform, tweak_path

# These are the SONAMES for libs we're allowed to get from the base system
# (most of these are frameworks, and therefore lack a dylib/so)
LIB_WHITELIST = '''
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
    libgcc_s.1.dylib
    libstdc++.6.dylib
'''.split()

def tarball_name():
    arch = get_platform()
    if opt.version is not None:
        return 'StereoPipeline-%s-%s-%s' % (opt.version, arch.machine, arch.prettyos)
    else:
        return 'StereoPipeline-%s-%s-%s' % (arch.machine, arch.prettyos, time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime()))

def run(*args, **kw):
    ret = Popen(args, stdout=PIPE).communicate()[0]
    if len(ret) == 0 and kw.get('need_output', True):
        raise Exception('%s: failed (no output)' % (args,))
    return ret

def readelf(filename):
    Ret = namedtuple('readelf', 'needed soname rpath')
    r = re.compile(' \((.*?)\).*\[(.*?)\]')
    needed = []
    soname = None
    rpath = []
    for line in run('readelf', '-d', filename).split('\n'):
        m = r.search(line)
        if m:
            if   m.group(1) == 'NEEDED': needed.append(m.group(2))
            elif m.group(1) == 'SONAME': soname = m.group(2)
            elif m.group(1) == 'RPATH' : rpath  = m.group(2).split(':')
    return Ret(needed, soname, rpath)

def ldd(filename):
    libs = {}
    r = re.compile('^\s*(\S+) => (\S+)')
    for line in run('ldd', filename).split('\n'):
        m = r.search(line)
        if m:
            libs[m.group(1)] = (None if m.group(2) == 'not' else m.group(2))
    return libs

def otool(filename):
    Ret = namedtuple('otool', 'soname sopath libs')
    r = re.compile('^\s*(\S+)')
    lines = run('otool', '-L', filename).split('\n')
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
    ''' Returns a list of required SONAMEs for the given binary '''
    arch = get_platform()
    tool = dict(osx   = lambda: otool(filename).libs.keys(),
                linux = lambda: readelf(filename).needed)
    return tool[arch.os]()

def grep(regex, filename):
    ret = []
    rx = re.compile(regex)
    with file(filename, 'r') as f:
        for line in f:
            m = rx.search(line)
            if m:
                ret.append(m)
    return ret

class Prefix(object):
    def __init__(self, directory):
        self._base = directory
    def base(self, *args):
        return P.normpath(P.join(self._base, *args))
    def bin(self, *args):
        args = ['bin'] + list(args)
        return self.base(*args)
    def lib(self, *args):
        args = ['lib'] + list(args)
        return self.base(*args)
    def libexec(self, *args):
        args = ['libexec'] + list(args)
        return self.base(*args)

def rm_f(filename):
    ''' An rm that doesn't care if the file isn't there '''
    try:
        remove(filename)
    except OSError, o:
        if o.errno != errno.ENOENT: # Don't care if it wasn't there
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
                copy2(srcname, dstname)
        except Error, err:
            errors.extend(err.args[0])
        except EnvironmentError, why:
            errors.append((srcname, dstname, str(why)))
    try:
        copystat(src, dst)
    except OSError, why:
        errors.extend((src, dst, str(why)))
    if errors:
        raise Error, errors


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('--set-version', dest='version',   default=None, help='Set the version number to use for the generated tarball')
    parser.add_option('--coreutils',   dest='coreutils', default=None, help='Bin directory holding GNU coreutils')
    parser.add_option('--prefix',      dest='prefix',    default='/tmp/build/base/install', help='Root of the installed files')
    parser.add_option('--include',     dest='include',   default='./whitelist', help='A file that lists the binaries for the dist')

    global opt
    (opt, args) = parser.parse_args()

    tweak_path(opt.coreutils)

    BUILDNAME  = tarball_name()
    INSTALLDIR = Prefix(opt.prefix)
    DISTDIR    = Prefix(P.join(tempfile.mkdtemp(), BUILDNAME))
    ISISROOT   = P.join(P.basename(INSTALLDIR.base()), 'isis') # sibling to INSTALLDIR

    liblist = set()

    # Make all the output directories
    [makedirs(i) for i in DISTDIR.bin(), DISTDIR.lib(), DISTDIR.libexec()]

    print('Adding binaries')
    copy2('libexec-funcs.sh', DISTDIR.libexec()) #XXX Don't depend on cwd
    with file(opt.include, 'r') as f:
        for binname in f:
            copy2(binname, DISTDIR.libexec())
            copy2('libexec-helper.sh', DISTDIR.bin(binname)) #XXX Don't depend on cwd
            [liblist.add(lib) for lib in required_libs(binname)]

    print('Adding ISIS version check')
    with file(DISTDIR.libexec('constants.sh')), 'w') as f:
        print('BAKED_ISIS_VERSION="%s"' % isis_version(ISISROOT), file=f)

    print('Adding libraries')
    # XXX Doesn't handle dlopen libs
    [liblist.remove(lib) for lib in LIB_WHITELIST]
    for lib in liblist:
        # We look for our deps in three places. Every library we need must be
        # in one of these three, or be on the whitelist. If we find it in the
        # install/lib dir, we copy it to the distdir
        ISISLIB      = P.join(ISISROOT, 'lib')
        ISIS3RDPARTY = P.join(ISISROOT, '3rdParty', 'lib')
        INSTALLLIB   = INSTALLDIR.lib()
        for searchdir in ISISLIB, ISIS3RDPARTY, INSTALLLIB:
            checklib = P.join(searchdir, lib)
            if P.exists(checklib):
                if searchdir == INSTALLLIB:
                    copy2(checklib, DISTDIR.lib())
                break
        else:
            raise Exception('Failed to find lib %s in any of our dirs' % lib)

    #XXX Don't depend on cwd
    print('Adding files in dist-add')
    if P.exists('dist-add'): #XXX Don't depend on cwd
        mergetree('dist-add', DISTDIR)

    print('Adding docs')
    mergetree(INSTALLDIR.doc(), DISTDIR)

    print('Removing dotfiles from dist')
    [remove(i) for i in run('find', DISTDIR, '-name', '.*', '-print0').split('\0') if len(i) > 0 and i != '.' and i != '..']

    [chmod(file, 755) for file in glob(DISTDIR.libexec('*')) + glob(DISTDIR.bin('*'))]

    print('Creating tarball %s.tar.gz' % BUILDNAME)
    tar = tarfile.open('%s.tar.gz' % BUILDNAME, 'w:gz')
    tar.add(DISTDIR.base(), exclude = lambda f: f.endswith('.debug'))
    tar.close()

    tar = tarfile.open('%s-debug.tar.gz' % BUILDNAME, 'w:gz')
    tar.add(DISTDIR.base(), exclude = lambda f: not f.endswith('.debug'))
    has_debug = len(tar.getnames()) > 0
    tar.close()
    if has_debug:
        print('Creating debug tarball %s-debug.tar.gz' % BUILDNAME)
    else:
        remove('%s-debug.tar.gz' % BUILDNAME)

'''
echo "Setting RPATH and stripping binaries"
for i in $olibexec/* $(find $olib -type f \( -name '*.dylib*' -o -name '*.so*' \) ); do
    if [[ -f $i ]]; then
        # root is the relative path from the object in question to the top of
        # the dist
        root="$(get_relative_path ${DIST_DIR} $i)"
        [[ -z "$root" ]] && die "failed to get relative path to root"

        case $i in
            *.py) echo "    Skipping python script $i";;
            */stereo) echo "    Skipping python script without .py $i";;
            *.sh) echo "    Skipping shell script $i";;
            *)
            # The rpaths given here are relative to the $root
            set_rpath $i $root ../isis/lib ../isis/3rdParty/lib lib || die "set_rpath failed"
            do_strip $i || die "Could not strip $i"
        esac
    fi
done
'''
