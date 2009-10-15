#!/usr/bin/env python

from __future__ import print_function

import os
import os.path as P
import sys
import subprocess

ccache = True
limit_symbols = None
save_temps = False

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
                    LDFLAGS  = r'-Wl,--enable-new-dtags -Wl,--hash-style=both -Wl,-rpath,/%s' % ('a'*100),
                    MAKEOPTS='-j4', PATH=os.environ['PATH'], HOME='/tmp/build')

    arch = get_platform()

    if arch == 'linux32':
        limit_symbols = P.join(P.abspath(P.dirname(__file__)), 'glibc24.h')
    if arch[:5] == 'linux':
        e.append('LDFLAGS', '-Wl,-O1')
    elif arch[:3] == 'osx':
        p = e.get('PATH', [])
        if p:
            p = p.split(':')
        e['PATH'] = ':'.join(['/home/mlundy/local/coreutils/bin'] + p + ['/opt/local/bin'])
        e.append('LDFLAGS', '-Wl,-headerpad_max_install_names')

    if limit_symbols is not None:
        e.append('LDFLAGS', '-include %s' % limit_symbols)

    if ccache and not save_temps:
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

    if save_temps:
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
