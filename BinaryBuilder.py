#!/usr/bin/env python

from __future__ import with_statement, print_function

import errno
import inspect
import os
import os.path as P
import platform
import subprocess
import sys
import urllib2
import logging

from collections import namedtuple
from functools import wraps, partial
from glob import glob
from hashlib import sha1
from shutil import rmtree
from urlparse import urlparse

global logger
logger = logging.getLogger()

def get_platform(pkg=None):
    system  = platform.system()
    machine = platform.machine()
    p = namedtuple('Platform', 'os bits osbits system machine prettyos dist_name dist_version')

    if system == 'Linux':
        dist = platform.linux_distribution(full_distribution_name=0)
        name = dist[0]
        ver  = dist[1]
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

def get_gcc_version():
    p = subprocess.Popen(["gcc","--version"], stdout=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0:
        raise Exception("Checking GCC version caused errors")
    out = out.split('\n')[0]
    return float(out[out.find(')')+2:out.rfind('.')])

class PackageError(Exception):
    def __init__(self, pkg, message):
        super(PackageError, self).__init__('Package[%s] %s' % (pkg.pkgname, message))
class HelperError(Exception):
    def __init__(self, tool, env, message):
        super(HelperError, self).__init__('Command[%s] %s\nEnv%s' % (tool, message, env))

def hash_file(filename):
    with file(filename, 'rb') as f:
        return sha1(f.read()).hexdigest()

def run(*args, **kw):
    need_output      = kw.pop('output', False)
    raise_on_failure = kw.pop('raise_on_failure', True)
    want_stderr      = kw.pop('want_stderr', False)
    kw['stdout']     = kw.get('stdout', subprocess.PIPE)
    kw['stderr']     = kw.get('stderr', subprocess.PIPE)

    logger.debug('run: [%s] (wd=%s)' % (' '.join(args), kw.get('cwd', os.getcwd())))

    p = subprocess.Popen(args, **kw)
    out, err = p.communicate()
    msg = None
    if p.returncode != 0:
        msg = '%s: command returned %d (%s)' % (args, p.returncode, err)
    elif need_output and len(out) == 0:
        msg = '%s: failed (no output). (%s)' % (args,err)
    if msg is not None:
        if raise_on_failure: raise Exception(msg)
        logger.warn(msg)
        return False, msg
    if want_stderr:
        return out, err
    return out

try:
    from termcolor import colored
except ImportError:
    def colored(value, *unused_args, **unused_kw):
        return value

def _message(*args, **kw):
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

info  = partial(_message, severity='info')
warn  = partial(_message, severity='warn')
error = partial(_message, severity='error')
def die(*args, **kw):
    error(*args, **kw)
    sys.exit(kw.get('code', -1))

def stage(f):
    @wraps(f)
    def wrapper(self, *args, **kw):
        stage = f.__name__
        info('========== %s.%s ==========' % (self.pkgname, stage))
        try:
            return f(self, *args, **kw)
        except HelperError, e:
            raise PackageError(self, 'Stage[%s] %s' % (stage,e))
    return wrapper

class Environment(dict):
    def __init__(self, **kw):
        self.update(dict(
            HOME           = kw['BUILD_DIR'],
            DOWNLOAD_DIR   = kw['DOWNLOAD_DIR'],
            BUILD_DIR      = kw['BUILD_DIR'],
            INSTALL_DIR    = kw['INSTALL_DIR'],
            NOINSTALL_DIR  = P.join(kw['INSTALL_DIR'], 'noinstall'),
            ISISROOT       = P.join(kw['INSTALL_DIR'], 'isis'),
        ))
        self.update(kw)
        self['ISIS3RDPARTY'] = P.join(self['ISISROOT'], '3rdParty', 'lib')

        self.create_dirs()

    def create_dirs(self):
        for d in ('DOWNLOAD_DIR', 'BUILD_DIR', 'INSTALL_DIR', 'NOINSTALL_DIR'):
            try:
                os.makedirs(self[d])
            except OSError, o:
                if o.errno != errno.EEXIST: # Don't care if it already exists
                    raise

    def copy_set_default(self, **kw):
        e = Environment(**self)
        for k,v in kw.iteritems():
            if k not in e:
                e[k] = v
        return e

    def append(self, key, value):
        if key in self:
            self[key] += ' ' + value
        else:
            self[key] = value

    def append_many(self, key_seq, value):
        for k in key_seq:
            self.append(k, value)

def unique_compiler_flags(iflags):
    #This is used instead of a set to preserve flag order

    oflags = []
    used_flags = set()
    for keyword in iflags.split():
        if keyword not in used_flags:
            used_flags.add(keyword)
            oflags.append(keyword)
    return " ".join(oflags)

def get(url, output=None):
    if output is None:
        output = P.basename(urlparse(url).path)
        base = output
    else:
        base = P.basename(output)

    with file(output, 'wb') as f:
        try:
            r = urllib2.urlopen(url)
        except urllib2.HTTPError, e:
            raise HelperError('urlopen', None, '%s: %s' % (url, e))

        current = 0
        size = int(r.info().get('Content-Length', -1))

        while True:
            block = r.read(16384)
            if not block:
                break
            current += len(block)
            if size < 0:
                info('\rDownloading %s: %i kB' % (base, current/1024.), end='')
            else:
                info('\rDownloading %s: %i / %i kB (%0.2f%%)' % (base, current/1024., size/1024., current*100./size), end='')
            f.write(block)
        info('\nDone')

class Package(object):
    src     = None
    chksum  = None
    patches = []
    patch_level = None

    def __init__(self, env):
        self.pkgname = self.__class__.__name__

        # Yes, it is possible to get a / into a class name.
        # os.path.join fails pathologically there. So catch that specific case.
        assert '/' not in self.pkgname

        self.pkgdir  = P.abspath(P.dirname(inspect.getfile(self.__class__)))
        #info(self.pkgdir)
        self.tarball = None
        self.workdir = None
        self.env = env
        self.arch = get_platform(self)

        self.env['CPPFLAGS'] = self.env.get('CPPFLAGS', '') + ' -I%(NOINSTALL_DIR)s/include -I%(INSTALL_DIR)s/include' % self.env
        self.env['CXXFLAGS'] = self.env.get('CXXFLAGS', '') + ' -I%(NOINSTALL_DIR)s/include -I%(INSTALL_DIR)s/include' % self.env
        # If we include flags to directories that don't exist, we
        # cause compiler tests to fail.
        if P.isdir(self.env['ISIS3RDPARTY']):
            self.env['LDFLAGS'] = self.env.get('LDFLAGS', '') + ' -L%(ISIS3RDPARTY)s' % self.env
        if P.isdir(self.env['INSTALL_DIR']+'/lib'):
            self.env['LDFLAGS'] = self.env.get('LDFLAGS', '') + ' -L%(INSTALL_DIR)s/lib' % self.env

        # Remove repeated entries in CPPFLAGS, CXXFLAGS, LDFLAGS
        self.env['CPPFLAGS'] = unique_compiler_flags(self.env['CPPFLAGS'])
        self.env['CXXFLAGS'] = unique_compiler_flags(self.env['CXXFLAGS'])
        self.env['CFLAGS']   = unique_compiler_flags(self.env['CFLAGS'])
        self.env['LDFLAGS']  = unique_compiler_flags(self.env['LDFLAGS'])

    @stage
    def fetch(self, skip=False):
        '''After fetch, the source code should be available.'''

        assert self.src,    'No src defined for package %s' % self.pkgname
        assert self.chksum, 'No chksum defined for package %s' % self.pkgname

        if isinstance(self.src, basestring):
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

                self.tarball = P.join(self.env['DOWNLOAD_DIR'], P.basename(urlparse(src).path))

                if not P.isfile(self.tarball):
                    if skip: raise PackageError(self, 'Fetch is skipped and no src available')
                    get(src, self.tarball)

                curr_chksum = hash_file(self.tarball)
                if curr_chksum != chksum:
                    os.remove(self.tarball)
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

        self.remove_build(output_dir)

        ext = P.splitext(self.tarball)[-1]

        if ext == '.zip':
            self.helper('unzip', '-d', output_dir, self.tarball)
        elif ext.endswith('xz'):
            self.helper('xz','-kcd', self.tarball, '|', 'tar', 'x', '-C', output_dir)
        else:
            flags = 'xf'
            if ext == '.Z' or ext.endswith('gz'):
                flags = 'z' + flags
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

    @stage
    def configure(self, other=(), with_=(), without=(), enable=(), disable=(), configure='./configure'):
        '''After configure, the source code should be ready to build.'''

        args = list(other)
        for flag in 'enable', 'disable', 'with', 'without':
            if flag == 'with':
                value = locals()['with_']
            else:
                value = locals()[flag]

            if isinstance(value, basestring):
                args += ['--%s-%s' % (flag, value)]
            else:
                args += ['--%s-%s'  % (flag, feature) for feature in value]

        # Did they pass a prefix? If not, add one.
        if len([True for a in args if a[:9] == '--prefix=']) == 0:
            args.append('--prefix=%(INSTALL_DIR)s' % self.env)

        self.helper('./configure', *args)

    @stage
    def compile(self, cwd=None):
        '''After compile, the compiled code should exist.'''

        cmd = ('make', )
        if 'MAKEOPTS' in self.env:
            cmd += (self.env['MAKEOPTS'],)

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
        #    a basestring, interpreted as a patch or a dir of patches
        patches = []
        if self.patches is None:
            return
        elif isinstance(self.patches, basestring):
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
        else:
            patches = self.patches

        def _apply(patch):
            if self.patch_level is None:
                self.helper('patch', '-p1', '-i', patch)
            else:
                self.helper('patch', self.patch_level, '-i', patch)

        # We have a list of patches now, but we can't trust they're all there
        for p in patches:
            if p.endswith('~') or p.endswith('#'):
                continue
            if not P.isfile(p):
                raise PackageError(self, 'Unknown patch: %s' % p)
            _apply(p)


    def helper(self, *args, **kw):
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
        except (TypeError,), e:
            raise Exception('%s\n%s' % (e.message, '\t\n'.join(['\t%s=%s%s' % (name, type(value).__name__, value) for name,value in kw['env'].iteritems() if not isinstance(value, basestring)])))
        except (OSError, subprocess.CalledProcessError), e:
            raise HelperError(args[0], kw['env'], e)

    def copytree(self, src, dest, args=(), delete=True):
        call = ['rsync', '-a']
        if delete:
            call.append('--delete')
        call += args
        call += [src, dest]
        self.helper(*call)

    def remove_build(self, output_dir):
        if P.isdir(output_dir):
            info("Removing old build dir")
            rmtree(output_dir, False)
        os.makedirs(output_dir)

class GITPackage(Package):
    commit = None
    def __init__(self, env):
        super(GITPackage, self).__init__(env)
        self.localcopy = P.join(env['DOWNLOAD_DIR'], 'git', self.pkgname)

        if self.commit is None:
            # If the user did not specify which commit to fetch,
            # we'll fetch the latest. Store its commit hash.
            for line in self.helper('git', 'ls-remote', '--heads', self.src,
                                    stdout=subprocess.PIPE)[0].split('\n'):
                tokens = line.split()
                if len(tokens) > 1 and tokens[1] == 'refs/heads/master':
                    self.commit = tokens[0]
        
        # For git packages we don't have a chksum as we do for
        # tarballs.  We will use instead the commit hash. This helps
        # during building in deciding if the current version of the
        # software was built already.
        if self.chksum is None:
            self.chksum = self.commit
        
    def _git(self, *args):
        cmd = ['git', '--git-dir', self.localcopy]
        cmd.extend(args)
        self.helper(*cmd)

    @stage
    def fetch(self, skip=False):
        if P.exists(self.localcopy):
            if skip: return
            self._git('fetch', 'origin')
        else:
            if skip: raise PackageError(self, 'Fetch is skipped and no src available')
            self.helper('git', 'clone', '--mirror', self.src, self.localcopy)

    @stage
    def unpack(self):
        output_dir = P.join(self.env['BUILD_DIR'], self.pkgname)
        self.remove_build(output_dir)
        self.workdir = P.join(output_dir, self.pkgname + '-git')
        os.mkdir(self.workdir)
        self.helper('git', 'clone', self.localcopy, self.workdir)
        # Checkout a specific commit
        if self.commit is not None:
            cmd = ('git', 'checkout', self.commit)
            self.helper(*cmd, cwd=self.workdir)
        self._apply_patches()

class SVNPackage(Package):

    def __init__(self, env):
        super(SVNPackage, self).__init__(env)
        self.localcopy = P.join(env['DOWNLOAD_DIR'], 'svn', self.pkgname)

    def _get_current_url(self, path):
        for line in self.helper('svn', 'info', path, stdout=subprocess.PIPE)[0].split('\n'):
            tokens = line.split()
            if tokens[0] == 'URL:':
                return tokens[1]

    @stage
    def fetch(self, skip=False):
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
        except HelperError, e:
            warn('svn failed (removing %s): %s' % (self.localcopy, e))
            rmtree(self.localcopy)
            self.helper('svn', 'checkout', self.src, self.localcopy)

    @stage
    def unpack(self):
        output_dir = P.join(self.env['BUILD_DIR'], self.pkgname)
        self.remove_build(output_dir)
        self.workdir = P.join(output_dir, self.pkgname + '-svn')

        cmd = ('svn', 'export', self.localcopy, self.workdir)
        self.helper(*cmd, cwd=output_dir)

        self._apply_patches()

def findfile(filename, path=None):
    if path is None: path = os.environ.get('PATH', [])
    for dirname in path.split(':'):
        possible = P.join(dirname, filename)
        if P.isfile(possible):
            return possible
    raise Exception('Could not find file %s in path[%s]' % (filename, path))

class CMakePackage(Package):
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
        self.builddir = P.join(self.workdir, 'build')

        def remove_danger(files, dirname, fnames):
            files.extend([P.join(dirname,f) for f in fnames if f == 'CMakeLists.txt'])

        files = []
        P.walk(self.workdir, remove_danger, files)
        cmd = ['sed', '-ibak']
        # strip out vars we must control from every CMakeLists.txt
        for var in self.BLACKLIST_VARS:
            cmd.append('-e')
            cmd.append('s/^[[:space:]]*[sS][eE][tT][[:space:]]*([[:space:]]*%s.*)/#BINARY BUILDER IGNORE /g' % var)

        cmd.extend(files)
        self.helper(*cmd)

        build_rules = P.join(self.env['BUILD_DIR'], 'my_rules.cmake')
        with file(build_rules, 'w') as f:
            print('SET (CMAKE_C_COMPILER "%s" CACHE FILEPATH "C compiler" FORCE)' % (findfile(self.env['CC'], self.env['PATH'])), file=f)
            print('SET (CMAKE_C_COMPILE_OBJECT "<CMAKE_C_COMPILER> <DEFINES> %s <FLAGS> -o <OBJECT> -c <SOURCE>" CACHE STRING "C compile command" FORCE)' % (self.env.get('CPPFLAGS', '')), file=f)
            print('SET (CMAKE_CXX_COMPILER "%s" CACHE FILEPATH "C++ compiler" FORCE)' % (findfile(self.env['CXX'], self.env['PATH'])), file=f)
            print('SET (CMAKE_Fortran_COMPILER "%s" CACHE FILEPATH "Fortran compiler" FORCE)' % (findfile(self.env['F77'], self.env['PATH'])), file=f)
            print('SET (CMAKE_CXX_COMPILE_OBJECT "<CMAKE_CXX_COMPILER> <DEFINES> %s <FLAGS> -o <OBJECT> -c <SOURCE>" CACHE STRING "C++ compile command" FORCE)' % (self.env.get('CPPFLAGS', '')), file=f)

        cmd = ['cmake']
        args = [
            '-DCMAKE_INSTALL_PREFIX=%(INSTALL_DIR)s' % self.env,
            '-DCMAKE_BUILD_TYPE=MyBuild',
            '-DCMAKE_USER_MAKE_RULES_OVERRIDE=%s' % build_rules,
            '-DCMAKE_SKIP_RPATH=YES',
            '-DCMAKE_INSTALL_DO_STRIP=OFF',
        ]

        if self.arch.os == 'osx':
            args.append('-DCMAKE_OSX_ARCHITECTURES=%s' % self.env['OSX_ARCH'])
            args.append('-DCMAKE_OSX_SYSROOT=%s' % self.env['OSX_SYSROOT'])
            args.append('-DCMAKE_OSX_DEPLOYMENT_TARGET=%s' % self.env['OSX_TARGET'])

        for arg in disable:
            args.append('-DENABLE_%s=OFF' % arg)
        for arg in enable:
            args.append('-DENABLE_%s=ON' % arg)
        for arg in without:
            args.append('-DWITH_%s=OFF' % arg)
        for arg in with_:
            args.append('-DWITH_%s=ON' % arg)

        args.extend([
            '-DCMAKE_PREFIX_PATH=%(INSTALL_DIR)s;%(NOINSTALL_DIR)s' % self.env,
            '-DLIB_POSTFIX=',
        ])

        [args.append(arg) for arg in other]

        os.mkdir(self.builddir)

        cmd = cmd + args + [self.workdir]

        self.helper(*cmd, cwd=self.builddir)

    @stage
    def compile(self):
        super(CMakePackage, self).compile(cwd=self.builddir)

    @stage
    def install(self):
        super(CMakePackage, self).install(cwd=self.builddir)

def write_vw_config(prefix, installdir, arch, config_file):

    print('Writing ' + config_file)
    base = '$BASE'

    # Enable
    enable_features = 'debug optimize rpath as_needed no_undefined'.split()
    enable_pkgs = 'jpeg png gdal proj4 z ilmbase openexr boost flapack protobuf flann'.split()
    enable_modules  = 'camera mosaic interestpoint cartography hdr stereo geometry tools bundleadjustment'.split()

    # Disable
    disable_features = 'pkg_paths_default static qt-qmake'.split()
    disable_pkgs = 'tiff hdr cairomm tcmalloc x11 clapack slapack opencv cg zeromq rabbitmq_c qt_qmake arbitrary_qt apple_qmake_qt linux_qmake_qt guess_qt qt'.split()
    disable_modules = 'gpu plate python gui'.split()
   
    with file(config_file, 'w') as config:

        print('# The path to the installed 3rd party libraries', file=config)
        print('BASE=%s' % installdir, file=config)
        print('', file=config) # newline

        print('# Installation prefix', file=config)
        print('PREFIX=%s' % prefix, file=config)
        print('', file=config) # newline

        # To do: Test removing -rpath from cflags and cxxflags
        if arch.os == 'osx':
            print('CFLAGS="-arch x86_64 -Wl,-rpath -Wl,%s"' % base,
                  file=config)
            print('CXXFLAGS="-arch x86_64 -Wl,-rpath -Wl,%s"' % base,
                  file=config)
            print('LDFLAGS="-Wl,-rpath -Wl,%s"' % base, file=config)
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
            print('PKG_%s_CPPFLAGS="-I%s"' % (pkg.upper(), P.join(base, 'include')), file=config)
            if pkg == 'gdal' and arch.os == 'linux':
                print('PKG_%s_LDFLAGS="-L%s -ltiff -ljpeg -lpng -lz -lopenjp2"'  % (pkg.upper(), P.join(base, 'lib')), file=config)
            else:
                print('PKG_%s_LDFLAGS="-L%s"'  % (pkg.upper(), P.join(base, 'lib')), file=config)

        for pkg in disable_pkgs:
            print('HAVE_PKG_%s=no' % pkg.upper(), file=config)
        print('', file=config) # newline

        # Specify executables we use
        print('PROTOC=%s' % (P.join(base, 'bin',
                                    'protoc')),file=config)
        print('MOC=%s' % (P.join(base, 'bin',
                                 'moc')),file=config)

class Apps:
    disable_modules = 'controlnettk mpi'
    enable_modules  = 'core spiceio isisio sessions'

    disable_apps = \
                 'bundleadjust demprofile isisadjustcameraerr \
                 isisadjustcnetclip plateorthoproject results \
                 rmax2cahvor rmaxadjust stereogui'
    enable_apps = \
                'bundlevis dem_geoid disparitydebug geodiff hsvmerge \
                isisadjust mapproject mer2camera orbitviz orthoproject \
                point2dem point2las point2mesh pc_align stereo rpc_gen \
                tif_mosaic wv_correct'
    install_pkgs = \
                 'boost openscenegraph flapack arbitrary_qt curl  \
                 suitesparse amd colamd cholmod flann spice qwt gsl\
                 geos xercesc protobuf tiff z ilmbase openexr jpeg laszip liblas geoid isis \
                 superlu gdal yaml libnabo eigen libpointmatcher proj4'
    vw_pkgs     = \
            'vw_core vw_math vw_image vw_fileio vw_camera \
             vw_stereo vw_cartography vw_interest_point'
    off_pkgs    = \
             'zeromq rabbitmq_c qt_qmake clapack slapack vw_plate \
             kakadu gsl_hasblas apple_qwt'
    qt_pkgs     = \
            'QtCore QtGui QtNetwork QtSql QtSvg QtXml QtXmlPatterns'


def write_asp_config(use_env_flags, prefix, installdir, vw_build, arch,
                     geoid, config_file):

    print('Writing ' + config_file)

    disable_apps = Apps.disable_apps.split()
    enable_apps  = Apps.enable_apps.split()
    off_pkgs     = Apps.off_pkgs.split()
    install_pkgs = Apps.install_pkgs.split()
    vw_pkgs      = Apps.vw_pkgs.split()
    base         = '$BASE'
    includedir   = P.join(base, 'include')
    libdir       = P.join(base, 'lib')
    bindir       = P.join(base, 'bin')

    # To do: Test removing -O3 and -g, as well as use_env_flags
    cflags   = ['-O3', '-g']
    cxxflags = ['-O3', '-g']
    cppflags = ['-I' + includedir]
    ldflags  = ['-L' + libdir, '-Wl,-rpath', '-Wl,' + base]

    with file(config_file, 'w') as config:

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

            if pkg == 'gdal':
                print('PKG_%s_LDFLAGS="-ltiff -ljpeg -lpng -lz -lopenjp2"'  % (pkg.upper()), file=config)

            if pkg == 'geoid':
                cppflags.extend(['-DGEOID_PATH=' + base + '/share/geoids-' \
                             + geoid.version])

        for pkg in install_pkgs:
            print('HAVE_PKG_%s=%s' % (pkg.upper(), base), file=config)
        for pkg in vw_pkgs:
            print('HAVE_PKG_%s=$VW' % pkg.upper(), file=config)
        for pkg in off_pkgs:
            print('HAVE_PKG_%s=no' % pkg.upper(), file=config)

        # Qt
        qt_pkgs = Apps.qt_pkgs
        print('QT_ARBITRARY_MODULES="%s"' % qt_pkgs, file=config)
        qt_cppflags=['-I%s' % includedir]
        qt_libs=['-L%s' % libdir]
        for module in qt_pkgs.split():
            qt_cppflags.append('-I%s/%s' % (includedir, module))
            qt_libs.append('-l%s' % module)
        print('PKG_ARBITRARY_QT_LIBS="%s"' %  ' '.join(qt_libs), file=config)
        print('PKG_ARBITRARY_QT_MORE_LIBS="-lpng -lz"', file=config)
        print('MOC=%s' % (P.join(bindir, 'moc')),file=config)
        cppflags.extend(qt_cppflags)

        print('PROTOC=%s' % (P.join(bindir, 'protoc')),file=config)
        cppflags.extend(["-I%s/eigen3" % includedir])

        if not use_env_flags:
            print('CFLAGS="'   + ' '.join(cflags)   + '"', file=config)
            print('CXXFLAGS="' + ' '.join(cxxflags) + '"', file=config)
        
        print('CPPFLAGS="' + ' '.join(cppflags) + '"', file=config)
        print('LDFLAGS="'  + ' '.join(ldflags)  + '"', file=config)

def binary_builder_prefix():
    return 'BinaryBuilder'


