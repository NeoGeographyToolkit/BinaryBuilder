#!/usr/bin/env python2.6

from __future__ import print_function

import os
import os.path as P
import subprocess
import sys
import errno
from optparse import OptionParser
from tempfile import mkdtemp, gettempdir
from distutils import version

from Packages import isis, gsl_headers, geos_headers, superlu_headers, xercesc_headers,\
                qt_headers, qwt_headers, cspice_headers, zlib, png, jpeg, proj, gdal,\
                ilmbase, openexr, boost, osg, lapack, visionworkbench, stereopipeline,\
                zlib_headers, png_headers, isis_local, protobuf_headers, jpeg_headers, \
                flann

from BinaryBuilder import Package, Environment, PackageError, die, info, get_platform, findfile, tweak_path, run

CC_FLAGS = ('CFLAGS', 'CXXFLAGS')
LD_FLAGS = ('LDFLAGS')
ALL_FLAGS = ('CFLAGS', 'CPPFLAGS', 'CXXFLAGS', 'LDFLAGS')

def get_cores():
    try:
        n = os.sysconf('SC_NPROCESSORS_ONLN')
        return n if n else 2
    except:
        return 2

def makelink(src, dst):
    try:
        os.remove(dst)
    except OSError, o:
        if o.errno != errno.ENOENT: # Don't care if it wasn't there
            raise
    os.symlink(src, dst)

def grablink(dst):
    if not P.exists(dst):
        raise Exception('Cannot resume, no link %s exists!' % dst)
    ret = os.readlink(dst)
    if not P.exists(ret):
        raise Exception('Cannot resume, link target %s for link %s doesn\'t exist' % (ret, dst))
    return ret


def summary(env):
    print('===== Environment =====')
    for k in sorted(env.keys()):
        print('%15s: %s' % (k,env[k]))

if __name__ == '__main__':
    parser = OptionParser()
    parser.set_defaults(mode='all')

    parser.add_option('--base',       action='append',      dest='base',         default=[],              help='Provide a tarball to use as a base system')
    parser.add_option('--no-ccache',  action='store_false', dest='ccache',       default=True,            help='Disable ccache')
    parser.add_option('--coreutils',                        dest='coreutils',    default=None,            help='Bin directory holding GNU coreutils')
    parser.add_option('--dev-env',    action='store_true',  dest='dev',          default=False,           help='Build everything but VW and ASP')
    parser.add_option('--fetch',      action='store_const', dest='mode',         const='fetch',           help='Fetch sources only, don\'t build')
    parser.add_option('--no-fetch',   action='store_const', dest='mode',         const='nofetch',         help='Build, but do not fetch (will fail if sources are missing)')
    parser.add_option('--isisroot',                         dest='isisroot',     default=None,            help='Use a locally-installed isis at this root')
    parser.add_option('--pretend',    action='store_true',  dest='pretend',      default=False,           help='Show the list of packages without actually doing anything')
    parser.add_option('--save-temps', action='store_true',  dest='save_temps',   default=False,           help='Save build files to check include paths')
    parser.add_option('--threads',    type='int',           dest='threads',      default=2*get_cores(),   help='Build threads to use')
    parser.add_option('--download-dir',                     dest='download_dir', default='/tmp/tarballs', help='Where to archive source files')
    parser.add_option('--build-root',                       dest='build_root',   default=None,            help='Root of the build and install')
    parser.add_option('--resume',     action='store_true',  dest='resume',       default=False,           help='Reuse in-progress build/install dirs')

    global opt
    (opt, args) = parser.parse_args()

    tweak_path(opt.coreutils)

    # GDAL 1.8.0 is mostly threads safe. However it hits a race
    # condition if you are building with more than 16 threads.
    if ( opt.threads > 16 ):
        opt.threads = 16
    info('Using %d build processes' % opt.threads)

    if opt.isisroot is not None and not P.isdir(opt.isisroot):
        parser.print_help()
        die('\nIllegal argument to --isisroot: path does not exist')

    if opt.ccache and opt.save_temps:
        die('--ccache and --save-temps conflict. Disabling ccache.')

    if opt.resume:
        opt.build_root = grablink('last-run')

    if opt.build_root is None or not P.exists(opt.build_root):
        opt.build_root = mkdtemp(prefix='BinaryBuilder')

    # Things misbehave if the buildroot is symlinks in it
    opt.build_root = P.realpath(opt.build_root)

    # -Wl,-z,now ?
    e = Environment(
                    CC       = 'gcc',
                    CXX      = 'g++',
                    F77      = 'gfortran',
                    CFLAGS   = '-O3 -g',
                    CXXFLAGS = '-O3 -g',
                    LDFLAGS  = r'-Wl,-rpath,/%s' % ('a'*100),
                    MAKEOPTS='-j%s' % opt.threads,
                    DOWNLOAD_DIR = opt.download_dir,
                    BUILD_DIR    = P.join(opt.build_root, 'build'),
                    INSTALL_DIR  = P.join(opt.build_root, 'install'),
                    MISC_DIR = P.join(opt.build_root, 'misc'),
                    PATH=os.environ['PATH'],
                    **({} if opt.isisroot is None else dict(ISISROOT=opt.isisroot)))

    arch = get_platform()

    if arch.os == 'linux':
        e.append('LDFLAGS', '-Wl,-O1 -Wl,--enable-new-dtags -Wl,--hash-style=both')
    elif arch.os == 'osx':
        e.append('LDFLAGS', '-Wl,-headerpad_max_install_names')

        # ISIS only supports 32-bit
        osx_arch = 'i386' #SEMICOLON-DELIMITED
        # We're targeting 10.5
        target = '10.5'
        # And also using the matching sdk for good measure
        sysroot = '/Developer/SDKs/MacOSX%s.sdk' % target

        # CMake needs these vars to not screw things up.
        e.append('OSX_SYSROOT', sysroot)
        e.append('OSX_ARCH', osx_arch)
        e.append('OSX_TARGET', target)

        e.append_many(ALL_FLAGS, ' '.join(['-arch ' + i for i in osx_arch.split(';')]))
        e.append_many(ALL_FLAGS, '-mmacosx-version-min=%s -isysroot %s' % (target, sysroot))

        # Resolve a bug with -mmacosx-version-min on 10.6 (see
        # http://markmail.org/message/45nbrtxsxvsjedpn).
        # Short version: 10.6 generates the new compact header (LD_DYLD_INFO)
        # even when told to support 10.5 (which can't read it)
        if version.StrictVersion(arch.dist_version) >= '10.6':
            e.append('LDFLAGS', '-Wl,-no_compact_linkedit')

    e.append_many(ALL_FLAGS, '-m%i' % arch.bits)

    if arch.osbits == 'linux32':
        limit_symbols = P.join(P.abspath(P.dirname(__file__)), 'glibc24.h')
        e.append('CPPFLAGS', '-include %s' % limit_symbols)

    if opt.ccache:
        compiler_dir = P.join(e['MISC_DIR'], 'mycompilers')
        new = dict(
            CC  = P.join(compiler_dir, e['CC']),
            CXX = P.join(compiler_dir, e['CXX']),
            CCACHE_DIR = P.join(opt.download_dir, 'ccache-dir'),
            CCACHE_BASEDIR = gettempdir(),
        )

        if not P.exists(compiler_dir):
            os.makedirs(compiler_dir)
        ccache_path = findfile('ccache', e['PATH'])
        subprocess.check_call(['ln', '-sf', ccache_path, new['CC']])
        subprocess.check_call(['ln', '-sf', ccache_path, new['CXX']])
        e.update(new)

    if opt.save_temps:
        e.append_many(CC_FLAGS, '-save-temps')
    else:
        e.append_many(CC_FLAGS, '-pipe')

    if len(args) == 0:
        # Were we told what isis to use?
        build = [isis_local if opt.isisroot is not None else isis]

        # Many things depend on isis 3rdparty, so do it before the rest
        build += [gsl_headers, geos_headers, superlu_headers, xercesc_headers, qt_headers, qwt_headers, cspice_headers, protobuf_headers]

        if arch.os == 'linux':
            build.extend([zlib, png, jpeg])
        elif arch.os == 'osx':
            build.extend([zlib_headers, png_headers, jpeg_headers])

        build.extend([proj, gdal, ilmbase, openexr, boost, osg, flann])

        if arch.os == 'linux':
            build.append(lapack)

        if not opt.dev:
            build.extend([visionworkbench, stereopipeline])
    else:
        build = (globals()[pkg] for pkg in args)

    if opt.pretend:
        info('I want to build:\n%s' % ' '.join(map(lambda x: x.__name__, build)))
        summary(e)
        sys.exit(0)

    makelink(opt.build_root, 'last-run')

    if opt.base:
        print('Untarring base system')
    for base in opt.base:
        run('tar', 'xf', base, '-C', e['INSTALL_DIR'], '--strip-components', '1')

    modes = dict(
        all     = lambda pkg : Package.build(pkg, skip_fetch=False),
        fetch   = lambda pkg : pkg.fetch(),
        nofetch = lambda pkg : Package.build(pkg, skip_fetch=True))

    try:
        for pkg in build:
            modes[opt.mode](pkg(e))
    except PackageError, e:
        die(e)

    makelink(opt.build_root, 'last-completed-run')

    info('\n\nAll done!')
    summary(e)
