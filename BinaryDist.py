#!/usr/bin/env python

import os.path as P
import logging
import itertools
import shutil
import re
import errno
from os import makedirs, remove, listdir, chmod, symlink, readlink, link
from collections import namedtuple
from BinaryBuilder import get_platform, run, hash_file
from tempfile import mkdtemp, NamedTemporaryFile
from glob import glob
from functools import partial

global logger
logger = logging.getLogger()

def default_baker(filename, distdir, searchpath):
    if not is_binary(filename): return
    set_rpath(filename, distdir, searchpath)
    strip(filename)

class DistManager(object):

    def __init__(self, tarname):
        self.tarname = tarname
        self.distdir = Prefix(P.join(mkdtemp(prefix='dist'), self.tarname))
        self.distlist = set()
        self.deplist  = dict()
        mkdir_f(self.distdir)

    def add_executable(self, inpath, wrapper_file='libexec-helper.sh', keep_symlink=True):
        ''' 'inpath' should be a file. This will add the executable to libexec/
            and the wrapper script to bin/ (with the basename of the exe) '''

        base = P.basename(inpath)
        if P.islink(inpath):
            self._add_file(inpath, self.distdir.bin(base))
        else:
            self._add_file(inpath, self.distdir.libexec(base))
            self._add_file(wrapper_file, self.distdir.bin(base))

    def add_library(self, inpath, symlinks_too=True, add_deps=True):
        ''' 'symlinks_too' means follow all symlinks, and add what they point
            to. 'add_deps' means scan the library and add its required dependencies
            to deplist.'''

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

    def add_glob(self, pattern, prefix, require_match=True):
        ''' Add a pattern to the tree. pattern must be relative to an
            installroot, provided in 'prefix' '''
        pat = P.join(prefix, pattern)
        inpaths = glob(pat)
        if require_match:
            assert len(inpaths) > 0, 'No matches for glob pattern %s' % pat
        [self.add_smart(i, prefix) for i in inpaths]

    def add_smart(self, inpath, prefix):
        ''' Looks at the relative path, and calls the correct add_* function '''
        if not P.isabs(inpath):
            inpath = P.abspath(P.join(prefix, inpath))
        assert P.commonprefix([inpath, prefix]) == prefix, 'path[%s] must be within prefix[%s]' % (inpath, prefix)

        relpath = P.relpath(inpath, prefix)
        if P.isdir(inpath):
            for d in listdir(P.join(prefix, inpath)):
                self.add_smart(P.relpath(P.join(prefix, inpath, d), prefix), prefix)
        elif relpath.startswith('bin/'):
            self.add_executable(inpath)
        elif relpath.startswith('lib/'):
            self.add_library(inpath)
        else:
            self._add_file(inpath, self.distdir.base(relpath))

    def add_directory(self, src, dst=None, hardlink=False):
        ''' Recursively add a directory. Will do it dumbly! No magic here. '''
        if dst is None: dst = self.distdir
        mergetree(src, dst, partial(self._add_file, hardlink=hardlink, add_deps=False))

    def remove_deps(self, seq):
        ''' Filter deps out of the deplist '''
        [self.deplist.pop(k, None) for k in seq]

    def resolve_deps(self, nocopy, copy, search = None):
        ''' Find as many of the currently-listed deps as possible. If the dep
            is found in one of the 'copy' dirs, copy it (without deps) to the dist.'''
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

    def create_file(self, relpath, mode='w'):
        return file(self.distdir.base(relpath), mode)

    def bake(self, searchpath, baker = default_baker):
        for filename in self.distlist:
            baker(filename, self.distdir, searchpath)

        [remove(i) for i in run('find', self.distdir, '-name', '.*', '-print0').split('\0') if len(i) > 0 and i != '.' and i != '..']
        [chmod(file, 0755) for file in glob(self.distdir.libexec('*')) + glob(self.distdir.bin('*'))]

    def make_tarball(self, include = (), exclude = (), name = None):
        ''' exclude takes priority over include '''

        if name is None: name = '%s.tar.gz' % self.tarname
        if isinstance(include, basestring):
            include = [include]
        if isinstance(exclude, basestring):
            exclude = [exclude]

        cmd = ['tar', 'czf', name, '-C', P.dirname(self.distdir), self.tarname]
        if include:
            cmd += ['--no-recursion']
        for i in include:
            cmd += ['-T', i]
        for e in exclude:
            cmd += ['-X', e]

        logger.info('Creating tarball %s' % name)
        run(*cmd)

    def find_filter(self, *filter, **kw):
        dir = kw.get('dir', self.tarname)
        cwd = kw.get('cwd', P.dirname(self.distdir))
        files = NamedTemporaryFile()
        cmd = ['find', dir] + list(filter) + ['-fprint', files.name]
        run(*cmd, cwd=cwd)
        return files

    def _add_file(self, src, dst, hardlink=False, keep_symlink=True, add_deps=True):
        dst = P.abspath(dst)

        assert not P.relpath(dst, self.distdir).startswith('..'), \
               'destination %s must be within distdir[%s]' % (dst, self.distdir)

        mkdir_f(P.dirname(dst))
        copy(src, dst, keep_symlink=keep_symlink, hardlink=hardlink)
        self.distlist.add(dst)

        if add_deps and is_binary(dst):
            self.deplist.update(required_libs(dst))

def copy(src, dst, hardlink=False, keep_symlink=True):
    assert not P.isdir(src), 'Source path must not be a dir'
    assert not P.isdir(dst), 'Destination path must not be a dir'

    if keep_symlink and P.islink(src):
        assert not P.isabs(readlink(src)), 'Cannot copy symlink that points to an absolute path'
        logger.debug('%8s %s -> %s' % ('symlink', src, dst))
        if P.exists(dst):
            assert readlink(dst) == readlink(src), 'Refusing to retarget already-exported symlink %s' % dst
        else:
            symlink(readlink(src), dst)
        return

    if P.exists(dst):
        assert hash_file(src) == hash_file(dst), 'Refusing to overwrite already exported dst %s' % dst
    else:
        if hardlink:
            try:
                link(src, dst)
                logger.debug('%8s %s -> %s' % ('hardlink', src, dst))
                return
            except OSError, o:
                if o.errno != errno.EXDEV: # Invalid cross-device link, not an error, fall back to copy
                    raise

        logger.debug('%8s %s -> %s' % ('copy', src, dst))
        shutil.copy2(src, dst)

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
    def linux():
        soname = set(readelf(filename).needed)
        return dict((k,v) for k,v in ldd(filename).iteritems() if k in soname)
    def osx():
        return otool(filename).libs

    return locals()[get_platform().os]()

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

    def linux():
        typ = run('file', filename, output=True)
        if typ.find('current ar archive') != -1:
            return ['-g']
        elif typ.find('SB executable') != -1 or typ.find('SB shared object') != -1:
            save_elf_debug(filename)
            return ['--strip-unneeded', '-R', '.comment']
        elif typ.find('SB relocatable') != -1:
            return ['--strip-unneeded']
        return None
    def osx():
        return ['-S']

    flags = locals()[get_platform().os]()
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
    assert not any(map(P.isabs, searchpath)), 'set_rpath: searchpaths must be relative to distdir (was given %s)' % (searchpath,)
    def linux():
        rel_to_top = P.relpath(toplevel, P.dirname(filename))
        rpath = [P.join('$ORIGIN', rel_to_top, path) for path in searchpath]
        if run('chrpath', '-r', ':'.join(rpath), filename, raise_on_failure = False) is None:
            logger.warn('Failed to set_rpath on %s' % filename)
    def osx():
        info = otool(filename)
        info.libs[info.soname] = info.sopath
        for sopath in info.libs.values():
            # /tmp/build/install/lib/libvwCore.5.dylib
            # base = libvwCore.5.dylib
            # looks for @executable_path/../lib/libvwCore.5.dylib

            # /opt/local/libexec/qt4-mac/lib/QtXml.framework/Versions/4/QtXml
            # base = QtXml.framework/Versions/4/QtXml
            # looks for @executable_path/../lib/QtXml.framework/Versions/4/QtXml
            fidx = sopath.rfind('.framework')
            if fidx >= 0:
                soname = sopath[sopath.rfind('/', 0, fidx)+1:]
            else:
                soname = P.basename(sopath)

            # OSX rpath points to one specific file, not anything that matches the
            # library SONAME. We've already done a whitelist check earlier, so
            # ignore it if we can't find the lib we want

            # XXX: This code carries an implicit assumption that all
            # executables are one level below the root (because
            # @executable_path is always the exe path, not the path of the
            # current binary like $ORIGIN in linux)
            for rpath in searchpath:
                if P.exists(P.join(toplevel, rpath, soname)):
                    new_path = P.join('@executable_path', '..', rpath, soname)
                    # If the entry is the "self" one, it has to be changed differently
                    if info.sopath == sopath:
                        run('install_name_tool', '-id', new_path, filename)
                        break
                    else:
                        run('install_name_tool', '-change', sopath, new_path, filename)
                        break

    locals()[get_platform().os]()

def snap_symlinks(src):
    assert not P.isdir(src), 'Cannot chase symlinks on a directory'
    if not P.islink(src):
        return [src]
    return [src] + snap_symlinks(P.join(P.dirname(src), readlink(src)))
