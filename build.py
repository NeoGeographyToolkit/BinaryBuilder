#!/usr/bin/env python

from __future__ import print_function

import os
import os.path as P
import subprocess
import sys
from optparse import OptionParser


from Packages import isis, gsl_headers, geos_headers, superlu_headers, xercesc_headers,\
                qt_headers, qwt_headers, cspice_headers, zlib, png, jpeg, proj, gdal,\
                ilmbase, openexr, boost, osg, lapack, visionworkbench, stereopipeline,\
                zlib_headers, png_headers, isis_local, protobuf_headers, jpeg_headers

from BinaryBuilder import Package, Environment, PackageError, die, info, get_platform, findfile

limit_symbols = None

CC_FLAGS = ('CFLAGS', 'CXXFLAGS')
LD_FLAGS = ('LDFLAGS')
ALL_FLAGS = ('CFLAGS', 'CPPFLAGS', 'CXXFLAGS', 'LDFLAGS')

if __name__ == '__main__':
    parser = OptionParser()
    parser.set_defaults(mode='all')
    parser.add_option('--build-root',                       dest='buildroot',  default='/tmp', help='Prefix of build dirs')
    parser.add_option('--no-ccache',  action='store_false', dest='ccache',     default=True,   help='Disable ccache')
    parser.add_option('--clean-build',action='store_true',  dest='clean_build',default=False,  help='Remove build files before starting run')
    parser.add_option('--coreutils',                        dest='coreutils',  default=None,   help='Bin directory holding GNU coreutils')
    parser.add_option('--dev-env',    action='store_true',  dest='dev',        default=False,  help='Build everything but VW and ASP')
    parser.add_option('--fetch',      action='store_const', dest='mode',       const='fetch',  help='Fetch sources only, don\'t build')
    parser.add_option('--no-fetch',   action='store_const', dest='mode',       const='nofetch',help='Build, but do not fetch (will fail if sources are missing)')
    parser.add_option('--isisroot',                         dest='isisroot',   default=None,   help='Use a locally-installed isis at this root')
    parser.add_option('--pretend',    action='store_true',  dest='pretend',    default=False,  help='Show the list of packages without actually doing anything')
    parser.add_option('--save-temps', action='store_true',  dest='save_temps', default=False,  help='Save build files to check include paths')
    parser.add_option('--threads',                          dest='threads',    default=4,      help='Build threads to use')

    global opt
    (opt, args) = parser.parse_args()

    if opt.coreutils is not None:
        if not P.isdir(opt.coreutils):
            parser.print_help()
            die('Illegal argument to --coreutils: path does not exist')
        p = os.environ.get('PATH', [])
        if p:
            p = p.split(':')
        os.environ['PATH'] = ':'.join([opt.coreutils] + p + ['/opt/local/bin'])

    if opt.isisroot is not None and not P.isdir(opt.isisroot):
        parser.print_help()
        die('\nIllegal argument to --isisroot: path does not exist')

    if opt.ccache and opt.save_temps:
        die('--ccache and --save-temps conflict. Disabling ccache.')

    e = Environment(BUILDROOT = opt.buildroot,
                    CC       = 'gcc',
                    CXX      = 'g++',
                    F77      = 'gfortran',
                    CFLAGS   = '-O3 -g',
                    CXXFLAGS = '-O3 -g',
                    LDFLAGS  = r'-Wl,-rpath,/%s' % ('a'*100),
                    MAKEOPTS='-j%s' % opt.threads,
                    PATH=os.environ['PATH'],
                    **({} if opt.isisroot is None else dict(ISISROOT=opt.isisroot)))

    if opt.clean_build:
        e.remove_build_dirs()
    e.create_dirs()

    arch = get_platform()

    if arch[2] == 'linux32':
        limit_symbols = P.join(P.abspath(P.dirname(__file__)), 'glibc24.h')

    if arch[0] == 'linux':
        e.append('LDFLAGS', '-Wl,-O1 -Wl,--enable-new-dtags -Wl,--hash-style=both')
    elif arch[0] == 'osx':
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

    # I should probably fix the gnu coreutils dep, but whatever
    if os.system('cp --version &>/dev/null') != 0:
        die('Your cp doesn\'t appear to be GNU coreutils. Install coreutils and put it in your path.')

    e.append_many(ALL_FLAGS, '-m%i' % arch[1])

    # XXX LDFLAGS? What?
    if limit_symbols is not None:
        e.append('LDFLAGS', '-include %s' % limit_symbols)

    if opt.ccache:
        compiler_dir = P.join(opt.buildroot, 'mycompilers')
        new = dict(
            CC  = P.join(compiler_dir, e['CC']),
            CXX = P.join(compiler_dir, e['CXX']),
        )

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

        if arch[0] == 'linux':
            build.extend([zlib, png, jpeg])
        elif arch[0] == 'osx':
            build.extend([zlib_headers, png_headers, jpeg_headers])

        build.extend([proj, gdal, ilmbase, openexr, boost, osg])

        if arch[0] == 'linux':
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
