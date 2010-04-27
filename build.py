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
                findfile, zlib_headers, png_headers

from BinaryBuilder import Package, Environment, PackageError, error, warn, get_platform

limit_symbols = None

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('--save-temps', action='store_true',  dest='save_temps', default=False, help='Save build files to check include paths')
    parser.add_option('--no-ccache',  action='store_false', dest='ccache',     default=True,  help='Disable ccache')

    global opt
    (opt, args) = parser.parse_args()

    if opt.ccache and opt.save_temps:
        warn('--cache and --save-temps conflict. Disabling ccache.')
        opt.ccache = False

    e = Environment(CC       = 'gcc',
                    CXX      = 'g++',
                    F77      = 'gfortran',
                    CFLAGS   = '-O3 -pipe',
                    CXXFLAGS = '-O3 -pipe',
                    LDFLAGS  = r'-Wl,-rpath,/%s' % ('a'*100),
                    MAKEOPTS='-j4', PATH=os.environ['PATH'], HOME='/tmp/build')

    arch = get_platform()

    if arch == 'linux32':
        limit_symbols = P.join(P.abspath(P.dirname(__file__)), 'glibc24.h')

    if arch[:5] == 'linux':
        e.append('LDFLAGS', '-Wl,-O1 -Wl,--enable-new-dtags -Wl,--hash-style=both')
    elif arch[:3] == 'osx':
        p = e.get('PATH', [])
        if p:
            p = p.split(':')
        e['PATH'] = ':'.join(['%s/local/coreutils/bin' % os.environ['HOME']] + p + ['/opt/local/bin'])
        e.append('LDFLAGS', '-Wl,-headerpad_max_install_names')

    # I should probably fix the gnu coreutils dep, but whatever
    if os.system('cp --version') != 0:
        error('Your cp doesn\'t appear to be GNU coreutils. Install coreutils and put it in your path.')
        sys.exit(-1)

    # XXX LDFLAGS? What?
    if limit_symbols is not None:
        e.append('LDFLAGS', '-include %s' % limit_symbols)

    if opt.ccache:
        compiler_dir = P.join(os.environ.get('TMPDIR', '/tmp'), 'mycompilers')
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

    if len(sys.argv) == 1:
        # Many things depend on isis 3rdparty, so do it first
        build = [isis, gsl_headers, geos_headers, superlu_headers, xercesc_headers, qt_headers, qwt_headers, cspice_headers]

        if arch[:5] == 'linux':
            build.extend([zlib, png])
        elif arch[:3] == 'osx':
            build.extend([zlib_headers, png_headers])

        build.extend([jpeg, proj, gdal, ilmbase, openexr, boost, osg])

        if arch[:5] == 'linux':
            build.append(lapack)

        build.extend([visionworkbench, stereopipeline])
    else:
        build = (globals()[pkg] for pkg in sys.argv[1:])

    try:
        for pkg in build:
            Package.build(pkg, e)

    except PackageError, e:
        error(e)

#png -> zlib
#boost -> bzip2
#gdal -> jpeg, png, proj
#openexr -> ilmbase zlib
#visionworkbench -> boost openexr gdal png
#stereopipeline -> gsl_headers, geos_headers, superlu_headers, xercesc_headers, qt_headers, qwt_headers, cspice_headers
