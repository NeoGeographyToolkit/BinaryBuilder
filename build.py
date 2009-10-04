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
        build = (zlib, png, jpeg, proj, gdal, ilmbase, openexr, boost, visionworkbench)
    else:
        build = (globals()[pkg] for pkg in sys.argv[1:])

    try:
        for pkg in build:
            Package.build(pkg, e)
    except PackageError, e:
        error(e)
