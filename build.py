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
                findfile, zlib_headers, png_headers, isis_local, protobuf_headers

from BinaryBuilder import Package, Environment, PackageError, die, info, get_platform

limit_symbols = None

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('--save-temps', action='store_true',  dest='save_temps', default=False,  help='Save build files to check include paths')
    parser.add_option('--no-ccache',  action='store_false', dest='ccache',     default=True,   help='Disable ccache')
    parser.add_option('--threads',                          dest='threads',    default=4,      help='Build threads to use')
    parser.add_option('--base-dir',                         dest='basedir',    default='/tmp', help='Prefix of build dirs')
    parser.add_option('--isisroot',                         dest='isisroot',   default=None,   help='Use a locally-installed isis at this root')
    parser.add_option('--dev-env',    action='store_true',  dest='dev',        default=False,  help='Build everything but VW and ASP')
    parser.add_option('--coreutils',                        dest='coreutils',  default=None,   help='Bin directory holding GNU coreutils')
    parser.add_option('--pretend',    action='store_true',  dest='pretend',    default=False,  help='Show the list of packages without actually doing anything')

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

    e = Environment(BASEDIR  = opt.basedir,
                    CC       = 'gcc',
                    CXX      = 'g++',
                    F77      = 'gfortran',
                    CFLAGS   = '-O3 -pipe -g',
                    CXXFLAGS = '-O3 -pipe -g',
                    LDFLAGS  = r'-Wl,-rpath,/%s' % ('a'*100),
                    MAKEOPTS='-j%s' % opt.threads,
                    PATH=os.environ['PATH'],
                    **({} if opt.isisroot is None else dict(ISISROOT=opt.isisroot)))

    arch = get_platform()

    if arch == 'linux32':
        limit_symbols = P.join(P.abspath(P.dirname(__file__)), 'glibc24.h')

    if arch[:5] == 'linux':
        e.append('LDFLAGS', '-Wl,-O1 -Wl,--enable-new-dtags -Wl,--hash-style=both')
    elif arch[:3] == 'osx':
        e.append('LDFLAGS', '-Wl,-headerpad_max_install_names')

    # I should probably fix the gnu coreutils dep, but whatever
    if os.system('cp --version &>/dev/null') != 0:
        die('Your cp doesn\'t appear to be GNU coreutils. Install coreutils and put it in your path.')

    # XXX LDFLAGS? What?
    if limit_symbols is not None:
        e.append('LDFLAGS', '-include %s' % limit_symbols)

    if opt.ccache:
        compiler_dir = P.join(opt.basedir, 'mycompilers')
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
    elif opt.save_temps:
        e.append('CFLAGS',   '-save-temps')
        e.append('CXXFLAGS', '-save-temps')

    if len(args) == 0:
        # Were we told what isis to use?
        build = [isis_local if opt.isisroot is not None else isis]

        # Many things depend on isis 3rdparty, so do it before the rest
        build += [gsl_headers, geos_headers, superlu_headers, xercesc_headers, qt_headers, qwt_headers, cspice_headers, protobuf_headers]

        if arch[:5] == 'linux':
            build.extend([zlib, png])
        elif arch[:3] == 'osx':
            build.extend([zlib_headers, png_headers])

        build.extend([jpeg, proj, gdal, ilmbase, openexr, boost, osg])

        if arch[:5] == 'linux':
            build.append(lapack)

        if not opt.dev:
            build.extend([visionworkbench, stereopipeline])
    else:
        build = (globals()[pkg] for pkg in args)

    if opt.pretend:
        info('I want to build:\n%s' % ' '.join(map(lambda x: x.__name__, build)))
        sys.exit(0)

    try:
        for pkg in build:
            Package.build(pkg, e)

    except PackageError, e:
        die(e)

#png -> zlib
#gdal -> jpeg, png, proj
#openexr -> ilmbase zlib
#visionworkbench -> boost openexr gdal png
#stereopipeline -> gsl_headers, geos_headers, superlu_headers, xercesc_headers, qt_headers, qwt_headers, cspice_headers
