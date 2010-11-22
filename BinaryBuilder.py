#!/usr/bin/env python

from __future__ import with_statement, print_function

import errno
import inspect
import os
import os.path as P
import subprocess
import sys
import urllib2

from functools import wraps, partial
from glob import glob
from hashlib import sha1
from shutil import rmtree
from urlparse import urlparse

def get_platform(pkg=None):
    import platform
    system  = platform.system()
    machine = platform.machine()

    if system == 'Linux' and machine == 'x86_64':
        return 'linux64'
    elif system == 'Linux' and machine == 'i686':
        return 'linux32'
    elif system == 'Darwin' and machine == 'i386':
        return 'osx32'
    else:
        message = 'Cannot match system to known platform'
        if pkg is None:
            raise Exception(message)
        else:
            raise PackageError(pkg, message)

class PackageError(Exception):
    def __init__(self, pkg, message):
        super(PackageError, self).__init__('Package[%s] %s' % (pkg.pkgname, message))
class HelperError(Exception):
    def __init__(self, tool, env, message):
        super(HelperError, self).__init__('Command[%s] %s\nEnv%s' % (tool, message, env))

def hash_file(filename):
    with file(filename, 'rb') as f:
        return sha1(f.read()).hexdigest()

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
        basedir  = kw.get('BASEDIR',  os.environ['HOME'])
        isisroot = kw.get('ISISROOT', P.join(basedir, 'build', 'isis'))

        self.update(dict(
            HOME           = basedir,
            DOWNLOAD_DIR   = P.join(basedir, 'build-src'),
            BUILD_DIR      = P.join(basedir, 'build', 'build'),
            INSTALL_DIR    = P.join(basedir, 'build', 'install'),
            NOINSTALL_DIR  = P.join(basedir, 'build', 'noinstall'),
            ISISROOT       = isisroot,
            ISIS3RDPARTY   = P.join(isisroot, '3rdParty', 'lib'),
        ))
        self.update(kw)

        for d in ('DOWNLOAD_DIR', 'BUILD_DIR', 'INSTALL_DIR'):
            try:
                os.makedirs(self[d])
            except OSError, o:
                if o.errno == errno.EEXIST:
                    pass # Don't care if it already exists
                else:
                    raise
    def append(self, key, value):
        if key in self:
            self[key] += ' ' + value
        else:
            self[key] = value



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

    def __init__(self, env):
        self.pkgname = self.__class__.__name__

        # Yes, it is possible to get a / into a class name.
        # os.path.join fails pathologically there. So catch that specific case.
        assert '/' not in self.pkgname

        self.pkgdir  = P.abspath(P.dirname(inspect.getfile(self.__class__)))
        info(self.pkgdir)
        self.tarball = None
        self.workdir = None
        self.env = dict(env)
        self.arch = get_platform(self)

        self.env['CFLAGS']   = self.env.get('CFLAGS', '')   + ' -I%(INSTALL_DIR)s/include -I%(NOINSTALL_DIR)s/include' % self.env
        self.env['CPPFLAGS'] = self.env.get('CPPFLAGS', '') + ' -I%(INSTALL_DIR)s/include -I%(NOINSTALL_DIR)s/include' % self.env
        self.env['CXXFLAGS'] = self.env.get('CXXFLAGS', '') + ' -I%(INSTALL_DIR)s/include -I%(NOINSTALL_DIR)s/include' % self.env
        self.env['LDFLAGS']  = self.env.get('LDFLAGS', '')  + ' -L%(ISIS3RDPARTY)s -L%(INSTALL_DIR)s/lib'              % self.env

    @stage
    def fetch(self):
        '''After fetch, the source code should be available.'''

        assert self.src,    'No src defined for package %s' % self.pkgname
        assert self.chksum, 'No chksum defined for package %s' % self.pkgname

        if isinstance(self.src, basestring):
            self.src = (self.src,)
            self.chksum = (self.chksum,)

        assert len(self.src) == len(self.chksum), 'len(src) and len(chksum) should be the same'

        for src,chksum in zip(self.src, self.chksum):

            self.tarball = P.join(self.env['DOWNLOAD_DIR'], P.basename(urlparse(src).path))

            if not P.isfile(self.tarball):
                get(src, self.tarball)

            if hash_file(self.tarball) != chksum:
                raise PackageError(self, 'Checksum on file[%s] failed!' % self.tarball)

    @stage
    def unpack(self):
        '''After unpack, the source code should be unpacked and should have any
        necessary patches applied.'''

        output_dir = P.join(self.env['BUILD_DIR'], self.pkgname)

        self.remove_build(output_dir)

        ext = P.splitext(self.tarball)[-1]

        if ext == '.zip':
            self.helper('unzip', '-d', output_dir, self.tarball)
        else:
            flags = 'xf'
            if ext == '.Z' or ext.endswith('gz'):
                flags = 'z' + flags
            elif ext.endswith('bz2'):
                flags = 'j' + flags

            self.helper('tar', flags, self.tarball, '-C',  output_dir)

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

        e = Environment(prefix=self.env['INSTALL_DIR'])
        e.update(self.env)

        self.helper(*cmd, env=e, cwd=cwd)

    @stage
    def install(self, cwd=None):
        '''After install, the binaries should be on the live filesystem.'''

        e = Environment(prefix=self.env['INSTALL_DIR'])
        e.update(self.env)

        cmd = ('make', 'install')
        self.helper(*cmd, env=e, cwd=cwd)

    @staticmethod
    def build(pkg, env):
        # If it's a type, we instantiate it. Otherwise, we just use whatever it is.
        if isinstance(pkg, type):
            pkg = pkg(env)
        pkg.fetch()
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
            if not P.exists(full):
                raise PackageError(self, 'Unknown patch: %s' % full)

            if P.isdir(full):
                patches = glob(P.join(full, '*'))
            else:
                patches = [full]
        else:
            patches = (P.join(self.pkgdir, p) for p in self.patches)

        def _apply(patch):
            cmd = ('patch',  '-p1',  '-i', patch)
            self.helper(*cmd)

        # We have a list of patches now, but we can't trust they're all there
        for p in sorted(patches):
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

        try:
            p = subprocess.Popen(args, **kw)
            (out, err) = p.communicate()
            if p.returncode != 0:
                raise subprocess.CalledProcessError(p.returncode, args)
            return out, err
        except (OSError, subprocess.CalledProcessError), e:
            raise HelperError(args[0], kw['env'], e)

    def copytree(self, src, dest, args=None):
        call = ['rsync', '-a', '--delete']
        if args is not None:
            call += args
        call += [src, dest]
        self.helper(*call)

    def remove_build(self, output_dir):
        if P.isdir(output_dir):
            info("Removing old build dir")
            rmtree(output_dir, False)

        os.mkdir(output_dir)

class GITPackage(Package):
    def __init__(self, env):
        super(GITPackage, self).__init__(env)
        self.localcopy = P.join(env['DOWNLOAD_DIR'], 'git', self.pkgname)

    def _git(self, *args):
        cmd = ['git', '--git-dir', self.localcopy]
        cmd.extend(args)
        self.helper(*cmd)

    @stage
    def fetch(self):
        if P.exists(self.localcopy):
            self._git('fetch', 'origin')
        else:
            self.helper('git', 'clone', '--mirror', self.src, self.localcopy)

    @stage
    def unpack(self):
        output_dir = P.join(self.env['BUILD_DIR'], self.pkgname)
        self.remove_build(output_dir)
        self.workdir = P.join(output_dir, self.pkgname + '-git')
        os.mkdir(self.workdir)
        self.helper('git', 'clone', self.localcopy, self.workdir)
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
    def fetch(self):
        try:
            if P.exists(self.localcopy):
                url = self._get_current_url(self.localcopy)
                if url == self.src:
                    self.helper('svn', 'update', self.localcopy)
                else:
                    self.helper('svn', 'switch', self.src, self.localcopy)
            else:
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

    def __init__(self, env):
        super(CMakePackage, self).__init__(env)

    @stage
    def configure(self, other=(), enable=(), disable=(), with_=(), without=()):
        self.builddir = P.join(self.workdir, 'build')

        def remove_danger(files, dirname, fnames):
            files.extend([P.join(dirname,f) for f in fnames if f == 'CMakeLists.txt'])

        files = []
        P.walk(self.workdir, remove_danger, files)
        cmd = ['sed',  '-ibak',
                    '-e', 's/^[[:space:]]*[sS][eE][tT][[:space:]]*([[:space:]]*CMAKE_BUILD_TYPE.*)/#IGNORE /g',
                    '-e', 's/^[[:space:]]*[sS][eE][tT][[:space:]]*([[:space:]]*CMAKE_INSTALL_PREFIX.*)/#IGNORE /g',
                    '-e', 's/^[[:space:]]*[sS][eE][tT][[:space:]]*([[:space:]]*CMAKE_OSX_ARCHITECTURES.*)/#IGNORE /g',
              ]

        cmd.extend(files)
        self.helper(*cmd)

        build_rules = P.join(self.env['BASEDIR'], 'my_rules.cmake')
        with file(build_rules, 'w') as f:
            print('SET (CMAKE_C_COMPILER "%s" CACHE FILEPATH "C compiler" FORCE)' % (findfile(self.env['CC'], self.env['PATH'])), file=f)
            print('SET (CMAKE_C_COMPILE_OBJECT "<CMAKE_C_COMPILER> <DEFINES> %s <FLAGS> -o <OBJECT> -c <SOURCE>" CACHE STRING "C compile command" FORCE)' % (self.env.get('CPPFLAGS', '')), file=f)
            print('SET (CMAKE_CXX_COMPILER "%s" CACHE FILEPATH "C++ compiler" FORCE)' % (findfile(self.env['CXX'], self.env['PATH'])), file=f)
            print('SET (CMAKE_CXX_COMPILE_OBJECT "<CMAKE_CXX_COMPILER> <DEFINES> %s <FLAGS> -o <OBJECT> -c <SOURCE>" CACHE STRING "C++ compile command" FORCE)' % (self.env.get('CPPFLAGS', '')), file=f)

        cmd = ['cmake']
        args = [
            '-DCMAKE_INSTALL_PREFIX=%(INSTALL_DIR)s' % self.env,
            '-DCMAKE_BUILD_TYPE=MyBuild',
            '-DCMAKE_USER_MAKE_RULES_OVERRIDE=%s' % build_rules,
            '-DCMAKE_SKIP_RPATH=YES',
            '-DCMAKE_INSTALL_DO_STRIP=OFF',
        ]

        if self.arch[:3] == 'osx':
            args.append('-DCMAKE_OSX_ARCHITECTURES=i386')

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
