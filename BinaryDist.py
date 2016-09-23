#!/usr/bin/env python

import os.path as P
import logging
import itertools, shutil, re, errno, sys, os, stat
from os import makedirs, remove, listdir, chmod, symlink, readlink, link
from collections import namedtuple
from BinaryBuilder import get_platform, run, hash_file, binary_builder_prefix,\
     list_recursively
from tempfile import mkdtemp, NamedTemporaryFile
from glob import glob
from functools import partial, wraps

''' Code for creating the downloadable binary distribution
'''


global logger
logger = logging.getLogger()

def is_binary(filename):
    '''Use the linux "file" tool to deterimen if a given file is a binary file'''
    ret = run('file', filename, output=True)
    return (ret.find('ELF') != -1) or (ret.find('Mach-O') != -1)

def doctest_on(os):
    '''Set up a function wrapper with a warning __doc__ if the provided os does not match?'''
    def outer(f):
        @wraps(f)
        def inner(*args, **kw): return f(*args, **kw)
        if get_platform().os != os:
            inner.__doc__ = '%s is only supported on %s' % (inner.__name__, os)
        return inner
    return outer

def default_baker(filename, distdir, searchpath):
    '''Updates a files rpath to be relative to distdir and strips it of symbols'''
    if not is_binary(filename):
        return
    set_rpath(filename, distdir, searchpath)
    strip(filename)

def which(program):
    '''Find if a program is in the PATH'''
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

class DistManager(object):
    '''Main class for creating a StereoPipeline binary distribution'''
    def __init__(self, tarname):
        self.tarname = tarname
        self.tempdir = mkdtemp(prefix='dist')
        self.distdir = Prefix(P.join(self.tempdir, self.tarname))
        self.distlist = set()  # List of files to be distributed
        self.deplist  = dict() # List of file dependencies
        mkdir_f(self.distdir)

    def remove_tempdir(self):
        shutil.rmtree(self.tempdir, True)

    def add_executable(self, inpath, wrapper_file='libexec-helper.sh', keep_symlink=True):
        ''' 'inpath' should be a file. This will add the executable to libexec/
            and the wrapper script to bin/ (with the basename of the exe) '''
        logger.debug('attempting to add %s' % inpath)
        base = P.basename(inpath)
        if P.islink(inpath):
            self._add_file(inpath, self.distdir.bin(base))
        elif base.endswith(".py"):
            self._add_file(inpath, self.distdir.bin(base))
        else:
            self._add_file(inpath, self.distdir.libexec(base))
            self._add_file(wrapper_file, self.distdir.bin(base))

    def add_library(self, inpath, symlinks_too=True, add_deps=True):
        ''' 'symlinks_too' means follow all symlinks, and add what they point
            to. 'add_deps' means scan the library and add its required dependencies
            to deplist.'''
        logger.debug('attempting to add %s' % inpath)
        for p in snap_symlinks(inpath) if symlinks_too else [inpath]:
            # This pulls out only the filename for the library. We
            # don't preserve the subdirs underneath 'lib'. This make
            # later rpath code easier to understand.
            lib = P.normpath(p).split('/')[-1]
            self._add_file(p, self.distdir.lib(lib), add_deps=add_deps)

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
        logger.debug('Dependency list--------------------------------------')
        for lib in self.deplist:
            logger.debug('  %s' % lib)

        found = set()
        for lib in self.deplist:
            for searchdir in search:
                checklib = P.join(searchdir, lib)
                print("search " + checklib)
                if P.exists(checklib):
                    found.add(lib)
                    logger.debug('\tFound: %s' % checklib)
                    if searchdir in copy:
                        self.add_library(checklib, add_deps=False)
                    break
        self.remove_deps(found)

    def create_file(self, relpath, mode='w'):
        '''Create a new file in self.distdir and open it'''
        return file(self.distdir.base(relpath), mode)

    def bake(self, searchpath, baker = default_baker):
        '''Updates the rpath of all files to be relative to distdir and strips it of symbols.
           Also cleans up some junk in self.distdir and sets file permissions.'''
        logger.debug('Baking list------------------------------------------')
        for filename in self.distlist:
            logger.debug('  %s' % filename)
        for filename in self.distlist:
            baker(filename, self.distdir, searchpath)

        # Delete all hidden files from the self.distdir folder
        [remove(i) for i in run('find', self.distdir, '-name', '.*', '-print0').split('\0') if len(i) > 0 and i != '.' and i != '..']
        # Enable read/execute on all files in libexec and bin
        [chmod(file, 0755) for file in glob(self.distdir.libexec('*')) + glob(self.distdir.bin('*'))]

    def make_tarball(self, include = (), exclude = (), name = None):
        '''Tar up all the files we have written to self.distdir.
           exclude takes priority over include '''

        if name is None: name = '%s.tar.bz2' % self.tarname
        if isinstance(include, basestring):
            include = [include]
        if isinstance(exclude, basestring):
            exclude = [exclude]

        cmd = ['tar', 'cf', name, '--use-compress-prog=pbzip2']
        cmd += ['-C', P.dirname(self.distdir)]
        if include:
            cmd += ['--no-recursion']
        for i in include:
            cmd += ['-T', i]
        for e in exclude:
            cmd += ['-X', e]
        cmd.append(self.tarname)

        logger.info('Creating tarball %s' % name)
        run(*cmd)

    def find_filter(self, *filter, **kw):
        '''Call "find" with a filter argument and write results to an opened temporary file'''
        dir = kw.get('dir', self.tarname)
        cwd = kw.get('cwd', P.dirname(self.distdir))
        cmd = ['find', dir] + list(filter)
        out = run(*cmd, cwd=cwd)
        files = NamedTemporaryFile()
        files.write(out)
        files.flush()
        return files

    def _add_file(self, src, dst, hardlink=False, keep_symlink=True, add_deps=True):
        '''Add a file to the list of distribution files'''
        dst = P.abspath(dst)

        assert not P.relpath(dst, self.distdir).startswith('..'), \
               'destination %s must be within distdir[%s]' % (dst, self.distdir)

        mkdir_f(P.dirname(dst))
        copy(src, dst, keep_symlink=keep_symlink, hardlink=hardlink)
        self.distlist.add(dst)

        if add_deps and is_binary(dst):
            self.deplist.update(required_libs(dst))

def copy(src, dst, hardlink=False, keep_symlink=True):
    '''Copy a file to another location with a bunch of link handling'''
    assert not P.isdir(src), 'Source path must not be a dir'
    assert not P.isdir(dst), 'Destination path must not be a dir'

    if keep_symlink and P.islink(src):
        assert not P.isabs(readlink(src)), 'Cannot copy symlink that points to an absolute path (%s)' % src
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

        # Bugfix, make it writeable
        mode = os.stat(dst)[stat.ST_MODE]
        os.chmod(dst, mode | stat.S_IWUSR)

@doctest_on('linux')
def readelf(filename):
    ''' Run readelf on a file

    >>> readelf('/lib/libc.so.6') # doctest:+ELLIPSIS
    readelf(needed=['ld-linux-...'], soname='libc.so.6', rpath=[])
    >>> readelf('/bin/ls') # doctest:+ELLIPSIS
    readelf(needed=[..., 'libc.so.6'], soname=None, rpath=[])
    '''

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

@doctest_on('linux')
def ldd(filename):
    ''' Run ldd on a file

    >>> ldd('/lib/libc.so.6')
    {}
    >>> ldd('/bin/ls') # doctest:+ELLIPSIS
    {..., 'libc.so.6': '/lib/libc.so.6'}

    '''

    libs = {}
    r = re.compile('^\s*(\S+) => (\S+)')
    for line in run('ldd', filename, output=True).split('\n'):
        m = r.search(line)
        if m:
            libs[m.group(1)] = (None if m.group(2) == 'not' else m.group(2))
    return libs

@doctest_on('osx')
def otool(filename):
    ''' Run otool on a binary
    >>> otool('/usr/lib/libSystem.B.dylib')
    otool(soname='libSystem.B.dylib', sopath='/usr/lib/libSystem.B.dylib', libs={'libmathCommon.A.dylib': '/usr/lib/system/libmathCommon.A.dylib'})
    >>> otool('/bin/ls')
    otool(soname=None, sopath=None, libs={'libSystem.B.dylib': '/usr/lib/libSystem.B.dylib', 'libncurses.5.4.dylib': '/usr/lib/libncurses.5.4.dylib'})
    '''

    Ret = namedtuple('otool', 'soname sopath libs old_rpaths')
    r = re.compile('^\s*(\S+)')
    lines = run('otool', '-L', filename, output=True).split('\n')
    libs = {}
    out = filter(lambda x: len(x.strip()), run('otool', '-D', filename, output=True).split('\n'))
    assert len(out) > 0, 'Empty output for otool -D %s' % filename
    assert len(out) < 3, 'Unexpected otool output: %s' % out

    this_soname = None
    this_sopath = None

    if len(out) == 2:
        this_sopath = out[1]
        this_soname = P.basename(this_sopath)

    for i in range(1, len(lines)):
        m = r.search(lines[i])
        if m:
            sopath = m.group(1)
            if this_sopath is not None and this_sopath == sopath:
                continue

            fidx = sopath.rfind('.framework')
            if fidx >= 0:
                soname = sopath[sopath.rfind('/', 0, fidx)+1:]
            else:
                soname = P.basename(sopath)
            libs[soname] = sopath

    # Identify the absolute RPATH dirs in the current install dir.
    # We'll wipe those later.
    old_rpaths = []
    lines = run('otool', '-l', filename, output=True).split('\n')
    for i in range(0, len(lines)):
        if re.search('cmd LC_RPATH', lines[i]):
            if i+2 < len(lines):
                m = re.match('^.*?path\s+([^\s]+)', lines[i+2])
                if m:
                    rpath_val = m.group(1)
                    if re.search(os.getcwd(), rpath_val):
                        # Keep only those in current dir, not system
                        # ones. Not sure about this, but it works.
                        old_rpaths.append(rpath_val)

    return Ret(soname=this_soname, sopath=this_sopath, libs=libs, old_rpaths=old_rpaths)

def required_libs(filename):
    ''' Returns a dict where the keys are required SONAMEs and the values are proposed full paths. '''
    def linux():
        soname = set(readelf(filename).needed)
        return dict((k,v) for k,v in ldd(filename).iteritems() if k in soname)
    def osx():
        return otool(filename).libs

    return locals()[get_platform().os]()

def grep(regex, filename):
    '''Run a regular expression search inside a file'''
    ret = []
    rx = re.compile(regex)
    with file(filename, 'r') as f:
        for line in f:
            m = rx.search(line)
            if m:
                ret.append(m)
    return ret

class Prefix(str):
    '''???'''
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
    ''' A mkdir -p that does not care if the dir is there '''
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
    '''Discard all symbols from this object file with OS specific flags'''
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

    # Get flags from one of the two functions above then run the strip command.
    flags = locals()[get_platform().os]()
    flags.append(filename)
    run('strip', *flags)


def save_elf_debug(filename):
    '''Copy the debug information from an ELF file'''
    debug = '%s.debug' % filename
    try:
        run('objcopy', '--only-keep-debug', filename, debug)
        run('objcopy', '--add-gnu-debuglink=%s' % debug, filename)
    except Exception:
        logger.warning('Failed to split debug info for %s' % filename)
        if P.exists(debug):
            remove(debug)

def set_rpath(filename, toplevel, searchpath, relative_name=True):
    '''For each input file, set the rpath to contain all the input
       search paths to be relative to the top level.'''
    assert not any(map(P.isabs, searchpath)), 'set_rpath: searchpaths must be relative to distdir (was given %s)' % (searchpath,)
    def linux():
        rel_to_top = P.relpath(toplevel, P.dirname(filename))
        rpath = [P.join('$ORIGIN', rel_to_top, path) for path in searchpath]
        if run('chrpath', '-r', ':'.join(rpath), filename, raise_on_failure = False) is None:
            logger.warn('Failed to set_rpath on %s' % filename)
    def osx():
        info = otool(filename)

        # soname is None for an executable
        if info.soname is not None:
            info.libs[info.soname] = info.sopath
            # If we are not using relative paths .. always fix the install name.
            if not relative_name:
                run('install_name_tool', '-id',
                    filename, filename)

        logger.debug("Trying to Bake %s" % filename)
        logger.debug("Info sopath %s" % info.sopath)
        logger.debug("Toplevel var %s" % toplevel)
        logger.debug("Possible search path %s" % searchpath)

        for soname, sopath in info.libs.iteritems():
            logger.debug("Soname %s Sopath %s" % (soname, sopath))
            # /tmp/build/install/lib/libvwCore.5.dylib
            # base = libvwCore.5.dylib
            # looks for @executable_path/../lib/libvwCore.5.dylib

            # /opt/local/libexec/qt4-mac/lib/QtXml.framework/Versions/4/QtXml
            # base = QtXml.framework/Versions/4/QtXml
            # looks for @executable_path/../lib/QtXml.framework/Versions/4/QtXml

            # OSX rpath points to one specific file, not anything that matches the
            # library SONAME. We've already done a whitelist check earlier, so
            # ignore it if we can't find the lib we want

            # XXX: This code carries an implicit assumption that all
            # executables are one level below the root (because
            # @executable_path is always the exe path, not the path of the
            # current binary like $ORIGIN in linux)
            for rpath in searchpath:
                if P.exists(P.join(toplevel, rpath, soname)):
                    new_path = P.join('@rpath', soname)
                    # If the entry is the "self" one, it has to be
                    # changed differently
                    if info.sopath == sopath:
                        if relative_name:
                            run('install_name_tool', '-id', new_path, filename)
                        break
                    else:
                        run('install_name_tool', '-change', sopath, new_path, filename)
                        break
        if len(info.libs):
            for rpath in searchpath:
                if run('install_name_tool','-add_rpath',P.join('@executable_path','..',rpath), filename,
                       raise_on_failure = False) is None:
                    logger.warn('Failed to add rpath on %s' % filename)
                if run('install_name_tool','-add_rpath',P.join('@loader_path','..',rpath), filename,
                       raise_on_failure = False) is None:
                    logger.warn('Failed to add rpath on %s' % filename)

        # We'd like to wipe the hard-coded RPATH pointing to the
        # original install directory. The user won't have it, and it
        # causes problems on the build machine, as libraries are
        # loaded from both the new and original locations which
        # results in a subtle crash. If the same rpath shows up twice,
        # wiping it causes problems, so then we don't do it.
        if len(info.old_rpaths) == 1:
            for old_rpath in info.old_rpaths:
                run('install_name_tool', '-delete_rpath', old_rpath, filename)

    # Call one of the two functions above depending on the OS
    locals()[get_platform().os]()

def snap_symlinks(src):
    '''Build a list of chained symlink files until we reach a non-link file.'''
    assert src, 'Cannot snap symlink which is NONE'
    assert not P.isdir(src), 'Cannot chase symlinks on a directory'
    if not P.islink(src):
        return [src]
    return [src] + snap_symlinks(P.join(P.dirname(src), readlink(src)))

def fix_install_paths(installdir, arch):
    ''' After unpacking a set of pre-built binaries, in given directory,
        fix any paths to point to the current directory. '''

    print('Fixing paths in libtool control files, etc.')
    control_files = glob(P.join(installdir,'include','*config.h')) + \
                    glob(P.join(installdir,'lib','*.la'))          + \
                    glob(P.join(installdir,'lib','*.prl'))         + \
                    glob(P.join(installdir,'lib','*', '*.pc'))     + \
                    glob(P.join(installdir,'bin','*'))             + \
                    glob(P.join(installdir,'mkspecs','*.pri'))     + \
                    list_recursively(P.join(installdir,'share'))

    for control in control_files:

        # Skip folders and binaries
        if os.path.isdir(control): continue
        if is_binary(control): continue

        print('  %s' % P.basename(control))

        # ensure we can read and write (some files have odd permissions)
        st = os.stat(control)
        os.chmod(control, st.st_mode | stat.S_IREAD | stat.S_IWRITE)

        # replace the temporary install directory with the one we're deploying to. (Modify file in-place)
        lines = []
        with open(control,'r') as f:
            lines = f.readlines()
        with open(control,'w') as f:
            for line in lines:
                line = re.sub('[\/\.]+[\w\/\.\-]*?' + binary_builder_prefix() + '\w*[\w\/\.]*?/install', installdir, line)
                f.write( line )

    # Create libblas.la (out of existing libsuperlu.la). We need
    # libblas.la to force blas to show up before superlu when linking
    # on Linux to avoid a bug with corruption when invoking lapack in
    # a multi-threaded environment.  A better long-term solution is needed.
    superlu_la = installdir + '/lib/libsuperlu.la'
    blas_la = installdir + '/lib/libblas.la'
    if arch.os == 'linux' and os.path.exists(superlu_la):
        lines = []
        with open(superlu_la,'r') as f:
                lines = f.readlines()
        with open(blas_la,'w') as f:
            for line in lines:
                line = re.sub('libsuperlu', 'libblas', line)
                line = re.sub('dlname=\'.*?\'',
                              'dlname=\'libblas.so\'', line)
                line = re.sub('library_names=\'.+?\'',
                              'library_names=\'libblas.so\'', line)
                # Force blas to depend on superlu
                line = re.sub('dependency_libs=\'.*?\'',
                              'dependency_libs=\' -L' + installdir
                              + '/lib  -lsuperlu -lm\'', line)
                f.write( line )

    library_ext = ["so"]
    if arch.os == 'osx':
        library_ext.append("dylib")

    # Ensure installdir/bin is in the path, to be able to find chrpath, etc.
    if "PATH" not in os.environ: os.environ["PATH"] = ""
    os.environ["PATH"] = P.join(installdir, 'bin') + \
                         os.pathsep + os.environ["PATH"]

    SEARCHPATH = [P.join(installdir,'lib'),
                  P.join(installdir,'lib','osgPlugins*')]

    print('Fixing RPATHs')
    for curr_path in SEARCHPATH:
        for extension in library_ext:
            for library in glob(P.join(curr_path,'*.'+extension+'*')):
                if not is_binary(library):
                    continue
                print('  %s' % P.basename(library))
                try:
                    set_rpath(library, installdir, map(lambda path: P.relpath(path, installdir), SEARCHPATH), False)
                except:
                    print('  Failed %s' % P.basename(library))

    print('Fixing Binaries')
    for binary in glob(P.join(installdir,'bin','*')):
        if not is_binary(binary):
            continue
        print('  %s' % P.basename(binary))
        try:
            set_rpath(binary, installdir, map(lambda path: P.relpath(path, installdir), SEARCHPATH), False)
        except:
            print('  Failed %s' % P.basename(binary))


if __name__ == '__main__':
    import doctest
    doctest.testmod()
