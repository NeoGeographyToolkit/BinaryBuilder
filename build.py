#!/usr/bin/env python

from __future__ import print_function

import os
import os.path as P
import sys
import subprocess

ccache = True

from Packages import isis, gsl_headers, geos_headers, superlu_headers, xercesc_headers,\
                qt_headers, qwt_headers, cspice_headers, zlib, png, jpeg, proj, gdal,\
                ilmbase, openexr, boost, osg, lapack, visionworkbench, stereopipeline,\
                findfile, zlib_headers, png_headers

from BinaryBuilder import Package, Environment, PackageError, error, get_platform

if __name__ == '__main__':
    e = Environment(CC       = 'gcc',
                    CXX      = 'g++',
                    F77      = 'gfortran',
                    CFLAGS   = '-O3 -pipe',
                    CXXFLAGS = '-O3 -pipe',
                    LDFLAGS  = r'-Wl,-rpath,/%s' % ('a'*100),
                    MAKEOPTS='-j4', PATH=os.environ['PATH'], HOME=os.environ['HOME'])

    arch = get_platform()

    if arch[:5] == 'linux':
        e['LDFLAGS'] = e.get('LDFLAGS', '') + ' -Wl,-O1'
    elif arch[:3] == 'osx':
        e['PATH'] = e['HOME'] + '/local/coreutils/bin:' + e['PATH'] + ':/opt/local/bin'
        e['LDFLAGS'] = e.get('LDFLAGS', '') + ' -Wl,-headerpad_max_install_names'

    if ccache:
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
    else:
        e['CFLAGS']   = e.get('CFLAGS', '')   + ' -save-temps'
        e['CXXFLAGS'] = e.get('CXXFLAGS', '') + ' -save-temps'

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
