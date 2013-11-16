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
import stat
import logging
import string
from optparse import OptionParser
from BinaryBuilder import get_platform, die, run, Apps
from BinaryDist import is_binary, set_rpath, binary_builder_prefix
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

    arch = get_platform()
    library_ext = ["so"]
    if arch.os == 'osx':
        library_ext.append("dylib")

    if not opt.skip_extraction:
        print('Extracting tarball')
        run('tar', 'xf', tarball, '-C', installdir, '--strip-components', '1')

    # Ensure installdir/bin is in the path, to be able to find chrpath, etc.
    if "PATH" not in os.environ: os.environ["PATH"] = ""
    os.environ["PATH"] = P.join(installdir, 'bin') + \
                         os.pathsep + os.environ["PATH"] 

    SEARCHPATH = [P.join(installdir,'lib'),
                  P.join(installdir,'lib','osgPlugins*')]

    print('Fixing RPATHs')
    for curr_path in SEARCHPATH:
        for extension in library_ext:
            for library in glob(P.join(curr_path,'*.'+extension+'*')):
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

    print('Fixing paths in libtool control files, etc.')
    control_files = glob(P.join(installdir,'include','*config.h')) + \
                    glob(P.join(installdir,'lib','*.la'))          + \
                    glob(P.join(installdir,'lib','*.prl'))         + \
                    glob(P.join(installdir,'lib','*', '*.pc'))     + \
                    glob(P.join(installdir,'bin','*-config'))      + \
                    glob(P.join(installdir,'mkspecs','*.pri'))

    for control in control_files:

        print('  %s' % P.basename(control))

        # ensure we can read and write (some files have odd permissions)
        st = os.stat(control)
        os.chmod(control, st.st_mode | stat.S_IREAD | stat.S_IWRITE)

        # replace the temporary install directory with the one we're deploying to.
        lines = []
        with open(control,'r') as f:
            lines = f.readlines()
        with open(control,'w') as f:
            for line in lines:
                line = re.sub('[\/\.]+[\w\/\.\-]*?' + binary_builder_prefix() + '\w*[\w\/\.]*?/install', installdir, line)
                f.write( line )

    # Create libblas.la (out of existing libsuperlu.la). We need
    # libblas.la to force blas to show up before superlu when linking
    # on Linux to avoid a bug with corruption when invoking lapack in
    # a multi-threaded environment.  A better long-term solution is
    # needed.
    superlu_la = installdir + '/lib/libsuperlu.la'
    blas_la = installdir + '/lib/libblas.la'
    if arch.os == 'linux' and os.path.exists(superlu_la):
        lines = []
        with open(superlu_la,'r') as f:
                lines = f.readlines()
        with open(blas_la,'w') as f:
            for line in lines:
                line = re.sub('libsuperlu', 'libblas', line)
                line = re.sub('dlname=\'.*?\'',
                              'dlname=\'libblas.so\'', line)
                line = re.sub('library_names=\'.+?\'',
                              'library_names=\'libblas.so\'', line)
                # Force blas to depend on superlu
                line = re.sub('dependency_libs=\'.*?\'',
                              'dependency_libs=\' -L' + installdir
                              + '/lib  -lsuperlu -lm\'', line)
                f.write( line )

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

    print('Writing config.options.asp')
    # To do: Fix duplication in writing config.options.asp in deploy_base.py
    # and class stereopipeline in Packages.py.
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

        disable_apps = Apps.disable_apps.split()
        enable_apps  = Apps.enable_apps.split()
        install_pkgs = Apps.install_pkgs.split()
        off_pkgs     = Apps.off_pkgs.split()
        vw_pkgs      = Apps.vw_pkgs.split()

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
                print('PKG_%s_LDFLAGS="-L%s -ltiff -ljpeg -lpng -lz -lopenjp2"' % (pkg.upper(),P.join('$BASE','lib')), file=config)
            else:
                print('PKG_%s_LDFLAGS="%s"' % (pkg.upper(), ' '.join(ldflags)), file=config)

            extra_path = ""
            if pkg == 'geoid':
                extra_path = " -DGEOID_PATH=$BASE/share/geoids-" + geoid.version
            print('PKG_%s_CPPFLAGS="-I%s%s"' % (pkg.upper(),
                                                P.join('$BASE','include'),
                                                extra_path), file=config)

            if pkg == 'protobuf':
                print('PROTOC=$BASE/bin/protoc', file=config)

        for pkg in install_pkgs:
            print('HAVE_PKG_%s=$BASE' % pkg.upper(), file=config)
        for pkg in vw_pkgs:
            print('HAVE_PKG_%s=$VW' % pkg.upper(), file=config)
        for pkg in off_pkgs:
            print('HAVE_PKG_%s=no' % pkg.upper(), file=config)

        qt_pkgs = Apps.qt_pkgs

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

        print('PROTOC=$BASE/bin/protoc', file=config)
        print('MOC=$BASE/bin/moc',file=config)

        print('PKG_EIGEN_CPPFLAGS="-I%s/eigen3"' % includedir, file=config)
        print('PKG_LIBPOINTMATCHER_CPPFLAGS="-I%s"' % includedir,
              file=config)
