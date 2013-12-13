#!/usr/bin/env python

from __future__ import print_function

import sys
code = -1
# Must have this check before importing other BB modules
if sys.version_info < (2, 6, 1):
    print('\nERROR: Must use Python 2.6.1 or greater.')
    sys.exit(code)

import time
import os.path as P
import os
import re
import logging
import string
from optparse import OptionParser
from BinaryBuilder import get_platform, die, run, Apps, write_asp_config
from BinaryDist import fix_install_paths
from Packages import geoid
from glob import glob

global logger
logger = logging.getLogger()

def usage(msg, code):
    parser.print_help()
    print('\n%s' % msg)
    sys.exit(code)

if __name__ == '__main__':

    parser = OptionParser(usage='%s tarball installdir' % sys.argv[0])
    parser.add_option('--debug',       dest='loglevel',  default=logging.INFO, action='store_const', const=logging.DEBUG, help='Turn on debug messages')
    parser.add_option("--skip-extracting-tarball",
                      action="store_true", dest="skip_extraction", default=False,
                      help="Skip the time-consuming tarball extraction (for debugging purposes)")

    global opt
    (opt, args) = parser.parse_args()

    if not len(args) == 2:
        usage('Missing required argument: installdir', code)
    tarball = P.realpath(args[0])
    installdir = P.realpath(args[1])
    if not P.exists(tarball):
        usage('Invalid tarball %s (does not exist)' % tarball, code)
    if not (P.exists(installdir)):
        os.makedirs(installdir)
    if not (P.isdir(installdir)):
        usage('Invalid installdir %s (not a directory)' % installdir, code)
    logging.basicConfig(level=opt.loglevel)

    if not opt.skip_extraction:
        print('Extracting tarball')
        run('tar', 'xf', tarball, '-C', installdir, '--strip-components', '1')

    arch = get_platform()
    fix_install_paths(installdir, arch)

    print('Writing config.options.vw')
    with file(P.join(installdir,'config.options.vw'), 'w') as config:
        print('ENABLE_DEBUG=yes',file=config)
        print('ENABLE_OPTIMIZE=yes',file=config)
        print('PREFIX=$PWD/build', file=config)
        print('ENABLE_RPATH=yes', file=config)
        print('ENABLE_STATIC=no', file=config)
        print('ENABLE_PKG_PATHS_DEFAULT=no', file=config)
        print('ENABLE_AS_NEEDED=yes', file=config)
        print('ENABLE_NO_UNDEFINED=yes', file=config)
        if arch.os == 'osx':
            print('CCFLAGS="-arch x86_64 -Wl,-rpath -Wl,%s"' % installdir, file=config)
            print('CXXFLAGS="-arch x86_64 -Wl,-rpath -Wl,%s"' % installdir, file=config)
            print('LDFLAGS="-Wl,-rpath -Wl,%s"' % (installdir), file=config)
        print('\n# You should enable modules that you want yourself', file=config)
        print('# Here are some simple modules to get you started', file=config)
        print('ENABLE_MODULE_MOSAIC=yes', file=config)
        print('ENABLE_MODULE_CAMERA=yes', file=config)
        print('ENABLE_MODULE_CARTOGRAPHY=yes', file=config)
        print('ENABLE_MODULE_STEREO=yes\n', file=config)
        print('BASE=%s' % installdir, file=config)

        install_pkgs = 'jpeg png gdal proj4 z ilmbase openexr boost flapack protobuf flann'.split()
        off_pkgs = 'tiff hdr cairomm x11 clapack slapack opencv cg zeromq rabbitmq_c qt_qmake arbitrary_qt apple_qmake_qt linux_qmake_qt guess_qt qt'.split()

        for pkg in install_pkgs:
            print('HAVE_PKG_%s=$BASE' % pkg.upper(), file=config)
            print('PKG_%s_CPPFLAGS="-I%s -I%s"' % (pkg.upper(), P.join('$BASE','noinstall','include'),
                                                   P.join('$BASE','include')), file=config)
            if pkg == 'gdal' and arch.os == 'linux':
                print('PKG_%s_LDFLAGS="-L%s -ltiff -ljpeg -lpng -lz -lopenjp2"' % (pkg.upper(),P.join('$BASE','lib')), file=config)
            else:
                print('PKG_%s_LDFLAGS="-L%s"' % (pkg.upper(),P.join('$BASE','lib')), file=config)
            if pkg == 'protobuf':
                print('PROTOC=$BASE/bin/protoc', file=config)

        for pkg in off_pkgs:
            print('HAVE_PKG_%s=no' % pkg.upper(), file=config)

    prefix       = '$PWD/build'
    vw_build     = '~/projects/visionworkbench/build'
    config_file  = P.join(installdir, 'config.options.asp')
    write_asp_config(prefix, installdir, vw_build, arch, geoid, config_file)

