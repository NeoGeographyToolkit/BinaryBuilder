#!/usr/bin/env python

from __future__ import print_function

import os
import os.path as P
import subprocess
import sys
import errno
from optparse import OptionParser
from tempfile import mkdtemp


from Packages import isis, gsl_headers, geos_headers, superlu_headers, xercesc_headers,\
                qt_headers, qwt_headers, cspice_headers, zlib, png, jpeg, proj, gdal,\
                ilmbase, openexr, boost, osg, lapack, visionworkbench, stereopipeline,\
                zlib_headers, png_headers, isis_local, protobuf_headers, jpeg_headers

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

def rm_f(filename):
    ''' An rm that doesn't care if the file isn't there '''
    try:
        os.remove(filename)
    except OSError, o:
        if o.errno != errno.ENOENT: # Don't care if it wasn't there
            raise

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
    parser.add_option('--build-dir',                        dest='build_dir',    default=None,            help='Root of the build')
    parser.add_option('--install-dir',                      dest='install_dir',  default=None,            help='Root of the install')

    global opt
    (opt, args) = parser.parse_args()

    tweak_path(opt.coreutils)

    info('Using %d build processes' % opt.threads)

    if opt.isisroot is not None and not P.isdir(opt.isisroot):
        parser.print_help()
        die('\nIllegal argument to --isisroot: path does not exist')

    if opt.ccache and opt.save_temps:
        die('--ccache and --save-temps conflict. Disabling ccache.')

    if opt.build_dir is None:
        opt.build_dir = mkdtemp()
    if opt.install_dir is None:
        opt.install_dir = mkdtemp()

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
                    BUILD_DIR    = opt.build_dir,
                    INSTALL_DIR  = opt.install_dir,
                    PATH=os.environ['PATH'],
                    **({} if opt.isisroot is None else dict(ISISROOT=opt.isisroot)))

    if opt.base:
        print('Untarring base system')
    for base in opt.base:
        run('tar', 'xf', base, '-C', e['INSTALL_DIR'], '--strip-components', '1')

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
        # http://markmail.org/message/45nbrtxsxvsjedpn)
        e.append('LDFLAGS', '-Wl,-no_compact_linkedit')

    e.append_many(ALL_FLAGS, '-m%i' % arch.bits)

    # XXX LDFLAGS? What?
    if arch.osbits == 'linux32':
        limit_symbols = P.join(P.abspath(P.dirname(__file__)), 'glibc24.h')
        e.append('LDFLAGS', '-include %s' % limit_symbols)

    if opt.ccache:
        compiler_dir = P.join(opt.build_dir, 'mycompilers')
        new = dict(
            CC  = P.join(compiler_dir, e['CC']),
            CXX = P.join(compiler_dir, e['CXX']))

        if not P.exists(compiler_dir):
            os.mkdir(compiler_dir)
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

        build.extend([proj, gdal, ilmbase, openexr, boost, osg])

        if arch.os == 'linux':
            build.append(lapack)

        if not opt.dev:
            build.extend([visionworkbench, stereopipeline])
    else:
        build = (globals()[pkg] for pkg in args)

    if opt.pretend:
        info('I want to build:\n%s' % ' '.join(map(lambda x: x.__name__, build)))
        sys.exit(0)

    modes = dict(
        all     = lambda pkg : Package.build(pkg, skip_fetch=False),
        fetch   = lambda pkg : pkg.fetch(),
        nofetch = lambda pkg : Package.build(pkg, skip_fetch=True))

    try:
        for pkg in build:
            modes[opt.mode](pkg(e))
    except PackageError, e:
        die(e)

    rm_f('last-build')
    rm_f('last-install')
    os.symlink(e['BUILD_DIR'], 'last-build')
    os.symlink(e['INSTALL_DIR'], 'last-install')

    print('Install finished.\n\tSOURCE: %(DOWNLOAD_DIR)s\n\tBUILD: %(BUILD_DIR)s\n\tINSTALL: %(INSTALL_DIR)s' % e)
