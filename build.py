#!/usr/bin/env python

from __future__ import print_function

import os
import sys

from Packages import *
from BinaryBuilder import Package, Environment, PackageError

if __name__ == '__main__':
    e = Environment(CC='ccache gcc', CFLAGS='', CXX='ccache g++', CXXFLAGS='', MAKEOPTS='-j4', PATH=os.environ['PATH'])

    if len(sys.argv) == 1:
        build = (zlib, png, jpeg, proj, gdal, ilmbase, openexr, boost, visionworkbench, isis, stereopipeline)
    else:
        build = (globals()[pkg] for pkg in sys.argv[1:])

    try:
        for pkg in build:
            Package.build(pkg, e)
    except PackageError, e:
        print('ERROR: ', e)
