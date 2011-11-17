#!/usr/bin/env python2.6

from __future__ import print_function

import time
import os.path as P
import logging
import string
from optparse import OptionParser
from BinaryBuilder import get_platform, die, run
from BinaryDist import is_binary, strip, otool
import sys
from glob import glob

def set_rpath_library(filename, toplevel, searchpath):
    assert not any(map(P.isabs, searchpath)), 'set_rpath: searchpaths must be relative to distdir (was given %s)' % (searchpath,)
    def linux():
        rel_to_top = P.relpath(toplevel, P.dirname(filename))
        rpath = [P.join('$ORIGIN', rel_to_top, path) for path in searchpath]
        if run('chrpath', '-r', ':'.join(rpath), filename, raise_on_failure = False) is None:
            logger.warn('Failed to set_rpath on %s' % filename)
    def osx():
        info = otool(filename)

        # soname is None for an executable
        if info.soname is not None:
            info.libs[info.soname] = info.sopath

        for soname, sopath in info.libs.iteritems():
            # /tmp/build/install/lib/libvwCore.5.dylib
            # base = libvwCore.5.dylib
            # looks for @executable_path/../lib/libvwCore.5.dylib

            # /opt/local/libexec/qt4-mac/lib/QtXml.framework/Versions/4/QtXml
            # base = QtXml.framework/Versions/4/QtXml
            # looks for @executable_path/../lib/QtXml.framework/Versions/4/QtXml

            # OSX rpath points to one specific file, not anything that matches the
            # library SONAME. We've already done a whitelist check earlier, so
            # ignore it if we can't find the lib we want

            # XXX: This code carries an implicit assumption that all
            # executables are one level below the root (because
            # @executable_path is always the exe path, not the path of the
            # current binary like $ORIGIN in linux)
            for rpath in searchpath:
                if P.exists(P.join(toplevel, rpath, soname)):
                    new_path = P.join('@loader_path', '..', rpath, soname)
                    # If the entry is the "self" one, it has to be changed differently
                    if info.sopath == sopath:
                        run('install_name_tool', '-id', filename, filename)
                        break
                    else:
                        run('install_name_tool', '-change', sopath, new_path, filename)
                        break

    locals()[get_platform().os]()

if __name__ == '__main__':
    parser = OptionParser(usage='%s tarball installdir' % sys.argv[0])
    parser.add_option('--debug',       dest='loglevel',  default=logging.INFO, action='store_const', const=logging.DEBUG, help='Turn on debug messages')

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
    if not (P.exists(installdir) and P.isdir(installdir)):
        usage('Invalid installdir %s (not a directory)' % installdir)
    logging.basicConfig(level=opt.loglevel)

    arch = get_platform()
    library_ext = "so"
    if arch.os == 'osx':
        library_ext = "dylib"

    print('Extracting tarball')
    run('tar', 'xf', tarball, '-C', installdir, '--strip-components', '1')

    ISISROOT = P.join(installdir,'isis')
    SEARCHPATH = [P.join(ISISROOT, 'lib'), P.join(ISISROOT,'3rdParty','lib'), P.join(installdir,'lib')]

    print('Fixing RPATHs')
    for curr_path in SEARCHPATH:
        for library in glob(P.join(curr_path,'*.'+library_ext+'*')):
            if not is_binary(library):
                continue
            print('  %s' % P.basename(library))
            try:
                set_rpath_library(library, installdir, map(lambda path: P.relpath(path, installdir), SEARCHPATH))
                #strip(filename) # Use this if you want to remove the debug symbols
            except:
                print('  Failed %s' % P.basename(library))

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
        print('ENABLE_PKG_PATH_DEFAULT=no', file=config)
        if arch.os == 'osx':
            print('CCFLAGS="-arch i386 -Wl,-rpath -Wl,%s"' % installdir, file=config)
            print('CXXFLAGS="-arch i386 -Wl,-rpath -Wl,%s"' % installdir, file=config)
        print('\n# You should enable modules that you want yourself', file=config)
        print('# Here are some simple modules to get you started', file=config)
        print('ENABLE_MODULE_MOSAIC=yes', file=config)
        print('ENABLE_MODULE_CAMERA=yes', file=config)
        print('ENABLE_MODULE_CARTOGRAPHY=yes', file=config)
        print('ENABLE_MODULE_STEREO=yes\n', file=config)
        print('BASE=%s' % installdir, file=config)

        install_pkgs = 'jpeg png gdal proj4 z ilmbase openexr boost flapack protobuf flann'.split()
        noinstall_pkgs = 'tiff hdr cairomm x11 clapack opencv cg'.split()

        for pkg in install_pkgs:
            print('HAVE_PKG_%s=$BASE' % pkg.upper(), file=config)
            print('PKG_%s_CPPFLAGS="-I%s -I%s"' % (pkg.upper(), P.join('$BASE','noinstall','include'),
                                                   P.join('$BASE','include')), file=config)
            if pkg == 'gdal' and arch.os == 'linux':
                print('PKG_%s_LDFLAGS="-L%s -L%s -ljpeg -lpng12 -lz"' % (pkg.upper(),P.join(ISISROOT,'3rdParty','lib'),P.join('$BASE','lib')), file=config)
            else:
                print('PKG_%s_LDFLAGS="-L%s -L%s"' % (pkg.upper(),P.join(ISISROOT,'3rdParty','lib'),P.join('$BASE','lib')), file=config)
            if pkg == 'protobuf':
                print('PROTOC=$BASE/bin/protoc', file=config)

        for pkg in noinstall_pkgs:
            print('HAVE_PKG_%s=no' % pkg.upper(), file=config)

    print('Writing config.options.asp')
    with file(P.join(installdir,'config.options.asp'), 'w') as config:
        print('ENABLE_DEBUG=yes',file=config)
        print('ENABLE_OPTIMIZE=yes',file=config)
        print('PREFIX=$PWD/build', file=config)
        print('ENABLE_RPATH=yes', file=config)
        print('ENABLE_STATIC=no', file=config)
        print('ENABLE_PKG_PATH_DEFAULT=no', file=config)
        if arch.os == 'osx':
            print('CCFLAGS="-arch i386"\nCXXFLAGS="-arch i386"', file=config)
        print('\n# You should enable modules that you want yourself', file=config)
        print('# Here are some simple modules to get you started', file=config)
        print('ENABLE_MODULE_CORE=yes', file=config)
        print('ENABLE_MODULE_SPICEIO=yes', file=config)
        print('ENABLE_MODULE_ISISIO=yes', file=config)
        print('ENABLE_MODULE_SESSIONS=yes\n', file=config)
        print('ENABLE_MODULE_CONTROLNETTK=no\n', file=config)
        print('ENABLE_MODULE_MPI=no\n', file=config)

        print('\n# You need to modify VW to point to the location of your VW install dir', file=config)
        print('VW=~/projects/visionworkbench/build', file=config)

        print('BASE=%s' % installdir, file=config)

        disable_apps = 'aligndem bundleadjust demprofile geodiff isisadjustcameraerr \
                        isisadjustcnetclip plateorthoproject reconstruct results \
                        rmax2cahvor rmaxadjust stereogui'.split()
        enable_apps  = 'bundlevis disparitydebug hsvmerge isisadjust orbitviz \
                        orthoproject point2dem point2mesh stereo mer2camera'.split()
        noinstall_pkgs = 'spice qwt gsl geos xercesc kakadu protobuf'.split()
        install_pkgs   = 'boost openscenegraph flapack arbitrary_qt curl \
                          ufconfig amd colamd cholmod flann'.split()
        vw_pkgs        = 'vw_core vw_math vw_image vw_fileio vw_camera \
                          vw_stereo vw_cartography vw_interest_point'.split()
        if arch.os == 'linux':
            noinstall_pkgs += ['superlu']

        print('\n# Applications', file=config)
        for app in disable_apps:
            print('ENABLE_APP_%s=no' % app.upper(), file=config)
        for app in enable_apps:
            print('ENABLE_APP_%s=yes' % app.upper(), file=config)

        print('\n# Dependencies', file=config)
        for pkg in install_pkgs + noinstall_pkgs:
            ldflags=[]
            ldflags.append('-L%s -L%s' % (P.join(ISISROOT,'3rdParty','lib'),P.join('$BASE','lib')))
            if arch.os == 'osx':
                ldflags.append('-F%s -F%s' % (P.join(ISISROOT,'3rdParty','lib'),P.join('$BASE','lib')))
            print('PKG_%s_LDFLAGS="%s"' % (pkg.upper(), ' '.join(ldflags)), file=config)
            print('PKG_%s_CPPFLAGS="-I%s -I%s"' % (pkg.upper(), P.join('$BASE','noinstall','include'),
                                                   P.join('$BASE','include')), file=config)
        for pkg in install_pkgs:
            print('HAVE_PKG_%s=$BASE' % pkg.upper(), file=config)
        for pkg in noinstall_pkgs:
            print('HAVE_PKG_%s=$BASE/noinstall' % pkg.upper(), file=config)
        for pkg in vw_pkgs:
            print('HAVE_PKG_%s=$VW' % pkg.upper(), file=config)

        qt_pkgs = 'QtCore QtGui QtNetwork QtSql QtSvg QtXml QtXmlPatterns'

        if arch.os == 'osx':
            libload = '-framework '
        else:
            libload = '-l'

        print('QT_ARBITRARY_MODULES="%s"' % qt_pkgs, file=config)

        includedir = P.join('$BASE','noinstall','include')
        qt_cppflags=['-I%s' % includedir]
        qt_libs=[]

        for module in qt_pkgs.split():
            qt_cppflags.append('-I%s/%s' % (includedir, module))
            qt_libs.append('%s%s' % (libload, module))

        print('PKG_ARBITRARY_QT_CPPFLAGS="%s"' %  ' '.join(qt_cppflags), file=config)
        print('PKG_ARBITRARY_QT_LIBS="%s"' %  ' '.join(qt_libs), file=config)
        print('PKG_ARBITRARY_QT_MORE_LIBS="-lpng -lz"', file=config)

        if arch.os == 'linux':
            print('PKG_SUPERLU_STATIC_LIBS=%s' % glob(P.join(ISISROOT, '3rdParty', 'lib', 'libsuperlu*.a'))[0], file=config)
        elif arch.os == 'osx':
            print('HAVE_PKG_SUPERLU=no', file=config)

        print('PKG_GEOS_LIBS=-lgeos-3.2.0', file=config)
        print('PROTOC=$BASE/bin/protoc', file=config)
        print('HAVE_PKG_ISIS=%s' % ISISROOT, file=config)
