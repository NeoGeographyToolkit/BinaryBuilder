#!/usr/bin/env python

from __future__ import print_function

import os
import sys

from Packages import *
from BinaryBuilder import Package, Environment, PackageError, error

if __name__ == '__main__':
    e = Environment(CC='ccache gcc',  CFLAGS='',
                    CXX='ccache g++', CXXFLAGS='',
                    LDFLAGS=r'-Wl,-rpath,/make/some/room/for/it',
                    MAKEOPTS='-j4', PATH=os.environ['PATH'], HOME=os.environ['HOME'])

    if len(sys.argv) == 1:
        build = (zlib, bzip2, png, jpeg, proj, gdal, ilmbase, openexr, boost,
                 visionworkbench, gsl_headers, geos_headers, superlu_headers,
                 xercesc_headers, qt_headers, qwt_headers, cspice_headers, isis,
                 stereopipeline)
    else:
        build = (globals()[pkg] for pkg in sys.argv[1:])

    try:
        for pkg in build:
            if pkg == stereopipeline:
                e2 = e.copy()
                e2['LDFLAGS'] = e.get('LDFLAGS', '') + ' -Wl,-rpath-link,%s' % P.join(e['INSTALL_DIR'], '..', 'isis3', '3rdParty', 'lib')
                Package.build(pkg, e2)
            else:
                Package.build(pkg, e)

    except PackageError, e:
        error(e)

#png -> zlib
#boost -> bzip2
#gdal -> jpeg, png, proj
#openexr -> ilmbase zlib
#visionworkbench -> boost openexr gdal png
#stereopipeline -> gsl_headers, geos_headers, superlu_headers, xercesc_headers, qt_headers, qwt_headers, cspice_headers
