#!/usr/bin/env python

from __future__ import with_statement, print_function

import errno
import inspect
import os
import os.path as P
import subprocess
import sys
import tarfile
import urllib2

from functools import wraps
from glob import glob
from hashlib import md5
from shutil import rmtree
from urlparse import urlparse

class PackageError(Exception):
    def __init__(self, pkg, message):
        super(PackageError, self).__init__('Package[%s]: %s' % (pkg.pkgname, message))
class HelperError(Exception): pass

def hash_file(filename):
    with file(filename, 'rb') as f:
        return md5(f.read()).hexdigest()

info = print

def error(value):
    print >>sys.stderr, value

def icall(*args, **kw):
    info(' '.join(args))
    try:
        subprocess.check_call(args, **kw)
    except OSError, e:
        raise HelperError('%s: %s' % (args[0],e))

def stage(f):
    @wraps(f)
    def wrapper(self, *args, **kw):
        stage = f.__name__
        info('%s.%s' % (self.pkgname, stage))
        try:
            return f(self, *args, **kw)
        except HelperError, e:
            raise PackageError(self, 'Stage[%s] failed: %s' % (stage,e))
    return wrapper

class Environment(dict):
    def __init__(self, **kw):
        self['DOWNLOAD_DIR'] = '/tmp/build/src'
        self['BUILD_DIR']    = '/tmp/build/build'
        self['INSTALL_DIR']  = '/tmp/build/install'
        self.update(kw)

        for d in ('DOWNLOAD_DIR', 'BUILD_DIR', 'INSTALL_DIR'):
            try:
                os.makedirs(self[d])
            except OSError, o:
                if o.errno == errno.EEXIST:
                    pass # Don't care if it already exists
                else:
                    raise

def get(url, output=None):
    if output is None:
        output = P.basename(urlparse(url).path)
        base = output
    else:
        base = P.basename(output)

    with file(output, 'wb') as f:
        r = urllib2.urlopen(url)

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
        info('Done')

class Package(object):

    src     = None
    chksum  = None
    patches = []

    def __init__(self, env):
        self.pkgname = self.__class__.__name__

        # Yes, it is possible to get a / into a class name.
        # os.path.join fails pathologically there.
        assert '/' not in self.pkgname

        self.pkgdir  = P.dirname(inspect.getfile(self.__class__))
        self.tarball = None
        self.workdir = None

    @stage
    def fetch(self, env):
        '''After fetch, the source code should be available.'''

        assert self.src,    'No src defined for package %s' % self.pkgname
        assert self.chksum, 'No chksum defined for package %s' % self.pkgname

        self.tarball = P.join(env['DOWNLOAD_DIR'], P.basename(urlparse(self.src).path))

        if not P.isfile(self.tarball):
            get(self.src, self.tarball)

        if hash_file(self.tarball) != self.chksum:
            raise PackageError(self, 'Checksum on file[%s] failed!' % self.tarball)

    @stage
    def unpack(self, env):
        '''After unpack, the source code should be unpacked and should have any
        necessary patches applied.'''

        output_dir = P.join(env['BUILD_DIR'], self.pkgname)

        if P.isdir(output_dir):
            info("Removing old build dir")
            rmtree(output_dir, False)

        os.mkdir(output_dir)

        tar = tarfile.open(self.tarball)
        tar.extractall(path=output_dir)
        tar.close()

        self.workdir = glob(P.join(output_dir, "*"))
        if len(self.workdir) != 1:
            raise PackageError(self, 'Badly-formed tarball: there should be 1 file in the output, but there are %i' % len(self.workdir))

        self.workdir = self.workdir[0]

        self._apply_patches()

    @stage
    def configure(self, env, *args):
        '''After configure, the source code should be ready to build.'''

        cmd=('./configure', '--prefix=%(INSTALL_DIR)s' % env) + args
        return icall(*cmd, cwd=self.workdir)

    @stage
    def compile(self, env):
        '''After compile, the compiled code should exist.'''

        cmd = ('make', ) + env.get('MAKEOPTS', ())
        return icall(*cmd, cwd=self.workdir)

    @stage
    def install(self, unused_env):
        '''After install, the binaries should be on the live filesystem.'''

        cmd = ('make', 'install')
        return icall(*cmd, cwd=self.workdir)

    def all(self, env):
        self.fetch(env)
        self.unpack(env)
        self.configure(env)
        self.compile(env)
        self.install(env)

    def _apply_patches(self):
        for p in self.patches:
            cmd = ['patch',  '-p1',  '-i',  P.join(self.pkgdir, p)]
            if icall(*cmd, cwd=self.workdir, stderr=open('/dev/null', 'w')) != 0:
                raise PackageError(self, 'Could not apply patch %s' % p)


class SVNPackage(Package):

    def __init__(self, env):
        super(SVNPackage, self).__init__()
        self.localcopy = P.join(env['DOWNLOAD_DIR'], 'svn', self.pkgname)

    @stage
    def fetch(self, env):
        if P.isdir(self.localcopy):
            cmd = ('svn', 'update', self.src, self.localcopy)
        else:
            cmd = ('svn', 'checkout', self.src, self.localcopy)

        icall(*cmd, cwd=self.workdir)

    @stage
    def unpack(self, env):
        output_dir = P.join(env['BUILD_DIR'], self.pkgname)
        if P.isdir(output_dir):
            info("Removing old build dir")
            rmtree(output_dir, False)

        os.mkdir(output_dir)

        self.workdir = P.join(output_dir, self.pkgname)

        cmd = ('svn', 'export', self.localcopy, self.workdir)
        icall(*cmd, cwd=self.workdir)

        self._apply_patches()
