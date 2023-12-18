#!/usr/bin/env python

import os.path as P
import logging
import itertools, shutil, re, errno, sys, os, stat, subprocess, platform
from os import makedirs, remove, listdir, chmod, symlink, readlink, link
from collections import namedtuple
from tempfile import mkdtemp, NamedTemporaryFile
from glob import glob
from functools import partial, wraps
from hashlib import sha1

'''
Code for creating the downloadable binary distribution of ASP.
'''

global logger
logger = logging.getLogger()

def binary_builder_prefix():
    return 'BinaryBuilder'

def hash_file(filename):
    with open(filename, 'rb') as f:
        return sha1(f.read()).hexdigest()

def run(*args, **kw):
    '''Try to execute a command line command'''
    need_output      = kw.pop('output', False)
    raise_on_failure = kw.pop('raise_on_failure', True)
    want_stderr      = kw.pop('want_stderr', False)
    kw['stdout']     = kw.get('stdout', subprocess.PIPE)
    kw['stderr']     = kw.get('stderr', subprocess.PIPE)

    logger.debug('run: [%s] (wd=%s)' % (' '.join(args), kw.get('cwd', os.getcwd())))

    p = subprocess.Popen(args, **kw)
    out, err = p.communicate()
    if out is not None:
        out = out.decode('utf-8')
    if err is not None:
        err = err.decode('utf-8')
    msg = None
    if p.returncode != 0:
        msg = '%s: return code: %d (output: %s) (error: %s)' % (args, p.returncode, out, err)
    elif need_output and len(out) == 0:
        msg = '%s: failed (no output). (%s)' % (args,err)
    if msg is not None:
        if raise_on_failure: raise Exception(msg)
        logger.warn(msg)
        return False, msg
    if want_stderr:
        return out, err
    return out

def get_platform(pkg=None):
    system  = platform.system()
    machine = platform.machine()
    p = namedtuple('Platform', 'os bits osbits system machine prettyos dist_name dist_version')
    if system == 'Linux':
        name  = 'Linux'
        ver  = ''
    elif system == 'Darwin':
        name = 'Darwin'
        ver  = platform.mac_ver()[0]

    if system == 'Linux' and machine == 'x86_64':
        return p('linux', 64, 'linux64', system, machine, 'Linux', name, ver)
    elif system == 'Linux' and machine == 'i686':
        return p('linux', 32, 'linux32', system, machine, 'Linux', name, ver)
    elif system == 'Darwin' and machine == 'i386':
        # Force 64 bit no matter what
        return p('osx', 64, 'osx64', system, 'x86_64', 'OSX', name, ver)
    elif system == 'Darwin' and machine == 'x86_64':
        return p('osx', 64, 'osx64', system, machine, 'OSX', name, ver)
    else:
        message = 'Cannot match system to known platform'
        if pkg is None:
            raise Exception(message)
        else:
            raise PackageError(pkg, message)

# List recursively all files in given directory
def list_recursively(dir):
    matches = []
    for root, dirnames, filenames in os.walk(dir):
        for filename in filenames:
            matches.append(os.path.join(root, filename))
    return matches

def make_list_unique(in_list):
    '''Remove repetitions from a list.'''
    vals_dict = {}
    out_list = []
    for val in in_list:
        if val in vals_dict:
            continue
        out_list.append(val)
        vals_dict[val] = 1

    return out_list

def lib_ext(arch):
    if arch == 'osx':
        lib_ext = '.dylib'
    else:
        lib_ext = '.so'
    return lib_ext
    
# What does this one do?
def strip_flag(flag, key, env):
    ret = []
    hit = None
    if not key in env:
        return
    for test in env[key].split():
        m = re.search(flag, test)
        if m:
            hit = m
        else:
            ret.append(test)
    if ret:
        env[key] = ' '.join(ret).strip()
    else:
        del env[key]
    return hit, env

def is_ascii(filename):
    '''Use the "file" tool to determine if a given file is ascii'''
    try:
        ret = run('file', filename, output=True)
    except:
       return False
    return (ret.find('ASCII') != -1)

def is_lib_or_bin_prog(filename):
    '''Use the "file" tool to determine if a given file is a a library or a binary
       executable program. Being non-ASCII, on its own, is not enough to qualify.'''
    try:
        ret = run('file', filename, output=True)
    except:
       return False
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
    if is_ascii(filename):
        fix_paths(filename)
        return
    if is_lib_or_bin_prog(filename):
        set_rpath(filename, distdir, searchpath)

    # On linux stripping causes the conda libraries to crash
    if get_platform().os != 'linux':
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

def mkdir_f(dirname):
    ''' A mkdir -p that does not care if the dir is there '''
    try:
        makedirs(dirname)
    except OSError as o:
        if o.errno == errno.EEXIST and P.isdir(dirname):
            return
        raise

class DistManager(object):
    '''Main class for creating a StereoPipeline binary distribution'''
    def __init__(self, tarname, exec_wrapper_file, asp_install_dir, asp_deps_dir):
        self.wrapper_file = exec_wrapper_file
        self.tarname = tarname
        self.tempdir = mkdtemp(prefix='dist')
        self.distdir = DistPrefix(P.join(self.tempdir, self.tarname))
        self.asp_install_dir = asp_install_dir
        self.asp_deps_dir = asp_deps_dir
        self.distlist  = set()  # List of files to be distributed
        self.deplist   = dict() # List of file dependencies
        self.parentlib = dict() # library k is used by parentlib[k]
        self.dst_to_src = dict()
        
        mkdir_f(self.distdir)

    def remove_tempdir(self):
        shutil.rmtree(self.tempdir, True)

    def add_executable(self, inpath, keep_symlink=True):
        ''' 'inpath' should be a file. This will add the executable to libexec/
            and the wrapper script to bin/ (with the basename of the exe) '''
        logger.debug('attempting to add %s' % inpath)
        base = P.basename(inpath)

        # When adding a symlink, also add the file it points to.
        if P.islink(inpath):
            paths = snap_symlinks(inpath)
        else:
            paths = [inpath]

        # Note: The .py executables are exempted from having a wrapper
        # file. This appears by design, as some of these
        # have external dependencies and must be invoked with an
        # external python, without the shell wrapper. This is a
        # haphazard approach, however.
        if base.endswith(".py"):
            self._add_file(inpath, self.distdir.bin(base))
        else:
            for path in paths:
                base = P.basename(path)
                self._add_file(path, self.distdir.libexec(base))
                self._add_file(self.wrapper_file, self.distdir.bin(base))

    def add_library(self, inpath, symlinks_too=True, add_deps=True, is_plugin = False):
        ''' 'symlinks_too' means follow all symlinks, and add what they point
            to. 'add_deps' means scan the library and add its required dependencies
            to deplist.'''
        logger.debug('attempting to add %s' % inpath)
        if symlinks_too:
            paths = snap_symlinks(inpath)

            # This is a bugfix, sometimes not all symbolic links are added
            all_paths = []
            for path in paths:
                for newpath in glob(path + '*'):
                    all_paths.append(newpath)
            paths = make_list_unique(all_paths)
                
        else:
            paths = [inpath]

        for p in paths:
            # This pulls out only the filename for the library. We
            # don't preserve the subdirs underneath 'lib'. This make
            # later rpath code easier to understand.
            lib = P.normpath(p).split('/')[-1]
            if not is_plugin:
                self._add_file(p, self.distdir.lib(lib), add_deps=add_deps)
            else:
                self._add_file(p, usgscsm_plugin_path(self.distdir, lib), add_deps=add_deps)

    def add_glob(self, pattern, prefixes):
        ''' Add a pattern to the tree. pattern must be relative to an
            installroot, provided in one of the prefixes.'''
        if pattern == "":
            raise Exception("Tried to add a glob with an empty pattern.")
        inpaths = []
        for prefix in prefixes:
            pat     = P.join(prefix, pattern)
            inpaths = glob(pat)
            [self.add_smart(i, prefix) for i in inpaths]
            
    def add_smart(self, inpath, prefix):
        ''' Looks at the relative path, and calls the correct add_* function '''
        if not P.isabs(inpath):
            inpath = P.abspath(P.join(prefix, inpath))
        assert P.commonprefix([inpath, prefix]) == prefix, \
               'path[%s] must be within prefix[%s]' % (inpath, prefix)

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

    def add_file(self, src, dst=None, hardlink=False):
        '''Copy a file to a destination given as a directory relative to distdir.
        That is, cp src distdir/dst/src.'''
        if dst is None:
            dst = self.distdir
        else:
            dst = P.join(self.distdir, dst)
        dst = P.join(dst, src)
        self._add_file(src, dst)
        
    def add_directory(self, src, dst = None, hardlink = False, subdirs = []):
        '''
        Recursively copy the files and dirs in src, and make them relative to directory dst.
        That is:
           cp -rf src/* dst/
        Can also add only selected subdirectories.
        '''
        if dst is None: dst = self.distdir
        if not P.exists(src):
            raise Exception("Failed to find directory: " + src)

        if len(subdirs) == 0:
            # Copy everything in src
            mergetree(src, dst, partial(self._add_file, hardlink=hardlink, add_deps=False))
        else:
            # Copy only selected subdirectories
            for subdir in subdirs:
                mergetree(src + "/" + subdir, dst + "/" + subdir,
                          partial(self._add_file, hardlink=hardlink, add_deps=False))
                
    def remove_deps(self, seq):
        ''' Filter deps out of the deplist '''
        for k in seq:
            self.deplist.pop(k, None)

    def remove_already_added(self, seq):
        '''It seems easier to first copy all dependences,
        then wipe the ones we do not want to ship.
        We assume any entry is in distdir/*/entry'''
        for k in seq:
            files = glob(P.join(self.distdir, '*', k + '*'))
            for f in files:
                try:
                    print("Removing: " + f)
                    os.remove(f)
                except:
                    pass
        
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
                if P.exists(checklib):
                    found.add(lib)
                    logger.debug('\tFound: %s' % checklib)
                    if searchdir in copy:
                        self.add_library(checklib, add_deps=False)
                    break
        self.remove_deps(found)

    def create_file(self, relpath, mode='w'):
        '''Create a new file in self.distdir and open it'''
        return open(self.distdir.base(relpath), mode)

    def bake(self, searchpath, baker = default_baker):
        '''Updates the rpath of all files to be relative to distdir and strips it of symbols.
           Also cleans up some junk in self.distdir and sets file permissions.'''
        logger.debug('Baking list')
        for filename in self.distlist:
            logger.debug('  %s' % filename)
        for filename in self.distlist:
            baker(filename, self.distdir, searchpath)

        # Delete all hidden files from the self.distdir folder
        for i in run('find', self.distdir, '-name', '.*', '-print0').split('\0'):
            if len(i) > 0 and i != '.' and i != '..':
                try:
                    remove(i)
                except Exception as e:
                    print(e)

    def make_tarball(self, include = (), exclude = (), name = None):
        '''Tar up all the files we have written to self.distdir.
           exclude takes priority over include '''

        if name is None: name = '%s.tar.bz2' % self.tarname
        if isinstance(include, str):
            include = [include]
        if isinstance(exclude, str):
            exclude = [exclude]

        # Ensure all the files are readable
        cmd = ['chmod', '-R', 'a+r', P.dirname(self.distdir)]
        run(*cmd)
        
        # Enable read/execute on all files in libexec, bin, and stereo plugins.
        # Also for all subdirectories.
        rwx_list = glob(self.distdir.libexec('*')) + glob(self.distdir.bin('*')) + \
                       glob(self.distdir + "/plugins/stereo/*/bin/*")
        for dir_name in glob(self.distdir + "/*"):
            if os.path.isdir(dir_name):
                rwx_list.append(dir_name)
        for path in rwx_list:
            os.chmod(path, 0o755) # note we use the octal value of 755

        # Use the current modification time. This is not working by
        # default or some reason.
        cmd = ['touch', self.distdir]
        run(*cmd)
        
        cmd = ['tar', 'cf', name, '--use-compress-prog=pbzip2']
        cmd += ['-C', P.dirname(self.distdir)]

        if include:
            cmd += ['--no-recursion']
        for i in include:
            cmd += ['-T', i]
        for e in exclude:
            if os.path.exists(e):
                cmd += ['-X', e]
        cmd.append(self.tarname)

        logger.info('Creating tarball %s' % name)
        run(*cmd)

    def find_filter(self, *filter, **kw):
        '''Call "find" with a filter argument and write results to an opened temporary file'''
        dir = kw.get('dir', self.tarname)
        cwd = kw.get('cwd', P.dirname(self.distdir))
        cmd = ['find', dir] + list(filter)
        out = run(*cmd, cwd=cwd).encode()
        files = NamedTemporaryFile()
        files.write(out)
        files.flush()
        return files

    def sym_link_lib(self, src, dst):
        '''In the lib directory, symlink src to dst.'''
        logger.debug('attempting to symlink ' + src + ' to ' + dst)
        base_src = P.normpath(src).split('/')[-1]
        base_dst = P.normpath(dst).split('/')[-1]
        lib_dir = P.dirname(self.distdir.lib(base_src))
        mkdir_f(lib_dir)

        # Go to the lib dir and make the link
        cmd = ['ln', '-s', base_src, base_dst]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=lib_dir)
        out, err = p.communicate()
        if out is not None:
            out = out.decode('utf-8')
        if err is not None:
            err = err.decode('utf-8')

    def _add_file(self, src, dst, hardlink=False, keep_symlink=True, add_deps=True):
        '''Add a file to the list of distribution files'''

        dst = P.abspath(dst)
        assert not P.relpath(dst, self.distdir).startswith('..'), \
               'destination %s must be within distdir[%s]' % (dst, self.distdir)

        mkdir_f(P.dirname(dst))

        # If a file to copy shows up in multiple places, prefer the
        # one from the ASP install dir. Then the one from
        # asp_deps_dir. Those are portable, unlike potentially the
        # files in the current system.
        if dst in self.dst_to_src:
            if self.asp_install_dir in self.dst_to_src[dst] and \
                    (not self.asp_install_dir in src):
                print("Will copy " + self.dst_to_src[dst] + " and not " + src)
                return
            if self.asp_deps_dir in self.dst_to_src[dst] and \
                    (not self.asp_deps_dir in src):
                print("Will copy " + self.dst_to_src[dst] + " and not " + src)
                return
                       
        self.dst_to_src[dst] = src

        try:
            copy(src, dst, keep_symlink=keep_symlink, hardlink=hardlink)
            self.distlist.add(dst)
        except Exception as e:
            # Bail out if the copying failed.
            # TODO(oalexan1): This may need finer-grained treatment
            print("Warning: " + str(e))
            return
        
        if add_deps and is_lib_or_bin_prog(dst):
            # Search for dependencies in our preferred locations first
            search_path = self.asp_install_dir + "/lib" + ":" + self.asp_deps_dir + "/lib"
            req = required_libs(dst, search_path)
            self.deplist.update(req)
            
            # Keep track for later which library needs the current library
            for lib in req.keys():
                if not lib in self.parentlib.keys():
                    self.parentlib[lib] = [dst]
                else:
                    self.parentlib[lib].append(dst)

def copy(src, dst, hardlink=False, keep_symlink=True):
    '''Copy a file to another location with a bunch of link handling'''
    assert not P.isdir(src), 'Source path must not be a dir'
    assert not P.isdir(dst), 'Destination path must not be a dir'

    # There is nothing we can do about absolute sym links in system dirs. We just
    # trace those to the source and copy.
    if keep_symlink and P.islink(src):
        if P.isabs(readlink(src)):
            m = re.match(r'^/usr', readlink(src))
            if m:
                print("Resolving absolute link: ", src)
                while P.islink(src) and \
                          P.isabs(readlink(src)) \
                          and os.path.basename(src) == os.path.basename(readlink(src)):
                    src = readlink(src)
                    print("Resolved to: ", src)

    if keep_symlink and P.islink(src):

        assert not P.isabs(readlink(src)), \
               'Cannot copy symlink that points to an absolute path (%s)' % src
        logger.debug('%8s %s -> %s' % ('symlink', src, dst))

        # Some of the libraries are both in our install dir and in USGS conda's package.
        # That is because they do not provide headers for cspice for example.
        # So below we will run into trouble. Just overwrite any library we built
        # with the one from conda.
        if P.exists(dst):
            is_soft_link = True
            try:
                link_val = readlink(dst)
            except:
                is_soft_link = False

            if (not is_soft_link) or (readlink(dst) != readlink(src)):
                print("Will overwrite " + dst + " with " + src)
                os.remove(dst)

        if not P.exists(dst):
            try:
                symlink(readlink(src), dst)
            except:
                pass
        return

    if P.exists(dst):
        # This should happen rarely, normally the problem of which
        # instance of a given file to copy should be solved by now.
        if hash_file(src) != hash_file(dst):
            print("Will overwrite " + dst + " with " + src + " having a different hash.")

    if hardlink:
        try:
            link(src, dst)
            logger.debug('%8s %s -> %s' % ('hardlink', src, dst))
            return
        except OSError as o:
            # Invalid cross-device link, not an error, fall back to copy
            if o.errno != errno.EXDEV: 
                raise

    logger.debug('%8s %s -> %s' % ('copy', src, dst))

    shutil.copyfile(src, dst)

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
    r = re.compile(r' \((.*?)\).*\[(.*?)\]')
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
def ldd(filename, search_path):
    ''' Run ldd on a file

    >>> ldd('/lib/libc.so.6')
    {}
    >>> ldd('/bin/ls') # doctest:+ELLIPSIS
    {..., 'libc.so.6': '/lib/libc.so.6'}

    '''

    libs = {}
    r = re.compile(r'^\s*(\S+) => (\S+)')

    # Ensure this is initalized
    if "LD_LIBRARY_PATH" not in os.environ:
        os.environ["LD_LIBRARY_PATH"] = ""

    # Help ldd find the libraries in the desired location
    # Turning this off recently as it causes isses with
    # system tools.
    #orig_path =  os.environ["LD_LIBRARY_PATH"]
    #os.environ["LD_LIBRARY_PATH"] = search_path
    
    for line in run('ldd', filename, output=True).split('\n'):
        m = r.search(line)
        if m:
            libs[m.group(1)] = (None if m.group(2) == 'not' else m.group(2))

    # Restore the orginal environment
    #os.environ["LD_LIBRARY_PATH"] = orig_path
    
    return libs

@doctest_on('osx')
def otool(filename):
    ''' Run otool on a binary
    >>> otool('/usr/lib/libSystem.B.dylib')
    otool(soname='libSystem.B.dylib', sopath='/usr/lib/libSystem.B.dylib', libs={'libmathCommon.A.dylib': '/usr/lib/system/libmathCommon.A.dylib'})
    >>> otool('/bin/ls')
    otool(soname=None, sopath=None, libs={'libSystem.B.dylib': '/usr/lib/libSystem.B.dylib', 'libncurses.5.4.dylib': '/usr/lib/libncurses.5.4.dylib'})
    '''

    Ret = namedtuple('otool', 'soname sopath libs abs_rpaths rel_rpaths')
    r = re.compile(r'^\s*(\S+)')
    lines = run('otool', '-L', filename, output=True).split('\n')
    libs = {}

    # Run otool -D and keep the non-empty lines
    vals = run('otool', '-D', filename, output=True).split('\n')
    out = []
    for val in vals:
        if len(val.strip()) > 0:
            out.append(val.strip())

    assert len(out) > 0, 'Empty output for otool -D %s' % filename

    # Turn this off as being too verbose
    #if len(out) > 2:
    #    print("Suspect output produced by otool -D " + filename + ".\n")
    #    print("Only two entries expected, but got: " + " ".join(out) + "\n")
    #    print("Ignoring the extra entries.\n")
    
    this_soname = None
    this_sopath = None

    if len(out) >= 2:
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
    # We'll wipe those later.  Record the relative ones separately.
    abs_rpaths   = []
    rel_rpaths = []
    lines = run('otool', '-l', filename, output=True).split('\n')
    for i in range(0, len(lines)):
        if re.search('cmd LC_RPATH', lines[i]):
            if i+2 >= len(lines):
                continue
            #print('found LC_RPATH: ' + lines[i+2])
            m = re.match(r'^.*?path\s+([^\s]+)', lines[i+2])
            if m:
                rpath_val = m.group(1)
                if re.search(os.getcwd(), rpath_val):
                    # Keep only those in current dir, not system
                    # ones. Not sure about this, but it works.
                    abs_rpaths.append(rpath_val)
                else:
                    rel_rpaths.append(rpath_val)

    return Ret(soname=this_soname, sopath=this_sopath, libs=libs, abs_rpaths=abs_rpaths, rel_rpaths=rel_rpaths)

def required_libs(filename, search_path):
    ''' Returns a dict where the keys are required SONAMEs and the values are proposed full paths. '''
    if get_platform().os == 'linux':
        soname = set(readelf(filename).needed)
        return dict((k,v) for k,v in ldd(filename, search_path).items() if k in soname)
    else:
        return otool(filename).libs

def grep(regex, filename):
    '''Run a regular expression search inside a file'''
    ret = []
    rx = re.compile(regex)
    with open(filename, 'r') as f:
        for line in f:
            m = rx.search(line)
            if m:
                ret.append(m)
    return ret

class DistPrefix(str):
    '''A class so that, for example, if myobj is an instance of
    DistPrefix, myobj.libexec(tool_name) would return
    <myobj base path>/libexec/tool_name.
    What an obfuscated piece of code. One could as well simply implement
    member functions like libexec(toolname) manually rather than doing
    the __getattr__ mumbo-jumbo.'''
    
    def __new__(cls, directory):
        return str.__new__(cls, P.normpath(directory))
    def base(self, *args):
        return P.join(self, *args)

    def __getattr__(self, name):
        def f(*args):
            args = [name] + list(args)
            return self.base(*args)
        return f

def usgscsm_plugin_path(distdir, base):
    '''Return the full path to a given USGS CSM plugin.'''
    out_path = P.join(distdir, 'plugins', 'usgscsm', base)
    return out_path

def rm_f(filename):
    ''' An rm that does not care if the file is not there '''
    try:
        remove(filename)
    except OSError as o:
        if o.errno != errno.ENOENT: # Don't care if it wasn't there
            raise

def mergetree(src, dst, copyfunc):
    """Merge one directory into another.

    The destination directory may already exist.
    If exception(s) occur, an error is raised with a list of reasons.
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
        except shutil.Error as err:
            errors.extend(err.args[0])
        except EnvironmentError as why:
            errors.append((srcname, dstname, str(why)))
    try:
        shutil.copystat(src, dst)
    except OSError as why:
        errors.extend((src, dst, str(why)))
    if errors:
        raise shutil.Error

def strip(filename):
    '''Discard all symbols from this object file with OS specific flags'''
    flags = None

    def linux_flags():
        typ = run('file', filename, output=True)
        if typ.find('current ar archive') != -1:
            return ['-g']
        elif typ.find('SB executable') != -1 or typ.find('SB shared object') != -1:
            save_elf_debug(filename)
            return ['--strip-unneeded', '-R', '.comment']
        elif typ.find('SB relocatable') != -1:
            return ['--strip-unneeded']
        return []
    def osx_flags():
        return ['-S']

    # Get flags from one of the two functions above then run the strip command.
    flags = []
    os_type = get_platform().os
    if os_type == 'linux':
        flags = linux_flags()
    elif os_type == 'osx':
        flags = osx_flags()
    else:
        raise Exception('Unknown platform: ' + os_type)

    flags.append(filename)
    try:
        run('strip', *flags)
    except Exception as e:
        print("Failed running strip with flags: ", flags, ". Got the error: ", e)

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

def fix_paths(filename):
    '''
    Fix paths of the form /home/.../ to be relative to /usr/. This way
    the build environment paths won't leak. This will apply only to text files.
    '''
    # This tool can corrupt non-ascii files, so skip them
    if not is_ascii(filename):
        return
        
    # Read all lines from the file
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
    except Exception as e:
        # In case the file cannot be read, just return
        return

    # Iterate through all lines and replace the paths
    for count in range(len(lines)):
        while True:
            # Use a loop since there can be multiple matches in a single line
            m = re.match(r"^(.*?)(\/home|\/Users)([\/\w\s]+\/)(bin|lib|libexec|include|share|plugins|appdata)(.*?\n)", lines[count])
            if m:
                lines[count] = m.group(1) + "/usr/" + m.group(4) + m.group(5)
            else:
                break

    # Write all lines back to the file
    with open(filename, 'w') as f:
        f.writelines(lines)
        
def set_rpath(filename, toplevel, searchpath, relative_name=True):
    '''For each input file, set the rpath to contain all the input
       search paths to be relative to the top level.'''
      
    # Careful not to corrupt files   
    if not is_lib_or_bin_prog(filename):
        return
        
    assert not any(map(P.isabs, searchpath)), 'set_rpath: searchpaths must be relative to distdir (was given %s)' % (searchpath,)
    if get_platform().os == 'linux':
        rel_to_top = P.relpath(toplevel, P.dirname(filename))
        #small_path = searchpath[0:1] # truncate this as it can't fit
        rpath = '$ORIGIN/../lib'
        # The command below can corrupt files. It should not be necessary
        # since the ASP wrappers set LD_LIBRARY_PATH, and at build time
        # it sets RPATH to be $ORIGIN/../lib.
        # if run('chrpath', '-r', rpath, filename, raise_on_failure = False) is None:
        #     # TODO: Apparently patchelf is better than chrpath when the
        #     # latter fails. Here, can use instead:
        #     # patchelf --set-rpath ':'.join(rpath) filename
        #     pass
        #     # This warning is too verbose.
        #     #logger.warn('Failed to set_rpath on %s' % filename)
    else:
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

        for soname, sopath in info.libs.items():
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
                exec_rpath = P.join('@executable_path', '..', rpath)
                load_rpath = P.join('@loader_path',     '..', rpath)
                if exec_rpath not in info.rel_rpaths:
                    if run('install_name_tool', '-add_rpath', exec_rpath, filename, raise_on_failure = False) is None:
                        logger.warn('Failed to add rpath on %s' % filename)
                if load_rpath not in info.rel_rpaths:
                    if run('install_name_tool', '-add_rpath', load_rpath, filename, raise_on_failure = False) is None:
                        logger.warn('Failed to add rpath on %s' % filename)

        # We'd like to wipe the hard-coded RPATH pointing to the
        # original install directory. The user won't have it, and it
        # causes problems on the build machine, as libraries are
        # loaded from both the new and original locations which
        # results in a subtle crash.
        for abs_rpath in info.abs_rpaths:
            run('install_name_tool', '-delete_rpath', abs_rpath, filename)

def snap_symlinks(src):
    '''Build a list of chained symlink files until we reach a non-link file.'''
    assert src, 'Cannot snap symlink which is NONE'
    assert not P.isdir(src), 'Cannot chase symlinks on a directory'
    if not P.islink(src):
        return [src]

    dst = snap_symlinks(P.join(P.dirname(src), readlink(src)))
    return [src] + dst

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
        if os.path.isdir(control): 
            continue
        if not is_ascii(control): 
            continue

        print('  %s' % P.basename(control))

        # ensure we can read and write (some files have odd permissions)
        st = os.stat(control)
        os.chmod(control, st.st_mode | stat.S_IREAD | stat.S_IWRITE)

        # replace the temporary install directory with the one we're
        # deploying to. (Modify file in-place)
        lines = []
        with open(control,'r') as f:
            lines = f.readlines()
        with open(control,'w') as f:
            for line in lines:
                line = re.sub(r'[\/\.]+[\w\/\.\-]*?' + binary_builder_prefix() + r'\w*[\w\/\.]*?/install', installdir, line)
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
                  P.join(installdir,'lib64')]

    print('Fixing RPATHs')
    for curr_path in SEARCHPATH:
        for extension in library_ext:
            for library in glob(P.join(curr_path,'*.'+extension+'*')):
                if not is_lib_or_bin_prog(library):
                    continue
                print('  %s' % P.basename(library))
                try:
                    set_rpath(library, installdir, map(lambda path: P.relpath(path, installdir), SEARCHPATH), False)
                except:
                    print('  Failed %s' % P.basename(library))

    print('Fixing files in bin/')
    for file in glob(P.join(installdir,'bin','*')):
        if is_ascii(file):
            fix_paths(file)
            continue
        print('  %s' % P.basename(binary))
        try:
            set_rpath(binary, installdir, map(lambda path: P.relpath(path, installdir), SEARCHPATH), False)
        except:
            print('  Failed %s' % P.basename(binary))


if __name__ == '__main__':
    import doctest
    doctest.testmod()
