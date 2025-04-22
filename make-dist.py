#!/usr/bin/env python

from __future__ import print_function

import sys
code = -1
# Must have this check before importing other BB modules
if sys.version_info < (2, 6, 1):
    print('\nERROR: Must use Python 2.6.1 or greater.')
    sys.exit(code)

from BinaryDist import grep, DistManager, DistPrefix, run

import logging, copy, re, os
import os.path as P
from optparse import OptionParser
from BinaryBuilder import die, program_exists
from BinaryDist import get_platform, required_libs
from glob import glob

# These are the libraries we're allowed to get from the base system.
# But we must not ship them as they cause trouble, especially libc.  A
# wildcard will be used after each of them.
LIB_SYSTEM_LIST = '''
    AGL.framework/Versions/A/AGL
    Accelerate.framework/Versions/A/Accelerate
    AppKit.framework/Versions/C/AppKit
    ApplicationServices.framework/Versions/A/ApplicationServices
    Carbon.framework/Versions/A/Carbon
    Cocoa.framework/Versions/A/Cocoa
    CoreFoundation.framework/Versions/A/CoreFoundation
    CoreServices.framework/Versions/A/CoreServices
    Foundation.framework/Versions/C/Foundation
    GLUT.framework/Versions/A/GLUT
    OpenGL.framework/Versions/A/OpenGL
    OpenCL.framework/Versions/A/OpenCL
    QuickTime.framework/Versions/A/QuickTime
    Security.framework/Versions/A/Security
    SystemConfiguration.framework/Versions/A/SystemConfiguration
    System/Library/Frameworks/GSS.framework/Versions/A/GSS
    GSS.framework/Versions/A/GSS
    vecLib.framework/Versions/A/vecLib
    CoreMedia.framework/Versions/A/CoreMedia
    AVFoundation.framework/Versions/A/AVFoundation
    QuartzCore.framework/Versions/A/QuartzCore
    CoreVideo.framework/Versions/A/CoreVideo
    IOKit.framework/Versions/A/IOKit
    XCTest.framework/Versions/A/XCTest
    DiskArbitration.framework/Versions/A/DiskArbitration
    CoreText.framework/Versions/A/CoreText
    QTKit.framework/Versions/A/QTKit
    CoreGraphics.framework/Versions/A/CoreGraphics
    CFNetwork.framework/Versions/A/CFNetwork
    ImageIO.framework/Versions/A/ImageIO
    VideoDecodeAcceleration.framework/Versions/A/VideoDecodeAcceleration
    AudioToolbox.framework/Versions/A/AudioToolbox
    VideoToolbox.framework/Versions/A/VideoToolbox
    Metal.framework/Versions/A/Metal
    IOSurface.framework/Versions/A/IOSurface
    ColorSync.framework/Versions/A/ColorSync
    GSS.framework/Versions/A/GSS
    Kerberos.framework/Versions/A/Kerberos

    libobjc.A.dylib
    libSystem.B.dylib
    libmathCommon.A.dylib

    libICE.so
    libSM.so
    libX11.so
    libXau.so
    libXext.so
    libXi.so
    libXmu.so
    libXrandr.so
    libXrender.so
    libXt.so
    libXxf86vm.so
    libc.so
    libc-
    libdl.so
    libdl-
    libm.so
    libm-
    libutil.so
    libutil-
    librt.so
    librt-
    libuuid.so
    libpthread.so.0
    libdbus-1.so.3.14.14
    libsystemd.so
    libX11-xcb.so
    libXdmcp.so
'''.split()

SKIP_IF_NOT_FOUND = []

if get_platform().os == 'linux':
    # Exclude this from shipping for Linux, but not for Mac, as then things don't work
    # TODO(oalexan1): May need to put libGL-related files back, but this works for now.
    LIB_SYSTEM_LIST += ['libresolv.so', 'libresolv-', 'libGL.so', 'libGLX.so', 'libGLdispatch.so']
else:
    # A recent OSX does not have this, and does not seem necessary
    SKIP_IF_NOT_FOUND += ['libXplugin.1.dylib']

# Lib files that we want to include that don't get pickep up automatically.
MANUAL_LIBS = '''libpcl_io_ply libopenjp2 libnabo libcurl libQt5Widgets_debug libQt5PrintSupport_debug libQt5Gui_debug libQt5Core_debug libicuuc libswresample libx264 libcsmapi libproj libproj.0 libGLX libGLdispatch'''.split()

# Prefixes of libs that we always ship
LIB_SHIP_PREFIX = '''libc++. libgfortran. libquadmath. libgcc_s. libgomp. libgobject-2.0. libgthread-2.0. libgmodule-2.0. libglib-2.0. libicui18n. libicuuc. libicudata. libdc1394. libxcb-xlib. libxcb.'''.split() # libssl. libcrypto.  libk5crypto. libcom_err. libkrb5support. libkeyutils. libresolv.

if get_platform().os == 'linux':
    MANUAL_LIBS += ['libnettle', 'libhogweed', 'libvorbis', 'libvorbisenc',
                    'libp11-kit', 'libopus', 'libFLAC']
else:
    # Need to have these on the Mac
    LIB_SHIP_PREFIX += ['libresolv.', 'libcups.', 'libc++abi.', 'libcrypto.']
    #MANUAL_LIBS += ['libintl']

USGSCSM_PLUGINS = ['libusgscsm']

def sibling_to(dir, name):
    ''' get a pathname for a directory 'name' which is a sibling of directory 'dir' '''
    return P.join(P.dirname(dir), P.basename(name))

# Keep this in sync with the function in libexec-funcs.sh
def isis_version(isisroot):
    isis_version_file = P.join(isisroot,'isis_version.txt')
    if not P.isfile(isis_version_file):
        raise Exception('Cannot find: %s' % isis_version_file)
        
    f = open(isis_version_file)
    raw     = f.readline().strip()
    version = raw.split('#')[0].strip().split('.') # Strip out comment first
    return ".".join(version[0:3])

def libc_version():
    locations=['/lib/x86_64-linux-gnu/libc.so.6', '/lib/i386-linux-gnu/libc.so.6',
               '/lib/i686-linux-gnu/libc.so.6', '/lib/libc.so.6', '/lib64/libc.so.6', '/lib32/libc.so.6']
    for library in locations:
        if P.isfile(library):
            output = run(library).split('\n')[0]
            return re.search(r'[^0-9.]*([0-9.]*).*',output).groups()
    return "FAILED"

if __name__ == '__main__':
    parser = OptionParser(usage='%s installdir' % sys.argv[0])
    parser.add_option('--debug',          dest='loglevel',    default=logging.INFO, action='store_const', const=logging.DEBUG, help='Turn on debug messages')
    parser.add_option('--include',        dest='include',     default='./whitelist', help='A file that lists the binaries for the dist')
    parser.add_option('--asp-deps-dir', dest='asp_deps_dir', default='', help='Path to where conda installed the ASP dependencies. Default: $HOME/miniconda3/envs/asp_deps.')
    parser.add_option('--python-env', dest='python_env', default='', help='Path of a conda-installed distribution having the same version of Python and numpy as in the ASP dependencies. Must be set. See StereoPipeline/docs/building_asp.rst for more info.')
    parser.add_option('--keep-temp',      dest='keeptemp',    default=False, action='store_true', help='Keep tmp distdir around for debugging')
    parser.add_option('--isisroot',       dest='isisroot',    default=None, help='Use a locally-installed isis at this root')
    parser.add_option('--force-continue', dest='force_continue', default=False, action='store_true', help='Continue despite errors. Not recommended.')

    global opt
    (opt, args) = parser.parse_args()
    
    def usage(msg, code=-1):
        parser.print_help()
        print('\n%s' % msg)
        sys.exit(code)

    if not args:
        usage('Missing required argument: install directory')

    if opt.asp_deps_dir == "":
        opt.asp_deps_dir = P.join(os.environ["HOME"], 'miniconda3/envs/asp_deps')
    if not P.exists(opt.asp_deps_dir):
        die('Cannot find the ASP dependencies directory installed with conda at ' + \
            opt.asp_deps_dir + '. Specify it via --asp-deps-dir.')

    if opt.python_env == "":
        die('\nMust specify --python-env.')
    # Check if it is a directory that exists
    if not P.exists(opt.python_env):
        die('\nCannot find the Python environment at ' + opt.python_env + '. Specify it via --python-env.')
    
    # TODO(oalexan1): Check that the Python environment has the same version of
    # Python and numpy as in the ASP dependencies.
    
    # ISISROOT env var must be set, as otherwise there's a crash on Mac Arm
    if 'ISISROOT' not in os.environ:
        die('The ISISROOT environment variable must be set.')

    installdir = P.realpath(args[0])
    if not (P.exists(installdir) and P.isdir(installdir)):
        usage('Invalid installdir %s (not a directory)' % installdir)
    if opt.isisroot is not None and not P.isdir(opt.isisroot):
        parser.print_help()
        die('\nIllegal argument to --isisroot: path does not exist')

    # Ensure asp_deps/bin is in the path, to be able to find chrpath, bzip2, etc.
    if "PATH" not in os.environ: os.environ["PATH"] = ""
    os.environ["PATH"] = P.join(opt.asp_deps_dir, 'bin') + os.pathsep + os.environ["PATH"]

    common_exec = ['bzip2', 'pbzip2', 'tar']
    missing_exec = []
    for program in common_exec:
        if not program_exists(program):
            missing_exec.append(program)
    if missing_exec:
        die('Missing required executables for building. You need to install: ', missing_exec)

    logging.basicConfig(level=opt.loglevel)

    lib_ext = '.dylib'
    if get_platform().os == 'linux':
        lib_ext = '.so'

    wrapper_file = 'libexec-helper.sh'
        
    INSTALLDIR = DistPrefix(installdir)
    mgr = DistManager(wrapper_file, INSTALLDIR, opt.asp_deps_dir)
    
    try:
        ISISROOT   = P.join(INSTALLDIR)
        SEARCHPATH = [INSTALLDIR.lib(), 
                      opt.asp_deps_dir + '/lib',
                      opt.asp_deps_dir + '/lib/csmplugins',
                      opt.asp_deps_dir + '/x86_64-conda-linux-gnu/sysroot/usr/lib64',
                      opt.asp_deps_dir + '/lib/pulseaudio',
                      '/usr/lib/x86_64-linux-gnu', '/usr/lib', '/opt/X11/lib']
        print('Search path = ' + str(SEARCHPATH))

        if get_platform().os == 'linux':
            if "PATH" not in os.environ:
                os.environ["PATH"] = ""
            os.environ["PATH"] = P.join(opt.asp_deps_dir, 'bin') + os.pathsep + \
                                 os.environ["PATH"]

        if opt.isisroot is not None:
            ISISROOT = opt.isisroot

        print('Adding requested files')

        sys.stdout.flush()
        with open(opt.include, 'r') as f:
            for line in f:
                line = line.strip()
                if line == "":
                    continue # skip empty lines
                mgr.add_glob(line, [INSTALLDIR, opt.asp_deps_dir])
            
        # Add some platform specific bugfixes
        if get_platform().os == 'linux':
            mgr.sym_link_lib('libproj.so', 'libproj.0.so')
            mgr.add_glob("lib/libQt5XcbQpa.*", [INSTALLDIR, opt.asp_deps_dir])
                                
        print('Adding the ISIS libraries')
        sys.stdout.flush()
        isis_secondary_set = set()
        for plugin in glob(P.join(INSTALLDIR,'lib','*.plugin')):
            with open(plugin,'r') as f:
                for line in f:
                    line = line.split()
                    if not len( line ):
                        continue
                    if line[0] == 'Library':
                        isis_secondary_set.add("lib/lib"+line[2]+"*")
        for library in isis_secondary_set:
            mgr.add_glob(library, [INSTALLDIR, opt.asp_deps_dir])

        # Add all libraries that link to isis, that is, specific instrument libs 
        for lib in glob(P.join(opt.asp_deps_dir, 'lib','*')):
            isIsisLib = False
            try:
                search_path = INSTALLDIR + "/lib" + ":" + opt.asp_deps_dir + "/lib"
                req = required_libs(lib, search_path)
                for key in req.keys():
                    if 'isis' in key:
                        isIsisLib = True
            except:
                pass
            if isIsisLib:
                mgr.add_glob(lib, [opt.asp_deps_dir])

        print('Adding ISIS and GLIBC version check')
        sys.stdout.flush()
        with mgr.create_file('libexec/constants.sh') as f: # Create constants file
            print('BAKED_ISIS_VERSION="%s"' % isis_version(opt.asp_deps_dir), file=f)
            print('\tFound ISIS version %s' % isis_version(opt.asp_deps_dir))
            print('BAKED_LIBC_VERSION="%s"' % libc_version(), file=f)
            if get_platform().os == 'linux':
                # glibc is for Linux only
                print('\tFound GLIBC version %s' % libc_version())

        print('Adding libraries')
        found_set = set()
        for i in range(2,10):
            print('\tPass %i to get dependencies of libraries' % i)
            sys.stdout.flush()
            deplist_copy = copy.deepcopy(mgr.deplist)

            # Force the use of these files
            for lib in MANUAL_LIBS:
                deplist_copy[lib + lib_ext] = ''
            for lib_dir in SEARCHPATH + ['/lib64']:
                for lib in deplist_copy:
                    lib_path = P.join(lib_dir, lib)
                    if P.exists(lib_path):
                        if lib in found_set:
                            # Already found, no need to search
                            # further, as then a copy of this may be
                            # found again in a different part of the
                            # system.
                            continue
                        
                        found_set.add(lib)
                        mgr.add_library(lib_path)
                        continue
                    
        # Handle the shiplist separately. This will also add more dependencies
        print('\tAdding forced-ship libraries')
        sys.stdout.flush()
        found_set = set()
        found_and_to_be_removed = []
        for copy_lib in LIB_SHIP_PREFIX:
            mgr_keys = mgr.deplist.copy().keys() # make a copy of the keys
            for soname in mgr_keys:
                if soname.startswith(copy_lib):
                    # Bugfix: Do an exhaustive search, as same prefix can
                    # refer to multiple libraries, e.g., libgfortran.so.3 and
                    # libgfortran.so.1, and sometimes the wrong one is picked.
                    if mgr.deplist[soname] in found_set:
                        continue
                    found_set.add(mgr.deplist[soname])
                    if mgr.deplist[soname] is not None:
                        mgr.add_library(mgr.deplist[soname])
                    else:
                        print("Skip empty deplist for: " + soname)
                    found_and_to_be_removed.append(soname)
        mgr.remove_deps(found_and_to_be_removed)

        print('\tRemoving system libs')
        sys.stdout.flush()
        mgr.remove_deps(LIB_SYSTEM_LIST)

        print('\tFinding deps in search path')
        sys.stdout.flush()
        nocopy_libs = [P.join(ISISROOT, 'lib'),
                       P.join(ISISROOT, '3rdParty', 'lib')]
        copy_libs = SEARCHPATH + \
                         ['/opt/X11/lib',
                          '/usr/lib',
                          '/usr/lib64',
                          '/lib64',
                          '/usr/lib/x86_64-linux-gnu/mesa',
                          '/usr/lib/x86_64-linux-gnu/mesa-egl',
                          '/lib/x86_64-linux-gnu',
                          '/usr/lib/x86_64-linux-gnu',
                          '/System/Library/Frameworks',
                          '/System/Library/Frameworks/Accelerate.framework/Versions/A/Frameworks',
                          '/usr/local/opt/python@3.12/Frameworks',
                          '/opt/local/lib/libomp'
                          ]
        mgr.resolve_deps(nocopy = nocopy_libs, copy = copy_libs)
        # TODO: Including system libraries rather than libaries we build
        # ourselves may be dangerous.
        if mgr.deplist:
            if not opt.force_continue:
                # For each lib, print who uses it:
                willThrow = False
                for lib in mgr.deplist.keys():
                    if lib in mgr.parentlib.keys():
                        print("Library '" + lib + "' is not found, and is needed by " \
                              + " ".join(mgr.parentlib[lib]) + "\n" )
                        if lib not in SKIP_IF_NOT_FOUND:
                            willThrow = True
                if willThrow:
                    msg = 'Failed to find some libs in the search path:\n\t%s' % \
                          '\n\t'.join(mgr.deplist.keys()) + "\n" + \
                          "No-copy search path: " + \
                          '\n\t'.join(nocopy_libs) + "\n" + \
                          "Copy search path: " + \
                          '\n\t'.join(copy_libs) + "\n"
                    raise Exception(msg)
            else:
                print("Warning: missing libs: " + '\n\t'.join(mgr.deplist.keys()) + "\n")
                
        print('Adding USGS CSM plugins')
        sys.stdout.flush()
        for lib_dir in SEARCHPATH:
            for lib in USGSCSM_PLUGINS:
                lib_path = P.join(lib_dir, lib + lib_ext)
                if P.exists(lib_path):
                    mgr.add_library(lib_path, add_deps = False, is_plugin = True)
                    continue

        print('Adding files in dist-add')
        mgr.add_directory('dist-add')

        # ISIS expects a full Python distribution to be shipped. See
        # the option --python-env for more details.
        # Add the directory wholesale. It is not easy to figure out
        # what can be excluded.
        print('Adding files in ' + opt.python_env)
        mgr.add_directory(opt.python_env)

        sys.stdout.flush()

        print('\tRemoving system libs')
        sys.stdout.flush()
        mgr.remove_already_added(LIB_SYSTEM_LIST)
        
        if get_platform().os != 'linux':
            # Bugfix for missing Python.framework on the Mac
            frameworkDir = '/usr/local/opt/python@3.12/Frameworks/Python.framework'
            try:
                mgr.add_directory(frameworkDir, mgr.distdir + '/lib/Python.framework')
            except:
                pass

        print('Baking RPATH and stripping binaries')
        # TODO(oalexan1): This step takes forever. It should be applied only to 
        # files in lib, bin, and libeexec. We ship many other files.
        sys.stdout.flush()
        # Create relative paths from SEARCHPATH. Use only the first two items.
        rel_search_path = list(map(lambda path: P.relpath(path, INSTALLDIR), SEARCHPATH[0:2]))
        mgr.bake(rel_search_path)

        mgr.make_tarball()
        
    finally:
        if not opt.keeptemp:
            mgr.remove_tempdir()
