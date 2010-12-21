#!/usr/bin/env python

import os.path as P
import logging
import itertools
import shutil
import re
import errno
from os import makedirs, remove, listdir, chmod, symlink, readlink
from subprocess import Popen, PIPE
from collections import namedtuple
from BinaryBuilder import get_platform
from tempfile import mkdtemp
from glob import glob

global logger
logger = logging.getLogger()

class DistManager(object):

    def __init__(self, tarname):
        self.tarname = tarname
        self.distdir = Prefix(P.join(mkdtemp(), self.tarname))
        self.distlist = set()
        self.deplist  = dict()

    def add_executable(self, inpath, wrapper_file='libexec-helper.sh'):
        assert not P.islink(inpath), 'Cannot deal with sylinks in the bindir'
        base = P.basename(inpath)
        self._add_file(inpath, self.distdir.libexec(base))
        self._add_file(wrapper_file, self.distdir.bin(base))

    def add_library(self, inpath, symlinks_too=True, add_deps=True):
        for p in snap_symlinks(inpath) if symlinks_too else [inpath]:
            # This relpath weirdness is because libdirs can have subdirs
            ps = P.normpath(p).split('/')
            for seg_idx in range(0,len(ps)):
                seg = ps[seg_idx]
                if seg == 'lib' or seg == 'lib64' or seg == 'lib32':
                    relpath = '/'.join(ps[seg_idx+1:])
                    break
            else:
                raise Exception('Expected library %s to be in a libdir' % p)
            self._add_file(p, self.distdir.lib(relpath), add_deps=add_deps)

    def add_smart(self, inpath, prefix):
        inpath = P.abspath(inpath)
        assert P.commonprefix([inpath, prefix]) == prefix, 'path[%s] must be within prefix[%s]' % (inpath, prefix)

        relpath = P.relpath(inpath, prefix)
        if P.isdir(inpath):
            self.add_directory(inpath)
        elif relpath.startswith('bin/'):
            self.add_executable(inpath)
        elif relpath.startswith('lib/'):
            self.add_library(inpath)
        else:
            self._add_file(inpath, P.distdir(relpath))

    def add_directory(self, src, dst=None):
        if dst is None: dst = self.distdir
        mergetree(src, dst, self._add_file)

    def remove_deps(self, seq):
        [self.deplist.pop(k, None) for k in seq]

    def resolve_deps(self, nocopy, copy, search = None):
        if search is None:
            search = list(itertools.chain(nocopy, copy))
        logger.debug('Searching: %s' % (search,))

        found = set()
        for lib in self.deplist:
            for searchdir in search:
                checklib = P.join(searchdir, lib)
                if P.exists(checklib):
                    found.add(lib)
                    logger.debug('\tFound: %s' % checklib)
                    if searchdir in copy:
                        self.add_library(checklib, add_deps=False)
                    break
        self.remove_deps(found)

    def clean_dist(self):
        [remove(i) for i in run('find', self.distdir, '-name', '.*', '-print0').split('\0') if len(i) > 0 and i != '.' and i != '..']
        [chmod(file, 0755) for file in glob(self.distdir.libexec('*')) + glob(self.distdir.bin('*'))]

    def _add_file(self, src, dst, keep_symlink=True, add_deps=True):
        assert not P.isdir(src), 'Source path must not be a dir'
        assert not P.exists(dst), 'Cannot overwrite %s' % dst

        assert not P.relpath(P.abspath(dst), self.distdir).startswith('..'), \
               'destination %s must be within distdir[%s]' % (dst, self.distdir)

        assert dst not in self.distlist, 'Added %s twice!' % dst

        mkdir_f(P.dirname(dst))

        logger.debug('%s -> %s' % (src, dst))
        if keep_symlink and P.islink(src):
            symlink(readlink(src), dst)
        else:
            shutil.copy2(src, dst)

        self.distlist.add(dst)

        if add_deps and is_binary(dst):
            self.deplist.update(required_libs(dst))

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

def mergetree(src, dst, copyfunc):
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
                mergetree(srcname, dstname, copyfunc)
            else:
                copyfunc(srcname, dstname)
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
            remove(debug)

def set_rpath(filename, toplevel, searchpath):
    pass
    # Relative path from the file to the top of the dist
    #rel_to_top = P.relpath(toplevel, filename)
    #search_from_top = map(lambda p: P.relpath(p, toplevel))

def snap_symlinks(src):
    assert not P.isdir(src), 'Cannot chase symlinks on a directory'
    if not P.islink(src):
        return [src]
    return [src] + snap_symlinks(P.join(P.dirname(src), readlink(src)))

#def copy_with_links(src, dst):
#    assert P.isdir(dst), 'Destination must be a directory'
#    for link in snap_symlinks(src):
#        copy(link, dst)
#
#def flatten(lol):
#    return itertools.chain(*lol)
