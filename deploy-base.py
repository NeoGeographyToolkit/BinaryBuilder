#!/usr/bin/env python2.6

from __future__ import print_function

import time
import os.path as P
from os import makedirs
import logging
import string
from optparse import OptionParser
from BinaryBuilder import get_platform, die, run
from BinaryDist import is_binary, set_rpath
import sys
from glob import glob

global logger
logger = logging.getLogger()

if __name__ == '__main__':
    parser = OptionParser(usage='%s tarball installdir' % sys.argv[0])
    parser.add_option('--debug',       dest='loglevel',  default=logging.INFO, action='store_const', const=logging.DEBUG, help='Turn on debug messages')
    parser.add_option("--skip-extracting-tarball",
                      action="store_true", dest="skip_extraction", default=False,
                      help="Skip the time-consuming tarball extraction (for debugging purposes)")
    
    global opt
    (opt, args) = parser.parse_args()

    def usage(msg, code=-1):
        parser.print_help()
        print('\n%s' % msg)
        sys.exit(code)

    if not len(args) == 2:
        usage('Missing required argument: installdir')
    tarball = P.realpath(args[0])
    installdir = P.realpath(args[1])
    if not P.exists(tarball):
        usage('Invalid tarball %s (does not exist)' % tarball)
    if not (P.exists(installdir)):
        makedirs(installdir)
    if not (P.isdir(installdir)):
        usage('Invalid installdir %s (not a directory)' % installdir)
    logging.basicConfig(level=opt.loglevel)

    arch = get_platform()
    library_ext = "so"
    if arch.os == 'osx':
        library_ext = "dylib"

    if not opt.skip_extraction:
        print('Extracting tarball')
        run('tar', 'xf', tarball, '-C', installdir, '--strip-components', '1')
        
    SEARCHPATH = [P.join(installdir,'lib')]

    print('Fixing RPATHs')
    for curr_path in SEARCHPATH:
        for library in glob(P.join(curr_path,'*.'+library_ext+'*')):
            if not is_binary(library):
                continue
            print('  %s' % P.basename(library))
            try:
                set_rpath(library, installdir, map(lambda path: P.relpath(path, installdir), SEARCHPATH), False)
            except:
                print('  Failed %s' % P.basename(library))

    print('Fixing Binaries')
    for binary in glob(P.join(installdir,'bin','*')):
        if not is_binary(binary):
            continue
        print('  %s' % P.basename(binary))
        try:
            set_rpath(binary, installdir, map(lambda path: P.relpath(path, installdir), SEARCHPATH), False)
        except:
            print('  Failed %s' % P.basename(binary))

    print('Fixing Paths in libtool control files')
    for control in glob(P.join(installdir,'lib','*.la')):
        lines = []
        print('  %s' % P.basename(control))
        with open(control,'r') as f:
            lines = f.readlines()
        old_libdir = P.normpath(P.join(lines[-1][lines[-1].find("'")+1:lines[-1].rfind("'")],'..'))
        with open(control,'w') as f:
            for line in lines:
                f.write( string.replace(line,old_libdir,installdir) )

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
                print('PKG_%s_LDFLAGS="-L%s -ltiff -ljpeg -lpng -lz -lopenjpeg"' % (pkg.upper(),P.join('$BASE','lib')), file=config)
            else:
                print('PKG_%s_LDFLAGS="-L%s"' % (pkg.upper(),P.join('$BASE','lib')), file=config)
            if pkg == 'protobuf':
                print('PROTOC=$BASE/bin/protoc', file=config)

        for pkg in off_pkgs:
            print('HAVE_PKG_%s=no' % pkg.upper(), file=config)

    print('Writing config.options.asp')
    with file(P.join(installdir,'config.options.asp'), 'w') as config:
        print('ENABLE_DEBUG=yes',file=config)
        print('ENABLE_OPTIMIZE=yes',file=config)
        print('PREFIX=$PWD/build', file=config)
        print('ENABLE_RPATH=yes', file=config)
        print('ENABLE_STATIC=no', file=config)
        print('ENABLE_PKG_PATHS_DEFAULT=no', file=config)
        if arch.os == 'osx':
            print('CCFLAGS="-arch x86_64"\nCXXFLAGS="-arch x86_64"', file=config)
            print('LDFLAGS="-Wl,-rpath -Wl,%s"' % installdir, file=config)
        print('\n# You should enable modules that you want yourself', file=config)
        print('# Here are some simple modules to get you started', file=config)
        print('ENABLE_MODULE_CORE=yes', file=config)
        print('ENABLE_MODULE_SPICEIO=yes', file=config)
        print('ENABLE_MODULE_ISISIO=yes', file=config)
        print('ENABLE_MODULE_SESSIONS=yes', file=config)
        print('ENABLE_MODULE_CONTROLNETTK=no', file=config)
        print('ENABLE_MODULE_MPI=no\n', file=config)

        print('\n# You need to modify VW to point to the location of your VW install dir', file=config)
        print('VW=~/projects/visionworkbench/build', file=config)

        print('BASE=%s' % installdir, file=config)

        disable_apps = 'aligndem bundleadjust demprofile geodiff isisadjustcameraerr \
                        isisadjustcnetclip plateorthoproject reconstruct results \
                        rmax2cahvor rmaxadjust stereogui'.split()
        enable_apps  = 'bundlevis disparitydebug hsvmerge isisadjust orbitviz \
                        orthoproject point2dem point2las dem_adjust point2mesh stereo mer2camera'.split()
        install_pkgs   = 'boost openscenegraph flapack arbitrary_qt curl  \
                          ufconfig amd colamd cholmod flann spice qwt gsl \
                          geos xercesc protobuf superlu tiff              \
                          laszip liblas geoid isis superlu gdal'.split()
        off_pkgs       = 'zeromq rabbitmq_c qt_qmake clapack slapack vw_plate kakadu gsl_hasblas apple_qwt'.split()
        vw_pkgs        = 'vw_core vw_math vw_image vw_fileio vw_camera \
                          vw_stereo vw_cartography vw_interest_point'.split()

        print('\n# Applications', file=config)
        for app in disable_apps:
            print('ENABLE_APP_%s=no' % app.upper(), file=config)
        for app in enable_apps:
            print('ENABLE_APP_%s=yes' % app.upper(), file=config)

        print('\n# Dependencies', file=config)
        for pkg in install_pkgs:
            ldflags=[]
            ldflags.append('-L%s' % (P.join('$BASE','lib')))
            if arch.os == 'osx':
                ldflags.append('-F%s' % (P.join('$BASE','lib')))
            if pkg == 'gdal' and arch.os == 'linux':
                print('PKG_%s_LDFLAGS="-L%s -ltiff -ljpeg -lpng -lz -lopenjpeg"' % (pkg.upper(),P.join('$BASE','lib')), file=config)
            else:
                print('PKG_%s_LDFLAGS="%s"' % (pkg.upper(), ' '.join(ldflags)), file=config)
            print('PKG_%s_CPPFLAGS="-I%s"' % (pkg.upper(),
                                              P.join('$BASE','include')), file=config)
            if pkg == 'protobuf':
                print('PROTOC=$BASE/bin/protoc', file=config)

        for pkg in install_pkgs:
            print('HAVE_PKG_%s=$BASE' % pkg.upper(), file=config)
        for pkg in vw_pkgs:
            print('HAVE_PKG_%s=$VW' % pkg.upper(), file=config)
        for pkg in off_pkgs:
            print('HAVE_PKG_%s=no' % pkg.upper(), file=config)

        qt_pkgs = 'QtCore QtGui QtNetwork QtSql QtSvg QtXml QtXmlPatterns'

        print('QT_ARBITRARY_MODULES="%s"' % qt_pkgs, file=config)

        includedir = P.join('$BASE','include')
        qt_cppflags=['-I%s' % includedir]
        qt_libs=['-L%s' % P.join('$BASE','lib')]

        for module in qt_pkgs.split():
            qt_cppflags.append('-I%s/%s' % (includedir, module))
            qt_libs.append('-l%s' % module)

        print('PKG_ARBITRARY_QT_CPPFLAGS="%s"' %  ' '.join(qt_cppflags), file=config)
        print('PKG_ARBITRARY_QT_LIBS="%s"' %  ' '.join(qt_libs), file=config)
        print('PKG_ARBITRARY_QT_MORE_LIBS="-lpng -lz"', file=config)

        if arch.os == 'linux':
            print('PKG_SUPERLU_PLAIN_LIBS=%s' % glob(P.join(installdir, 'lib', 'libsuperlu*.so'))[0], file=config)

        print('PROTOC=$BASE/bin/protoc', file=config)
        print('MOC=$BASE/bin/moc',file=config)
        
        print('PKG_GEOID_CPPFLAGS="-I$BASE/include -DDEM_ADJUST_GEOID_PATH=$BASE/share/geoids"', file=config)
        
