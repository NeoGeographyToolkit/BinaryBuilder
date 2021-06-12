#!/usr/bin/env python

from __future__ import print_function

import sys
code = -1
# Must have this check before importing other BB modules
if sys.version_info < (2, 6, 1):
    print('\nERROR: Must use Python 2.6.1 or greater.')
    sys.exit(code)

from BinaryDist import grep, DistManager, Prefix, run

import time, logging, copy, re, os
import os.path as P
from optparse import OptionParser
from BinaryBuilder import die
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
    QuickTime.framework/Versions/A/QuickTime
    Security.framework/Versions/A/Security
    SystemConfiguration.framework/Versions/A/SystemConfiguration
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
    libdl.so
    libm.so
    libpthread.so.0
    librt.so
    libuuid.so
    libc-
    libdbus-1.so.3.14.14
    libsystemd.so
'''.split()

# Lib files that we want to include that don't get pickep up automatically.
MANUAL_LIBS = '''libpcl_io_ply libopenjp2 libnabo libcurl libQt5Widgets_debug libQt5PrintSupport_debug libQt5Gui_debug libQt5Core_debug libMagickCore-6.Q16 libMagickWand-6.Q16 libicuuc libswresample libx264 libcsmapi libproj libproj.0 libGLX libGLdispatch'''.split()

# Prefixes of libs that we always ship
LIB_SHIP_PREFIX = '''libc++. libgfortran. libquadmath. libgcc_s. libgomp. libgobject-2.0. libgthread-2.0. libgmodule-2.0. libglib-2.0. libicui18n. libicuuc. libicudata. libdc1394. libxcb-xlib. libxcb.'''.split() # libssl. libcrypto.  libk5crypto. libcom_err. libkrb5support. libkeyutils. libresolv.

USGSCSM_PLUGINS = ['libusgscsm']

def tarball_name():
    arch = get_platform()
    if opt.version is not None:
        return '%s-%s-%s-%s%s' % (opt.name, opt.version, arch.machine, arch.dist_name, arch.dist_version)
    else:
        git = run('git', 'describe', '--always', '--dirty', output=False, raise_on_failure=False)
        if git is None: git = ''
        if len(git): git = '%s' % git.strip()
        return '%s-%s-%s%s-%s%s' % (opt.name, arch.machine, arch.dist_name, arch.dist_version, time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime()), git)

def sibling_to(dir, name):
    ''' get a pathname for a directory 'name' which is a sibling of directory 'dir' '''
    return P.join(P.dirname(dir), P.basename(name))

# Keep this in sync with the function in libexec-funcs.sh
def isis_version(isisroot):
    # Check the ISIS version
    if P.isfile(P.join(isisroot,'version')):
        f       = open(P.join(isisroot,'version'),'r')
        raw     = f.readline().strip()
        version = raw.split('#')[0].strip().split('.') # Strip out comment first
        return ".".join(version[0:3])
    # TODO(oalexan1): The isis headers will move from here the miniconda dir at some point
    header = P.join(isisroot, 'include/isis/Constants.h')
    m      = grep('version\("(.*?)"', header)
    if not m:
        raise Exception('Unable to locate ISIS version header (expected at %s). Perhaps your ISISROOT (%s) is incorrect?' 
                        % (header, isisroot))
    return m[0].group(1)

def libc_version():
    locations=['/lib/x86_64-linux-gnu/libc.so.6', '/lib/i386-linux-gnu/libc.so.6',
               '/lib/i686-linux-gnu/libc.so.6', '/lib/libc.so.6', '/lib64/libc.so.6', '/lib32/libc.so.6']
    for library in locations:
        if P.isfile(library):
            output = run(library).split('\n')[0]
            return re.search('[^0-9.]*([0-9.]*).*',output).groups()
    return "FAILED"

if __name__ == '__main__':
    parser = OptionParser(usage='%s installdir' % sys.argv[0])
    parser.add_option('--debug',          dest='loglevel',    default=logging.INFO, action='store_const', const=logging.DEBUG, help='Turn on debug messages')
    parser.add_option('--include',        dest='include',     default='./whitelist', help='A file that lists the binaries for the dist')
    parser.add_option('--asp-deps-dir', dest='asp_deps_dir', default='', help='Path to where conda installed the ASP dependencies. Default: $HOME/miniconda3/envs/asp_deps.')
    parser.add_option('--debug-build',    dest='debug_build', default=False, action='store_true', help='Create a build having debug symbols')
    parser.add_option('--vw-build',       dest='vw_build',    default=False, action='store_true', help='Set to true when packaging a non-ASP build')
    parser.add_option('--keep-temp',      dest='keeptemp',    default=False, action='store_true', help='Keep tmp distdir around for debugging')
    parser.add_option('--set-version',    dest='version',     default=None, help='Set the version number to use for the generated tarball')
    parser.add_option('--set-name',       dest='name',        default='StereoPipeline', help='Tarball name for this dist')
    parser.add_option('--isisroot',       dest='isisroot',    default=None, help='Use a locally-installed isis at this root')
    parser.add_option('--force-continue', dest='force_continue', default=False, action='store_true', help='Continue despite errors. Not recommended.')

    global opt
    (opt, args) = parser.parse_args()

    def usage(msg, code=-1):
        parser.print_help()
        print('\n%s' % msg)
        sys.exit(code)

    if not args:
        usage('Missing required argument: installdir')

    if opt.asp_deps_dir == "":
        opt.asp_deps_dir = P.join(os.environ["HOME"], 'miniconda3/envs/asp_deps')
    if not P.exists(opt.asp_deps_dir):
        die('Cannot find the ASP dependencies directory installed with conda at ' + opt.asp_deps_dir + '. Specify it via --asp-deps-dir.')

    # If the user specified a VW build, update some default options.
    if opt.vw_build:
        if opt.include == './whitelist':
            opt.include = './whitelist_vw'
        if opt.name == 'StereoPipeline':
            opt.name = 'VisionWorkbench'

    installdir = P.realpath(args[0])
    if not (P.exists(installdir) and P.isdir(installdir)):
        usage('Invalid installdir %s (not a directory)' % installdir)
    if opt.isisroot is not None and not P.isdir(opt.isisroot):
        parser.print_help()
        die('\nIllegal argument to --isisroot: path does not exist')

    # Ensure installdir/bin is in the path, to be able to find chrpath, etc.
    if "PATH" not in os.environ: os.environ["PATH"] = ""
    os.environ["PATH"] = P.join(installdir, 'bin') + os.pathsep + os.environ["PATH"]

    logging.basicConfig(level=opt.loglevel)

    lib_ext = '.dylib'
    if get_platform().os == 'linux':
        lib_ext = '.so'

    wrapper_file = 'libexec-helper.sh'
    if (opt.vw_build):
        wrapper_file = 'libexec-helper_vw.sh'
    mgr = DistManager(tarball_name(), wrapper_file, opt.asp_deps_dir)

    try:
        INSTALLDIR = Prefix(installdir)
        ISISROOT   = P.join(INSTALLDIR)
        SEARCHPATH = [INSTALLDIR.lib(), opt.asp_deps_dir + '/lib',
                      opt.asp_deps_dir + '/x86_64-conda-linux-gnu/sysroot/usr/lib64',
                      '/usr/lib/x86_64-linux-gnu']
        print('Search path = ' + str(SEARCHPATH))

        # Bug fix for osg3. Must set LD_LIBRARY_PATH for ldd to later
        # work correctly on Ubuntu 13.10.
        if get_platform().os == 'linux':
            if "PATH" not in os.environ:
                os.environ["PATH"] = ""
            os.environ["PATH"] = P.join(opt.asp_deps_dir, 'bin') + os.pathsep + \
                                 os.environ["PATH"]

            if "LD_LIBRARY_PATH" not in os.environ:
                os.environ["LD_LIBRARY_PATH"] = ""
            os.environ["LD_LIBRARY_PATH"] = INSTALLDIR.lib() + \
                                            os.pathsep + os.environ["LD_LIBRARY_PATH"]

        if opt.isisroot is not None:
            ISISROOT = opt.isisroot

        if opt.include == 'all':
            mgr.add_directory(INSTALLDIR, hardlink=True)
            mgr.make_tarball()
            sys.exit(0)

        print('Adding requested files')

        sys.stdout.flush()
        with open(opt.include, 'r') as f:
            for line in f:
                line = line.strip()
                mgr.add_glob(line, [INSTALLDIR, opt.asp_deps_dir])
            
        # Add some platform specific bugfixes
        if get_platform().os == 'linux':
            mgr.sym_link_lib('libproj.so', 'libproj.0.so')
            mgr.add_glob("lib/libQt5XcbQpa.*", [INSTALLDIR, opt.asp_deps_dir])
                                
        if not opt.vw_build:
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
                    req = required_libs(lib)
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
            if not opt.vw_build:
                print('BAKED_ISIS_VERSION="%s"' % isis_version(opt.asp_deps_dir), file=f)
                print('\tFound ISIS version %s' % isis_version(opt.asp_deps_dir))
            print('BAKED_LIBC_VERSION="%s"' % libc_version(), file=f)
            if get_platform().os == 'linux':
                # glibc is for Linux only
                print('\tFound GLIBC version %s' % libc_version())

        print('Adding libraries')
        for i in range(2,4):
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
        mgr.resolve_deps(nocopy = [P.join(ISISROOT, 'lib'), P.join(ISISROOT, '3rdParty', 'lib')],
                         copy = SEARCHPATH + \
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
                          '/opt/local/lib/libomp'
                          ])
        # TODO: Including system libraries rather than libaries we build ourselves may be dangerous!
        if mgr.deplist:
            if not opt.force_continue:
                # For each lib, print who uses it:
                for lib in mgr.deplist.keys():
                    if lib in mgr.parentlib.keys():
                        print("Library " + lib + " is not found, and is needed by " \
                              + " ".join(mgr.parentlib[lib]) + "\n" )
                raise Exception('Failed to find some libs in any of our dirs:\n\t%s' % \
                                '\n\t'.join(mgr.deplist.keys()))
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
        sys.stdout.flush()
        # To do: Don't depend on cwd
        for dir in ['dist-add']:
            if P.exists(dir):
                mgr.add_directory(dir)

        print('\tRemoving system libs')
        sys.stdout.flush()
        mgr.remove_already_added(LIB_SYSTEM_LIST)

        print('Baking RPATH and stripping binaries')
        sys.stdout.flush()
        # Create relative paths from SEARCHPATH. Use only the first two items,
        # hence just the values 'lib' and 'lib64'.
        rel_search_path = list(map(lambda path: P.relpath(path, INSTALLDIR), SEARCHPATH[0:2]))
        mgr.bake(rel_search_path)

        debug_list_name = ''
        try:
            debuglist = mgr.find_filter('-name', '*.debug')
            debug_list_name = debuglist.name
        except:
            pass
        
        mgr.make_tarball(exclude = [debug_list_name])
        if P.getsize(debug_list_name) > 0 and opt.debug_build:
            mgr.make_tarball(include = debug_list_name, name = '%s-debug.tar.bz2' % mgr.tarname)
    finally:
        if not opt.keeptemp:
            mgr.remove_tempdir()
