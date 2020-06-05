#!/usr/bin/env python

from __future__ import with_statement, print_function

import errno
import inspect
import os
import os.path as P
import platform
import subprocess
import sys
import logging
import copy, re

if sys.version_info < (3, 0, 0):
    # Python 2
    from urllib2 import urlopen
    from urlparse import urlparse
else:
    # Python 3
    from urllib.request import urlopen
    from urllib.parse import urlparse

from collections import namedtuple
from functools import wraps, partial
from glob import glob
from shutil import rmtree

from BinaryDist import which, mkdir_f, get_platform, run, hash_file

global logger
logger = logging.getLogger()

# Replace a line in a file with another
def replace_line_in_file(filename, line_in, line_out):
    lines = []
    with open(filename,'r') as f:
        lines = f.readlines()
    with open(filename,'w') as f:
        for line in lines:
            line = line.rstrip('\n')
            if line == line_in:
                line = line_out
            f.write( line + '\n')

def get_prog_version(prog):
    try:
        p = subprocess.Popen([prog,"--version"], stdout=subprocess.PIPE)
        out, err = p.communicate()
        if out is not None:
            out = out.decode('utf-8')
    except:
        raise Exception("Could not find: " + prog)
    if p.returncode != 0:
        raise Exception("Checking " + prog + " version caused errors")

    m = re.match("^.*?(\d+\.\d+)", out)
    if not m:
        raise Exception("Could not find " + prog + " version")
    return float(m.group(1))

class PackageError(Exception):
    def __init__(self, pkg, message):
        super(PackageError, self).__init__('Package[%s] %s' % (pkg.pkgname, message))
class HelperError(Exception):
    def __init__(self, tool, env, message):
        # This is helpful when trying to reproduce the environment in which
        # things failed.
        print("Environment:")
        for key in env:
            val=env[key]
            print("export " + key + '=\'' + val + '\'')
        super(HelperError, self).__init__('Command[%s] %s\nEnv%s' % (tool, message, env))

try:
    from termcolor import colored
except ImportError:
    def colored(value, *unused_args, **unused_kw):
        return value

def _message(*args, **kw):
    '''Print a message color coded according to a severity flag'''
    severity = kw.get('severity', 'info')
    del kw['severity']

    if severity == 'info':
        args = [colored(i, 'blue', attrs=['bold']) for i in args]
        print(*args, **kw)
    elif severity == 'warn':
        args = [colored(i, 'yellow', attrs=['bold']) for i in ['WARNING:'] + list(args)]
    elif severity == 'error':
        args = [colored(i, 'red', attrs=['bold']) for i in ['ERROR:'] + list(args)]
        print(*args, **kw)
    else:
        raise Exception('Unknown severity')

# Set up three output print functions with the color-coding built in.
info  = partial(_message, severity='info')
warn  = partial(_message, severity='warn')
error = partial(_message, severity='error')

# Return a list of paths where this program is present
def program_paths(program, check_help=False):
    def is_exec(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    def has_help(fpath):
        try:
            FNULL = open(os.devnull,'w')
            subprocess.check_call([fpath,"--help"],stdout=FNULL,stderr=FNULL)
            return True
        except subprocess.CalledProcessError:
            return False

    paths=[]
    for path in os.environ["PATH"].split(os.pathsep):
        exec_file = os.path.join( path, program )
        if is_exec(exec_file):
            if not check_help or has_help(exec_file):
                paths.append(exec_file)
                                    
    return paths

def program_exists(program,check_help=False):
    return len(program_paths(program, check_help))

def get_cores():
    try:
        n = os.sysconf('SC_NPROCESSORS_ONLN')
        if n:
            return n
        return 2
    except:
        return 2

def find_file(filename, path=None):
    '''Search for a file in the system PATH or provided path string'''
    if path is None:
        path = os.environ.get('PATH', [])
    for dirname in path.split(':'):
        possible = P.join(dirname, filename)
        if P.isfile(possible):
            return possible
    raise Exception('Could not find file %s in path[%s]' % (filename, path))

def die(*args, **kw):
    '''Quit, printing the provided error message.'''
    error(*args, **kw)
    sys.exit(kw.get('code', -1))

def stage(f):
    '''Wraps a function to provide some standard output formatting.
       Only compatible with the Package class!'''
    @wraps(f)
    def wrapper(self, *args, **kw):
        stage = f.__name__
        info('========== %s.%s ==========' % (self.pkgname, stage))
        try:
            return f(self, *args, **kw)
        except HelperError as e:
            raise PackageError(self, 'Stage[%s] %s' % (stage,e))
    return wrapper

class Environment(dict):
    '''Dictionary object containing the required environment info'''
    def __init__(self, **kw):
        '''Constructor requires several directory paths to be specified'''
        self.update(dict(
            HOME           = kw['BUILD_DIR'],
            DOWNLOAD_DIR   = kw['DOWNLOAD_DIR'],
            BUILD_DIR      = kw['BUILD_DIR'],
            INSTALL_DIR    = kw['INSTALL_DIR'],
            NOINSTALL_DIR  = P.join(kw['INSTALL_DIR'], 'noinstall'),
            ISISROOT       = P.join(kw['INSTALL_DIR'], 'isis'),
            GIT_SSL_NO_VERIFY = 'true' # to avoid complaints on pfe27
        ))
        self.update(kw)
        self['ISIS3RDPARTY'] = P.join(self['ISISROOT'], '3rdParty', 'lib')

        self.create_dirs()

    def create_dirs(self):
        '''Create all required directories'''
        for d in ('DOWNLOAD_DIR', 'BUILD_DIR', 'INSTALL_DIR', 'NOINSTALL_DIR'):
            try:
                os.makedirs(self[d])
            except OSError as o:
                if o.errno != errno.EEXIST: # Don't care if it already exists
                    raise

    def copy_set_default(self, **kw):
        '''Create a copy of this object with default values provided in case they are missing'''
        e = Environment(**self) # Create copy of this object
        for k,v in kw.items():
            if k not in e:
                e[k] = v
        return e

    def append(self, key, value):
        '''Safely append the value to a list of entries with the given key'''
        if key in self:
            self[key] += ' ' + value
        else:
            self[key] = value

    def append_many(self, key_seq, value):
        '''Call append() with the same value for multiple keys.'''
        for k in key_seq:
            self.append(k, value)

def unique_compiler_flags(iflags):
    '''Prune duplicate flags from a list'''
    #This is used instead of a set to preserve flag order

    oflags = []
    used_flags = set()
    for keyword in iflags.split():
        if keyword not in used_flags:
            used_flags.add(keyword)
            oflags.append(keyword)
    return " ".join(oflags)

def get(url, output=None):
    '''Fetch a file from a url and write to "output"'''
    # Provide a default output path
    if output is None:
        output = P.basename(urlparse(url).path)
        base = output
    else:
        base = P.basename(output)

    # Read from the URL and write to the output file in blocks
    BLOCK_SIZE = 16384
    with open(output, 'wb') as f:
        try:
            r = urlopen(url)
        except urllib2.HTTPError as e:
            print("Failed to get: " + url + ", error was: " + str(e))
            raise HelperError('urlopen', None, '%s: %s' % (url, e))

        current = 0
        size = int(r.info().get('Content-Length', -1))
        
        while True: # Download until we run out of data
            block = r.read(BLOCK_SIZE)
            if not block:
                break # Block read failed or completed
            current += len(block)
            if size < 0: # Unknown size
                info('\rDownloading %s: %i kB' % (base, current/1024.), end='')
            else: # Known size
                info('\rDownloading %s: %i / %i kB (%0.2f%%)' % (base, current/1024., size/1024., current*100./size), end='')
            f.write(block) # Write to disk
        info('\nDone')
        
class Package(object):
    '''Class to represent a single package that needs to be built.
       This class assumes the code for the package is posted online as a compressed file
       and it can be built with configure -> make -> make install.'''
    src     = None
    chksum  = None
    patches = []
    patch_level = None

    def __init__(self, env):
        '''Construct with the environment info'''
        self.pkgname = self.__class__.__name__

        # Yes, it is possible to get a / into a class name.
        # os.path.join fails pathologically there. So catch that specific case.
        assert '/' not in self.pkgname

        self.pkgdir  = P.abspath(P.dirname(inspect.getfile(self.__class__)))
        #info(self.pkgdir)
        self.tarball = None
        self.workdir = None
        self.env = copy.deepcopy(env) # local copy of the environment, not affecting other packages
        self.arch = get_platform(self)

        self.env['CPPFLAGS'] = self.env.get('CPPFLAGS', '') + ' -I%(INSTALL_DIR)s/include' % self.env
        self.env['CXXFLAGS'] = self.env.get('CXXFLAGS', '') + ' -I%(INSTALL_DIR)s/include' % self.env
        # If we include flags to directories that don't exist, we
        # cause compiler tests to fail.
        if P.isdir(self.env['ISIS3RDPARTY']):
            self.env['LDFLAGS'] = self.env.get('LDFLAGS', '') + ' -L%(ISIS3RDPARTY)s' % self.env
        if P.isdir(self.env['INSTALL_DIR']+'/lib'):
            self.env['LDFLAGS'] = self.env.get('LDFLAGS', '') + ' -L%(INSTALL_DIR)s/lib' % self.env
        if P.isdir(self.env['INSTALL_DIR']+'/lib64'):
            self.env['LDFLAGS'] = self.env.get('LDFLAGS', '') + ' -L%(INSTALL_DIR)s/lib64' % self.env

        # Remove repeated entries in CPPFLAGS, CXXFLAGS, LDFLAGS
        self.env['CPPFLAGS'] = unique_compiler_flags(self.env['CPPFLAGS'])
        self.env['CXXFLAGS'] = unique_compiler_flags(self.env['CXXFLAGS'])
        self.env['CFLAGS'  ] = unique_compiler_flags(self.env['CFLAGS'  ])
        self.env['LDFLAGS' ] = unique_compiler_flags(self.env['LDFLAGS' ])

    @stage
    def fetch(self, skip=False):
        '''After fetch, the source code should be available.'''

        assert self.src,    'No src defined for package %s' % self.pkgname
        assert self.chksum, 'No chksum defined for package %s' % self.pkgname

        if isinstance(self.src, str):
            self.src = (self.src,)
            self.chksum = (self.chksum,)

        assert len(self.src) == len(self.chksum), 'len(src) and len(chksum) should be the same'

        # Do two attempts, perhaps the locally cached version of the tarball
        # is not up-to-date, in that case remove it and try again.
        is_good = False
        chksum = ""
        curr_chksum = ""
        for i in range(0, 2):

            for src, chksum in zip(self.src, self.chksum):
                # Get the tarball path and if we don't have it, download it from the url (src)
                self.tarball = P.join(self.env['DOWNLOAD_DIR'], P.basename(urlparse(src).path))
                if not P.isfile(self.tarball):
                    if skip: raise PackageError(self, 'Fetch is skipped and no src available')
                    get(src, self.tarball)

                # See if we got the expected checksum
                curr_chksum = hash_file(self.tarball)
                if curr_chksum != chksum:
                    os.remove(self.tarball) # Remove the bad tarball so we fetch it on the second pass
                else:
                    is_good = True

        if not is_good:
            raise PackageError(self, 'Checksum on file[%s] failed. Expected %s but got %s. Removed!'
                               % (self.tarball, chksum, curr_chksum) )

    @stage
    def unpack(self):
        '''After unpack, the source code should be unpacked and should have any
        necessary patches applied.'''

        output_dir = P.join(self.env['BUILD_DIR'], self.pkgname)

        self.remove_build(output_dir) # Throw out the old content
        ext = P.splitext(self.tarball)[-1]
        
        # Call the appropriate tool to unpack the code into the build directory
        if ext == '.zip':
            self.helper('unzip', '-d', output_dir, self.tarball)
        else:
            flags = 'xf'
            if ext == '.Z' or ext.endswith('gz'):
                flags = 'z' + flags
            elif ext.endswith('xz'):
                flags = 'J' + flags
            elif ext.endswith('bz2'):
                flags = 'j' + flags
            self.helper('tar', flags, self.tarball, '-C',  output_dir)

        # If the user didn't provide a work directory define it as the
        # single directory output from tarball.
        if self.workdir is None:
            self.workdir = glob(P.join(output_dir, "*"))
            if len(self.workdir) != 1:
                raise PackageError(self, 'Badly-formed tarball[%s]: there should be 1 file in the output dir [%s], but there are %i' %
                                   (self.tarball, output_dir, len(self.workdir)))

            self.workdir = self.workdir[0]

        self._apply_patches()

        # Prepend the work dir to the include/link dirs, to ensure the newest
        # version of any software is used. This is a bugfix.
        self.env['CPPFLAGS'] = '-I' + self.workdir + '/include ' + self.env['CPPFLAGS']
        self.env['CXXFLAGS'] = '-I' + self.workdir + '/include ' + self.env['CXXFLAGS']
        self.env['CFLAGS'  ] = '-I' + self.workdir + '/include ' + self.env['CFLAGS']
        #self.env['LDFLAGS' ] = '-L' + self.workdir + '/lib ' + self.workdir + '/lib64 '  + self.env['LDFLAGS']
    @stage
    def configure(self, other=(), with_=(), without=(), enable=(), disable=(), configure='./configure'):
        '''After configure, the source code should be ready to build.'''

        # Generate a list of "enable-X", "without-Y" etc strings according to the inputs
        args = list(other)
        for flag in 'enable', 'disable', 'with', 'without':
            # Set "value" equal to the corresponding input argument
            if flag == 'with': # Could not use "with" as a variable name because it is a Python word.
                value = locals()['with_']
            else:
                value = locals()[flag]

            if isinstance(value, str):
                args += ['--%s-%s' % (flag, value)]
            else: # Value is a list of strings
                args += ['--%s-%s'  % (flag, feature) for feature in value]
                
        # Did they pass a prefix? If not, add one.
        if len([True for a in args if a[:9] == '--prefix=']) == 0:
            args.append('--prefix=%(INSTALL_DIR)s' % self.env)

        # Call the package's configure script with the parsed arguments
        self.helper('./configure', *args)

    @stage
    def compile(self, cwd=None):
        '''After compile, the compiled code should exist.'''

        cmd = ('make', )
        if 'MAKEOPTS' in self.env:
            cmd += tuple(self.env['MAKEOPTS'].split(' '))

        e = self.env.copy_set_default(prefix = self.env['INSTALL_DIR'])
        self.helper(*cmd, env=e, cwd=cwd)

    @stage
    def install(self, cwd=None):
        '''After install, the binaries should be on the live filesystem.'''

        e = self.env.copy_set_default(prefix = self.env['INSTALL_DIR'])

        cmd = ('make', 'install')
        self.helper(*cmd, env=e, cwd=cwd)

    @staticmethod
    def build(pkg, skip_fetch=False):
        '''Shortcut to call all steps for a package with no arguments'''
        # If it's a type, we instantiate it. Otherwise, we just use whatever it is.
        assert isinstance(pkg, Package)
        pkg.fetch(skip=skip_fetch)
        pkg.unpack()
        pkg.configure()
        pkg.compile()
        pkg.install()

    def _apply_patches(self):
        # self.patches could be:
        #    list of strings, interpreted as a list of patches
        #    a string, interpreted as a patch or a dir of patches
        patches = []
        if self.patches is None:
            return
        elif isinstance(self.patches, str):
            # Grab all of the patch file paths out of the provided directory
            full = P.join(self.pkgdir, self.patches)

            if P.exists(full):
                pass
            elif P.exists(self.patches):
                full = self.patches
            else:
                raise PackageError(self, 'Unknown patch: %s' % full)

            if P.isdir(full):
                patches = sorted(glob(P.join(full, '*')))
            else:
                patches = [full]
        else: # Input is already a list of patch files
            patches = self.patches

        def _apply(patch):
            '''Helper function to apply a patch with a custom self.patch_level'''
            if self.patch_level is None:
                self.helper('patch', '-p1', '-i', patch)
            else:
                self.helper('patch', self.patch_level, '-i', patch)

        # We have a list of patches now, but we can't trust they're all there
        for p in patches:
            if p.endswith('~') or p.endswith('#'): # Skip junk file paths
                continue
            if not P.isfile(p):
                raise PackageError(self, 'Unknown patch: %s' % p)
            _apply(p) # The patch file is there, apply it!


    def helper(self, *args, **kw):
        '''Run a command line command with some extra argument handling'''
        info(' '.join(args))
        kw['stdout'] = kw.get('stdout', sys.stdout)
        kw['stderr'] = kw.get('stderr', kw['stdout'])

        if kw.get('cwd', None) is None:
            kw['cwd'] = self.workdir
        if kw.get('env', None) is None:
            kw['env'] = self.env
        kw['raise_on_failure'] = False
        kw['want_stderr'] = True

        try:
            out, err = run(*args, **kw)
            if out is None:
                return out, err
            if out is False:
                raise HelperError(args[0], kw['env'], err)
            return out, err
        except (TypeError,) as e:
            raise Exception('%s\n%s' % (e.message, '\t\n'.join(['\t%s=%s%s' % (name, type(value).__name__, value) for name,value in kw['env'].iteritems() if not isinstance(value, str)])))
        except (OSError, subprocess.CalledProcessError) as e:
            raise HelperError(args[0], kw['env'], e)

    def copytree(self, src, dest, args=(), delete=True):
        '''rsync wrapper to duplicate a directory to a new location'''
        call = ['rsync', '-a']
        if delete:
            call.append('--delete')
        call += args
        call += [src, dest]
        self.helper(*call)

    # TODO: Delete the installed files!
    def remove_build(self, output_dir):
        '''Make output_dir into an empty directory, deleting everything that is inside.'''
        if P.isdir(output_dir):
            info("Removing old build directory: " + output_dir)
            rmtree(output_dir, False)
        os.makedirs(output_dir)

class GITPackage(Package):
    ''' A git package does not have a checksum. Here we interpret
        this variable as the commit id. This is a bit confusing.
        The goal here is to not re-build a git package if
        we already built it with given commit id.'''
    chksum = None
    fast = False
    def __init__(self, env):
        super(GITPackage, self).__init__(env)
        self.localcopy = P.join(env['DOWNLOAD_DIR'], 'git', self.pkgname)

        # Git gets confused by LD_LIBRARY_PATH but some
        # other tools need it.
        self.local_env = self.env.copy_set_default()
        self.local_env["LD_LIBRARY_PATH"] = ""
        
        if 'FAST' in env and int(env['FAST']) != 0:
            self.fast = True

        if self.chksum is None:
            # If the user did not specify which commit to fetch,
            # we'll fetch the latest. Store its commit hash.
            for line in self.helper('git', 'ls-remote', '--heads', self.src,
                                    env = self.local_env,
                                    stdout=subprocess.PIPE)[0].split('\n'):
                tokens = line.split()
                if len(tokens) > 1 and tokens[1] == 'refs/heads/master':
                    self.chksum = tokens[0]

    def _git(self, *args):
        '''Call a git command from the local folder we are using for this package.'''
        cmd = ['git', '--git-dir', self.localcopy]
        cmd.extend(args)
        self.helper(*cmd, env = self.local_env)

    @stage
    def fetch(self, skip=False):
        '''Override the fetch function to call git fetch or git clone'''
        if P.exists(self.localcopy):
            if skip: return
            self._git('fetch', 'origin')
        else:
            if skip: raise PackageError(self, 'Fetch is skipped and no src available')
            self.helper('git', 'clone', '--mirror', self.src, self.localcopy,
                        env = self.local_env)

    @stage
    def unpack(self):
        '''Go from the location we cloned into to a different working directory 
           containing the desired commit'''
        output_dir = P.join(self.env['BUILD_DIR'], self.pkgname)
        self.workdir = P.join(output_dir, self.pkgname + '-git')

        # If fast, update and build in existing directory
        # (assuming it exists).
        if self.fast:
            return
        
        #  Delete the existing build and start over.
        if os.path.exists(output_dir):
            self.remove_build(output_dir)
            
        mkdir_f(self.workdir)
            
        self.helper('git', 'clone', '--recurse-submodules', self.localcopy, self.workdir,
                    env = self.local_env)
        
        # Checkout a specific commit
        if self.chksum is not None:
            cmd = ('git', 'checkout', self.chksum)
            self.helper(*cmd, cwd=self.workdir, env = self.local_env)
            
        self._apply_patches()

class SVNPackage(Package):
    '''Package class for handling SVN repos'''

    def __init__(self, env):
        super(SVNPackage, self).__init__(env)
        self.localcopy = P.join(env['DOWNLOAD_DIR'], 'svn', self.pkgname)

    def _get_current_url(self, path):
        ''''''
        for line in self.helper('svn', 'info', path, stdout=subprocess.PIPE)[0].split('\n'):
            tokens = line.split()
            if tokens[0] == 'URL:':
                return tokens[1]

    @stage
    def fetch(self, skip=False):
        '''Call SVN update or checkout to download the code'''
        try:
            if P.exists(self.localcopy):
                if skip: return
                url = self._get_current_url(self.localcopy)
                if url == self.src:
                    self.helper('svn', 'update', self.localcopy)
                else:
                    self.helper('svn', 'switch', self.src, self.localcopy)
            else:
                if skip: raise PackageError(self, 'Fetch is skipped and no src available')
                self.helper('svn', 'checkout', self.src, self.localcopy)
        except HelperError as e:
            warn('svn failed (removing %s): %s' % (self.localcopy, e))
            rmtree(self.localcopy)
            self.helper('svn', 'checkout', self.src, self.localcopy)

    @stage
    def unpack(self):
        '''Go from the location we checked out into to a different working directory'''
        output_dir = P.join(self.env['BUILD_DIR'], self.pkgname)
        self.remove_build(output_dir)
        self.workdir = P.join(output_dir, self.pkgname + '-svn')

        cmd = ('svn', 'export', self.localcopy, self.workdir)
        self.helper(*cmd, cwd=output_dir)

        self._apply_patches()

class CMakePackage(Package):
    '''Package variant that must be built using CMake'''
    # Don't allow these to be specified by the user, we need control over these.
    BLACKLIST_VARS = (
            'CMAKE_BUILD_TYPE',
            'CMAKE_INSTALL_PREFIX',
            'CMAKE_OSX_ARCHITECTURES',
            'CMAKE_OSX_DEPLOYMENT_TARGET',
            'CMAKE_OSX_SYSROOT',
    )

    def __init__(self, env):
        super(CMakePackage, self).__init__(env)

    @stage
    def configure(self, other=(), enable=(), disable=(), with_=(), without=()):
        # The tradition is to use "build", but some tools include a
        #  file called "BUILD" which conflicts in OSX.
        self.builddir = P.join(self.workdir, 'build_binarybuilder')

        def remove_danger(files, dirname, fnames):
            '''Function to find all CMakeLists.txt files in a set of files'''
            files.extend([P.join(dirname,f) for f in fnames if f == 'CMakeLists.txt'])

        # Generate a custom "sed" command to remove all blacklisted CMake 
        # variables from the existing CMakeLists.txt files
        #files = []
        #P.walk(self.workdir, remove_danger, files) # Find all CMakeLists files
        #cmd = ['sed', '-ibak']
        # strip out vars we must control from every CMakeLists.txt
        #for var in self.BLACKLIST_VARS:
        #    cmd.append('-e')
        #    cmd.append('s/^[[:space:]]*[sS][eE][tT][[:space:]]*([[:space:]]*%s.*)/#BINARY BUILDER IGNORE /g' % var)
        #cmd.extend(files)
        #self.helper(*cmd)

        # Some of these build rules were breaking recent packages (ISIS etc) so they had to be turned off.
        #  If it breaks something else then we will find out why these changes were there!

        # Write out a custom cmake rules file
        build_rules = P.join(self.env['BUILD_DIR'], 'my_rules.cmake')
        with open(build_rules, 'w') as f:
            print('SET (CMAKE_C_COMPILER "%s" CACHE FILEPATH "C compiler" FORCE)' % (find_file(self.env['CC'], self.env['PATH'])), file=f)
            #print('SET (CMAKE_C_COMPILE_OBJECT "<CMAKE_C_COMPILER> <DEFINES> %s <FLAGS> -o <OBJECT> -c <SOURCE>" CACHE STRING "C compile command" FORCE)' % (self.env.get('CPPFLAGS', '')), file=f)
            print('SET (CMAKE_CXX_COMPILER "%s" CACHE FILEPATH "C++ compiler" FORCE)' % (find_file(self.env['CXX'], self.env['PATH'])), file=f)
            print('SET (CMAKE_Fortran_COMPILER "%s" CACHE FILEPATH "Fortran compiler" FORCE)' % (find_file(self.env['GFORTRAN'], self.env['PATH'])), file=f)
            #print('SET (CMAKE_CXX_COMPILE_OBJECT "<CMAKE_CXX_COMPILER> <DEFINES> %s <FLAGS> -o <OBJECT> -c <SOURCE>" CACHE STRING "C++ compile command" FORCE)' % (self.env.get('CPPFLAGS', '')), file=f)

        # Build up the main cmake command using our environment variables
        cmd = ['cmake']
        args = [
            '-DCMAKE_INSTALL_PREFIX=%(INSTALL_DIR)s' % self.env,
            '-DCMAKE_BUILD_TYPE=MyBuild',
            '-DCMAKE_USER_MAKE_RULES_OVERRIDE=%s' % build_rules#,
        #    '-DCMAKE_SKIP_RPATH=YES',
#            '-DCMAKE_INSTALL_DO_STRIP=OFF',
        ]

#        if self.arch.os == 'osx':
#            args.append('-DCMAKE_OSX_ARCHITECTURES=%s' % self.env['OSX_ARCH'])
#            args.append('-DCMAKE_OSX_SYSROOT=%s' % self.env['OSX_SYSROOT'])
#            args.append('-DCMAKE_OSX_DEPLOYMENT_TARGET=%s' % self.env['OSX_TARGET'])

        # Include commands for the input enable/disable commands
        for arg in disable:
            args.append('-DENABLE_%s=OFF' % arg)
        for arg in enable:
            args.append('-DENABLE_%s=ON' % arg)
        for arg in without:
            args.append('-DWITH_%s=OFF' % arg)
        for arg in with_:
            args.append('-DWITH_%s=ON' % arg)

        args.extend([
            '-DCMAKE_PREFIX_PATH=%(INSTALL_DIR)s' % self.env,
            '-DLIB_POSTFIX=',
        ])

        [args.append(arg) for arg in other]

        try:
            os.makedirs(self.builddir)
        except OSError as e:
            pass

        cmd = cmd + args + [self.workdir]

        # Finally, run the cmake command!
        self.helper(*cmd, cwd=self.builddir)

    @stage
    def compile(self):
        '''Compile works the same as the base class'''
        super(CMakePackage, self).compile(cwd=self.builddir)

    @stage
    def install(self):
        '''Install works the same as the base class'''
        super(CMakePackage, self).install(cwd=self.builddir)

# TODO: Duplicated in Packages.py!
def print_qt_config(cppflags, config, bindir, includedir, libdir):
    '''Print out a bunch of QT stuff'''
    qt_pkgs = ('QtConcurrent QtCore QtGui QtNetwork QtSql QtSvg QtWidgets QtXml QtXmlPatterns QtPrintSupport QtTest'
               + ' QtQml QtQuick QtOpenGL QtMultimedia QtMultimediaWidgets QtDBus')
    print('QT_ARBITRARY_MODULES="%s"' % qt_pkgs, file=config)
    qt_cppflags=[]
    qt_libs=['-L%s' % libdir]
    for module in qt_pkgs.split():
        qt_cppflags.append('-I%s/%s' % (includedir, module))
        qt_libs.append('-l%s' % module.replace('Qt','Qt5'))
    print('PKG_ARBITRARY_QT_LIBS="%s"' %  ' '.join(qt_libs), file=config)
    print('PKG_ARBITRARY_QT_MORE_LIBS="-lpng -lz -lssl -lcrypto"', file=config)
    print('MOC=%s' % (P.join(bindir, 'moc')),file=config)
    cppflags.extend(qt_cppflags)

def write_vw_config(prefix, installdir, arch, config_file):
    '''Generate a config file required by Vision Workbench'''

    print('Writing ' + config_file)
    base       = '$BASE'
    includedir = P.join(base, 'include')
    libdir     = P.join(base, 'lib')
    bindir     = P.join(base, 'bin')
    cppflags = ['-I' + includedir]

    # Enable
    enable_features = 'debug optimize rpath as_needed no_undefined'.split()
    if arch.os != 'osx': # Currently our OSX build does not support this feature!
        enable_features.append('sse')
    enable_pkgs = ('jpeg png geotiff geos gdal proj4 z ilmbase openexr boost flapack ' +
                  'protobuf flann opencv').split()
    enable_modules  = ('camera mosaic interestpoint cartography hdr stereo ' +
                       'geometry tools bundleadjustment').split()

    # Disable
    disable_features = 'pkg_paths_default static'.split()
    disable_pkgs = ('tiff hdr tcmalloc clapack slapack ').split()
    disable_modules = 'python flood_detect'.split() # Python is needed for the googlenasa project

    with open(config_file, 'w') as config:

        print('# The path to the installed 3rd party libraries', file=config)
        print('BASE=%s' % installdir, file=config)
        print('', file=config) # newline

        print('# Installation prefix', file=config)
        print('PREFIX=%s' % prefix, file=config)
        print('', file=config) # newline

        for feature in enable_features:
            print('ENABLE_%s=yes' % feature.upper(), file=config)
        for feature in disable_features:
            print('ENABLE_%s=no' % feature.upper(), file=config)
        print('', file=config) # newline

        for module in enable_modules:
            print('ENABLE_MODULE_%s=yes' % module.upper(), file=config)
        for module in disable_modules:
            print('ENABLE_MODULE_%s=no' % module.upper(), file=config)
        print('', file=config) # newline

        for pkg in enable_pkgs:
            print('HAVE_PKG_%s=%s' % (pkg.upper(), base),
                  file=config)
            print('PKG_%s_CPPFLAGS="-I%s"' % (pkg.upper(), includedir),
                  file=config)
            if pkg == 'gdal':
                print('PKG_%s_LDFLAGS="-L%s -lgeotiff -lproj -ltiff -lgeos -lgeos_c -ljpeg -lpng -lz -lopenjp2"'  % (pkg.upper(), libdir), file=config)
            else:
                print('PKG_%s_LDFLAGS="-L%s"'  % (pkg.upper(), libdir), file=config)

        for pkg in disable_pkgs:
            print('HAVE_PKG_%s=no' % pkg.upper(), file=config)
        print('', file=config) # newline

        # Specify executables we use
        print('PROTOC=%s' % (P.join(bindir, 'protoc')),file=config)
        print('', file=config) # newline

        print('CPPFLAGS="' + ' '.join(cppflags) + '"', file=config)
        if arch.os == 'osx':
            # To do: Test removing -rpath from cflags and cxxflags
            print('CFLAGS="-arch x86_64 -Wl,-rpath -Wl,%s"' % base,
                  file=config)
            print('CXXFLAGS="-arch x86_64 -Wl,-rpath -Wl,%s"' % base,
                  file=config)
            print('LDFLAGS="-Wl,-rpath -Wl,%s"' % base, file=config)
        print('', file=config) # newline

class Apps:
    disable_modules = ''
    enable_modules  = 'core camera spiceio isisio sessions gui'

    disable_apps = \
                 'demprofile plateorthoproject results \
                 rmax2cahvor rmaxadjust orthoproject'
    enable_apps = \
                'bundle_adjust datum_convert dem_geoid dem_mosaic disparitydebug \
                geodiff hsvmerge lronacjitreg mapproject mer2camera orbitviz \
                point2dem point2las point2mesh pc_align rpc_gen \
                sfs stereo tif_mosaic wv_correct image_calc pc_merge pansharp'
    install_pkgs = \
                 'boost openscenegraph flapack arbitrary_qt curl    \
                 suitesparse amd colamd cholmod glog ceres flann dsk spice qwt gsl \
                 geos xercesc protobuf z ilmbase openexr jpeg  \
                 laszip liblas geoid isis superlu geotiff gdal libnabo \
                 eigen libpointmatcher proj4 gflags theia'
    vw_pkgs     = \
            'vw_core vw_math vw_image vw_fileio vw_camera \
             vw_stereo vw_cartography vw_interest_point vw_geometry'
    off_pkgs    = \
             'qt_qmake clapack slapack kakadu gsl_hasblas apple_qwt'

def write_asp_config(use_env_flags, prefix, installdir, vw_build, arch,
                     geoid, config_file):
    '''Generate a config file required by Stereo Pipeline'''
    print('Writing ' + config_file)

    disable_apps = Apps.disable_apps.split()
    enable_apps  = Apps.enable_apps.split()
    off_pkgs     = Apps.off_pkgs.split()
    install_pkgs = Apps.install_pkgs.split()
    vw_pkgs      = Apps.vw_pkgs.split()
    base         = '$BASE'
    includedir   = P.join(base, 'include')
    libdir       = P.join(base, 'lib')
    lib64dir     = P.join(base, 'lib64')
    bindir       = P.join(base, 'bin')

    # To do: Test removing -O3 and -g, as well as use_env_flags
    cflags   = ['-O3', '-g', '-fPIC']
    cxxflags = ['-O3', '-g', '-fPIC']
    cppflags = ['-I' + includedir]
    ldflags  = ['-L' + libdir, '-L' + lib64dir, '-Wl,-rpath', '-Wl,' + base,
                ' -Wl,-rpath,'+libdir+' -Wl,-rpath,'+lib64dir]

    with open(config_file, 'w') as config:

        print('# The path to the installed 3rd party libraries', file=config)
        print('BASE=%s' % installdir, file=config)
        print('', file=config) # newline

        print('# The location of the VW install directory', file=config)
        print('VW=' + vw_build, file=config)
        print('', file=config) # newline

        print('# Installation prefix', file=config)
        print('PREFIX=' + prefix, file=config)
        print('', file=config) # newline

        print('ENABLE_DEBUG=yes', file=config)
        print('ENABLE_OPTIMIZE=yes', file=config)
        print('ENABLE_RPATH=yes', file=config)
        print('ENABLE_STATIC=no', file=config)
        print('ENABLE_PKG_PATHS_DEFAULT=no', file=config)

        if arch.os == 'osx':
            cflags.extend(['-arch x86_64'])
            cxxflags.extend(['-arch x86_64'])
            ldflags.extend(['-F' + libdir])

        for module in Apps.disable_modules.split():
            print('ENABLE_MODULE_%s=no' % module.upper(), file=config)
        for module in Apps.enable_modules.split():
            print('ENABLE_MODULE_%s=yes' % module.upper(), file=config)

        print('\n# Applications', file=config)
        for app in disable_apps:
            print('ENABLE_APP_%s=no' % app.upper(), file=config)
        for app in enable_apps:
            print('ENABLE_APP_%s=yes' % app.upper(), file=config)

        print('\n# Dependencies', file=config)
        for pkg in install_pkgs:
            if pkg == 'geoid':
                cppflags.extend(['-DGEOID_PATH=' + base + '/share/geoids'])

        # For as many packages as possible use 'yes' instead of
        # '$BASE' to cut down on the auto-generated compile commands.
        pkg_needs_path_list = ['boost', 'spice', 'eigen', 'isis', 'libpointmatcher', 'superlu', 'geoid', 'geos']
        for pkg in install_pkgs:
            if pkg.lower() in pkg_needs_path_list:
                print('HAVE_PKG_%s=%s' % (pkg.upper(), base), file=config)
            else:
                print('HAVE_PKG_%s=yes' % pkg.upper(), file=config)

        for pkg in vw_pkgs:
            print('HAVE_PKG_%s=$VW' % pkg.upper(), file=config)
        for pkg in off_pkgs:
            print('HAVE_PKG_%s=no' % pkg.upper(), file=config)

        print_qt_config(cppflags, config, bindir, includedir, libdir)

        print('PROTOC=%s' % (P.join(bindir, 'protoc')),file=config)
        print('', file=config) # newline

        # Add include directories for some modules that put their includes in a sub-folder.
        cppflags.extend(["-I%s/eigen3"  % includedir])
        cppflags.extend(["-I%s/pcl-1.8" % includedir])
        cppflags.extend(["-I%s/isis3"   % includedir])

        if not use_env_flags:
            print('CFLAGS="'   + ' '.join(cflags)   + '"', file=config)
            print('CXXFLAGS="' + ' '.join(cxxflags) + '"', file=config)

        print('CPPFLAGS="' + ' '.join(cppflags) + '"', file=config)
        print('LDFLAGS="'  + ' '.join(ldflags)  + '"', file=config)

