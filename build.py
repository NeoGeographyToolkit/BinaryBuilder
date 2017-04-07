#!/usr/bin/env python

from __future__ import print_function
import sys
code = -1
# Must have this check before importing other BB modules
if sys.version_info < (2, 6, 1):
    print('\nERROR: Must use Python 2.6.1 or greater.')
    sys.exit(code)

import os
import os.path as P
import subprocess
import errno
import string
import types
import time
from optparse import OptionParser
from tempfile import mkdtemp
from distutils import version
from glob import glob
from Packages import *

from BinaryBuilder import Package, Environment, PackageError, die, info,\
     get_platform, findfile, run, get_prog_version, logger, warn, \
     binary_builder_prefix
from BinaryDist import fix_install_paths, which

CC_FLAGS = ('CFLAGS', 'CXXFLAGS')
LD_FLAGS = ('LDFLAGS')
ALL_FLAGS = ('CFLAGS', 'CPPFLAGS', 'CXXFLAGS', 'LDFLAGS')

# List of codes for build types
BUILD_GOAL_ASP     = 0 # Build everything (the default)
BUILD_GOAL_ASP_DEV = 1 # Build a full development environment
BUILD_GOAL_VW      = 2 # Build VW
BUILD_GOAL_VW_DEV  = 3 # Build a VW development environment

def get_cores():
    try:
        n = os.sysconf('SC_NPROCESSORS_ONLN')
        if n:
            return n
        return 2
    except:
        return 2

def makelink(src, dst):
    try:
        os.remove(dst)
    except OSError, o:
        if o.errno != errno.ENOENT: # Don't care if it wasn't there
            raise
    os.symlink(src, dst)

def grablink(dst):
    if not P.exists(dst):
        raise Exception('Cannot resume, no link %s exists!' % dst)
    ret = os.readlink(dst)
    if not P.exists(ret):
        raise Exception('Cannot resume, link target %s for link %s doesn\'t exist' % (ret, dst))
    return ret

def verify(program,check_help=False):
    def is_exec(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    def has_help(fpath):
        try:
            FNULL = open(os.devnull,'w')
            subprocess.check_call([fpath,"--help"],stdout=FNULL,stderr=FNULL)
            return True
        except subprocess.CalledProcessError:
            return False

    for path in os.environ["PATH"].split(os.pathsep):
        exec_file = os.path.join( path, program )
        if is_exec( exec_file):
            if check_help:
                if has_help(exec_file):
                    return True
            else:
                return True
    return False;

def summary(env_dict):
    print('===== Environment =====')
    for k in sorted(env_dict.keys()):
        print('%15s: %s' % (k,env_dict[k]))

def is_sequence(arg):
    # Returns true if current object is a tuple or list
    return (not hasattr(arg, "strip") and
            hasattr(arg, "__getitem__") or
            hasattr(arg, "__iter__"))

def get_chksum(name):
    try:
        pkg = globals()[name](build_env)
    except KeyError:
        return "none"
    chksum = pkg.chksum
    # sometimes chksum is a sequence
    if is_sequence(chksum): chksum = chksum[0]
    # sometimes chksum is a number
    chksum = str(chksum)
    return chksum

def read_done(done_file):
    # Read the packages already built. Ensure that the chksum agrees.
    print("\nReading: %s" % done_file)
    done = {}
    try:
        f = open(done_file, 'r')
        for line in f:
            a = line.rstrip("\n").split(" ")
            if len(a) != 2: continue
            name = a[0]; chksum = a[1]
            pkg_chksum = get_chksum(name)
            if chksum == pkg_chksum:
                done[name] = chksum
        f.close()
    except IOError:
        # Don't complain is the file is missing, that means no
        # packages were built yet.
        pass

    return done

def write_done(done, done_file):
    # Write the packages already built.
    f = open(done_file, 'w')
    for name in done:
        chksum = done[name]
        f.write(name + " " + chksum + "\n")
    f.close()

if __name__ == '__main__':
    parser = OptionParser()
    parser.set_defaults(mode='all')

    parser.add_option('--base',       action='append',      dest='base',         default=[],              help='Provide a tarball to use as a base system')
    parser.add_option('--build-root',                       dest='build_root',   default='./build_asp',            help='Root of the build and install')
    parser.add_option('--cc',                               dest='cc',           default='gcc',           help='Explicitly state which C compiler to use. [gcc (default), clang, gcc-mp-4.7]')
    parser.add_option('--cxx',                              dest='cxx',          default='g++',           help='Explicitly state which C++ compiler to use. [g++ (default), clang++, g++-mp-4.7]')
    parser.add_option('--build-goal', type='int',           dest='build_goal',   default=BUILD_GOAL_ASP,  help='Select the goal of the build.  Increasing numbers are smaller builds: [0 = Full ASP build, 1 = ASP/VW development build, 2 = VW build, 3 = VW development build]')
    parser.add_option('--download-dir',                     dest='download_dir', default='./tarballs', help='Where to archive source files')
    parser.add_option('--f77',                              dest='f77',          default='gfortran',      help='Explicitly state which Fortran compiler to use. [gfortran (default), gfortran-mp-4.7]')
    parser.add_option('--fetch',      action='store_const', dest='mode',         const='fetch',           help='Fetch sources only, don\'t build')
    parser.add_option('--libtoolize',                       dest='libtoolize',   default=None,            help='Value to set LIBTOOLIZE, use to override if system\'s default is bad.')
    parser.add_option('--no-ccache',  action='store_false', dest='ccache',       default=True,            help='Disable ccache')
    parser.add_option('--no-fetch',   action='store_const', dest='mode',         const='nofetch',         help='Build, but do not fetch (will fail if sources are missing)')
    parser.add_option('--osx-sdk-version',                  dest='osx_sdk',      default='10.6',          help='SDK version to use. Make sure you have the SDK version before requesting it.')
    parser.add_option('--pretend',    action='store_true',  dest='pretend',      default=False,           help='Show the list of packages without actually doing anything')
    parser.add_option('--resume',     action='store_true',  dest='resume',       default=False,           help='Reuse in-progress build/install dirs')
    parser.add_option('--save-temps', action='store_true',  dest='save_temps',   default=False,           help='Save build files to check include paths')
    parser.add_option('--threads',    type='int',           dest='threads',      default=get_cores(),     help='Build threads to use')
    parser.add_option('--fast',                             action='store_true', dest='fast',      default=False,           help='For any git package, update and build in existing directory rather than stating from scratch (may fail)')
    parser.add_option('--add-ld-library-path',              dest='ld_library_path', default=None,          help='This is a hack for the supercomputer that uses libstdc++ in a non-standard location. Please don\'t use this option unless you truly needed. This has the ability to corrupt our builds if you put /usr/lib or /lib as an argument.')

    global opt
    (opt, args) = parser.parse_args()

    info('Using %d build processes' % opt.threads)

    if opt.ccache and opt.save_temps:
        die('--save-temps was specified. Disable ccache with --no-ccache.')

    if opt.build_root is not None and not P.exists(opt.build_root):
        os.makedirs(opt.build_root)

    if opt.resume and opt.build_root is None:
        opt.build_root = grablink('last-run')

    if opt.build_root is None:
        opt.build_root = mkdtemp(prefix=binary_builder_prefix())

    # Things misbehave if directories have symlinks or are relative
    opt.build_root = P.realpath(opt.build_root)
    opt.download_dir = P.realpath(opt.download_dir)

    # We count in deploy-base.py on opt.build_root to contain the
    # string binary_builder_prefix()
    m = re.match("^.*?" + binary_builder_prefix(), opt.build_root)
    if not m:
        raise Exception('Build directory: %s must contain the string: "%s".'
                        % ( opt.build_root, binary_builder_prefix()) )

    makelink(opt.build_root, 'last-run')

    print("Using build root directory: %s" % opt.build_root)

    # Ensure that opt.build_root/install/bin is in the path, as there we keep
    # chrpath, etc.
    if "PATH" not in os.environ: os.environ["PATH"] = ""
    os.environ["PATH"] = P.join(opt.build_root, 'install/bin') + \
                         os.pathsep + os.environ["PATH"]

    MIN_CC_VERSION = 4.9

    # -Wl,-z,now ?
    build_env = Environment(
        CC       = opt.cc,
        CXX      = opt.cxx,
        F77      = opt.f77,
        CFLAGS   = '-O3 -g',
        CXXFLAGS = '-O3 -g',
        LDFLAGS  = r'-Wl,-rpath,/%s' % ('a'*100),
        MAKEOPTS = '-j%s' % opt.threads,
        DOWNLOAD_DIR = opt.download_dir,
        BUILD_DIR    = P.join(opt.build_root, 'build'),
        INSTALL_DIR  = P.join(opt.build_root, 'install'),
        MISC_DIR = P.join(opt.build_root, 'misc'),
        PKG_CONFIG_PATH = P.join(opt.build_root, 'install', 'lib', 'pkgconfig'),
        PATH = os.environ['PATH'],
        FAST = str(int(opt.fast))
        )

    if opt.ld_library_path is not None:
        build_env['LD_LIBRARY_PATH'] = opt.ld_library_path

    # Bugfix, add compiler's libraries to LD_LIBRARY_PATH.
    comp_path = which(build_env['CC'])
    libdir1 = P.join(P.dirname(P.dirname(comp_path)), "lib")
    libdir2 = P.join(P.dirname(P.dirname(comp_path)), "lib64")
    if 'LD_LIBRARY_PATH' not in build_env:
        build_env['LD_LIBRARY_PATH'] = ""
    build_env['LD_LIBRARY_PATH'] += ":" + libdir1 + ":" + libdir2

    arch = get_platform()

    # Check compiler version for compilers we hate
    output = run(build_env['CC'],'--version')
    if 'gcc' in build_env['CC']:
        output = output.lower()
        if "llvm" in output or "clang" in output:
            die('Your compiler is an LLVM-GCC hybrid. It is our experience that these tools can not compile Vision Workbench and Stereo Pipeline correctly. Please change your compiler choice.')

    #if arch.os == 'linux':
    ver1 = get_prog_version(build_env['CC'])
    ver2 = get_prog_version(build_env['CXX'])
    if ver1 < MIN_CC_VERSION or ver2 < MIN_CC_VERSION:
        die('Expecting gcc and g++ version >= ' + str(MIN_CC_VERSION))
        
    if arch.os == 'linux':
        build_env.append('LDFLAGS', '-Wl,-O1 -Wl,--enable-new-dtags -Wl,--hash-style=both')
        build_env.append_many(ALL_FLAGS, '-m%i' % arch.bits)

    elif arch.os == 'osx':
        build_env.append('LDFLAGS', '-Wl,-headerpad_max_install_names')
        osx_arch = 'x86_64' #SEMICOLON-DELIMITED

        ver = version.StrictVersion(arch.dist_version)

        # Transform 10.8.5 into 10.8
        ver_arr = str(ver).split("."); ver_arr = ver_arr[0:2]
        ver2 = ".".join(ver_arr)

        # Define SDK location. This moved in OSX 10.8
        sysroot = '/Developer/SDKs/MacOSX%s.sdk' % opt.osx_sdk
        if ver >= "10.8":
            sysroot = '/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX%s.sdk' % ver2
        if not os.path.isdir( sysroot ):
            die("Unable to open '%s'. Double check that you actually have the SDK for OSX %s." % (sysroot,opt.osx_sdk))

        # CMake needs these vars to not screw things up.
        build_env.append('OSX_SYSROOT', sysroot)
        build_env.append('OSX_ARCH', osx_arch)
        build_env.append('OSX_TARGET', opt.osx_sdk)

        build_env.append_many(ALL_FLAGS, ' '.join(['-arch ' + i for i in osx_arch.split(';')])) # OSX compiler extension
        #build_env.append_many(ALL_FLAGS, '-mmacosx-version-min=%s -isysroot %s' % (opt.osx_sdk, sysroot))
        build_env.append_many(ALL_FLAGS, '-m64')

        # # Resolve a bug with -mmacosx-version-min on 10.6 (see
        # # http://markmail.org/message/45nbrtxsxvsjedpn).
        # # Short version: 10.6 generates the new compact header (LD_DYLD_INFO)
        # # even when told to support 10.5 (which can't read it)
        if ver >= '10.6' and opt.osx_sdk == '10.5':
            build_env.append('LDFLAGS', '-Wl,-no_compact_linkedit')

    # if arch.osbits == 'linux32':
    #     limit_symbols = P.join(P.abspath(P.dirname(__file__)), 'glibc24.h')
    #     build_env.append('CPPFLAGS', '-include %s' % limit_symbols)

    compiler_dir = P.join(build_env['MISC_DIR'], 'mycompilers')
    if not P.exists(compiler_dir):
        os.makedirs(compiler_dir)

    # Deal with the Fortran compiler
    try:
        findfile(build_env['F77'], build_env['PATH'])
    except Exception:
        acceptable_fortran_compilers = [build_env['F77'],'g77']
        for i in range(0,10):
            acceptable_fortran_compilers.append("gfortran-mp-4.%s" % i)
        for compiler in acceptable_fortran_compilers:
            try:
                gfortran_path = findfile(compiler, build_env['PATH'])
                print("Found fortran at: %s" % gfortran_path)
                build_env['F77'] = compiler
                break
            except Exception:
                pass
    ver = get_prog_version(build_env['F77'])
    if ver < MIN_CC_VERSION:
        die('Expecting ' + build_env['F77'] + ' version >= ' + str(MIN_CC_VERSION))

    print("%s" % build_env['PATH'])

    if opt.save_temps:
        build_env.append_many(CC_FLAGS, '-save-temps')
    else:
        build_env.append_many(CC_FLAGS, '-pipe')

    if opt.libtoolize is not None:
        build_env['LIBTOOLIZE'] = opt.libtoolize

    # Verify we have the executables we need
    common_exec = ["make", "tar", "ln", "autoreconf", "cp", "sed", "bzip2", "unzip", "patch", "csh", "git", "svn", "wget"]
    compiler_exec = [ build_env['CC'],build_env['CXX'],build_env['F77'] ]
    if arch.os == 'linux':
        common_exec.extend( ["libtool"] )
    else:
        common_exec.extend( ["glibtool", "install_name_tool"] )

    missing_exec = []
    for program in common_exec:
        if not verify( program ):
            missing_exec.append(program)
    for program in compiler_exec:
        if not verify( program, True ):
            missing_exec.append(program)
    if missing_exec:
        die('Missing required executables for building. You need to install %s.' % missing_exec)

    build = []
    
    LINUX_DEPS1 = [m4, libtool, autoconf, automake]
    CORE_DEPS   = [cmake, bzip2, pbzip2] # For some reason these are inserted in the linux deps
    LINUX_DEPS2 = [chrpath, lapack]
    VW_DEPS     = [zlib, openssl, dsk, png,
                   jpeg, tiff, proj, openjpeg2, libgeotiff, gdal,
                   ilmbase, openexr, boost, flann, hdf5, opencv]
    ASP_DEPS    = [parallel, gsl, geos, xercesc, cspice, protobuf, 
                   superlu, gmm, osg3, qt, qwt, suitesparse, tnt,
                   jama, laszip, liblas, geoid, isis, eigen, gflags, glog, ceres,
                   libnabo, libpointmatcher, imagemagick, theia]

    if (len(args) == 0):
        # Specific package not specified, set packages according to the build goal.
        
        # These packages are always needed.
        if arch.os == 'linux':
            build.extend(LINUX_DEPS1)
        build.extend(CORE_DEPS)
        if arch.os == 'linux':
            build.extend(LINUX_DEPS2)
        build.extend(VW_DEPS)

        # Add ASP dependencies if needed
        if (opt.build_goal == BUILD_GOAL_ASP) or (opt.build_goal == BUILD_GOAL_ASP_DEV):
            build.extend(ASP_DEPS)
        
        # Add VW/ASP if not building a dev environment
        if (opt.build_goal == BUILD_GOAL_VW):
            build.extend([visionworkbench])
        if (opt.build_goal == BUILD_GOAL_ASP):
            build.extend([visionworkbench, stereopipeline])

    # Now handle the arguments the user supplied to us! This might be
    # additional packages or minus packages.
    if len(args) != 0:
        # Seperate the packages out that have a minus
        remove_build = [globals()[pkg[1:]] for pkg in args if pkg.startswith('_')]
        # Add the stuff without a minus in front of them
        build.extend( [globals()[pkg] for pkg in args if not pkg.startswith('_')] )
        for pkg in remove_build:
            build.remove( pkg )

    if opt.pretend:
        info('I want to build:\n%s' % ' '.join(map(lambda x: x.__name__, build)))
        summary(build_env)
        sys.exit(0)

    if opt.base and not opt.resume:
        print('Untarring base system')
        for base in opt.base:
            run('tar', 'xf', base, '-C', build_env['INSTALL_DIR'], '--strip-components', '1')
        fix_install_paths(build_env['INSTALL_DIR'], arch)

    # This must happen after untarring the base system,
    # as perhaps cache will be found there.
    if opt.ccache:

        try:
            ccache_path = findfile('ccache', build_env['PATH'])
        except:
            # If could not find ccache, build it.
            print("\n========== Building: %s ==========" % ccache.__name__)
            Package.build(ccache(build_env.copy_set_default()))
            ccache_path = findfile('ccache', build_env['PATH'])

        new = dict(
            CC  = P.join(compiler_dir, build_env['CC']),
            CXX = P.join(compiler_dir, build_env['CXX']),
        )

        subprocess.check_call(['ln', '-sf', ccache_path, new['CC']])
        subprocess.check_call(['ln', '-sf', ccache_path, new['CXX']])
        build_env.update(new)

    modes = dict(
        all     = lambda pkg : Package.build(pkg, skip_fetch=False),
        fetch   = lambda pkg : pkg.fetch(),
        nofetch = lambda pkg : Package.build(pkg, skip_fetch=True))

    # Build the packages, skipping the ones already done
    done_file = opt.build_root + "/done.txt"
    done = read_done(done_file)
    try:
        for pkg in build:
            name = pkg.__name__
            if name in done:
                print("Package %s was already built, skipping" % name)
                continue
            print("\n========== Building: %s ==========" % name)
            # Make several attempts, perhaps the servers are down.
            num=10
            for i in range(0,num):
                try:
                    # Build
                    modes[opt.mode](pkg(build_env.copy_set_default()))
                    # Mark as done
                    name = pkg.__name__
                    chksum = get_chksum(name)
                    done[name] = chksum
                    # Save the status after each package was built,
                    # in case the process gets interrupted.
                    write_done(done, done_file)
                    break
                except Exception, e:
                    print("Failed to build %s in attempt %d %s" %
                          (name, i, str(e)))
                    raise
                    #if i < num-1:
                    #    print("Sleep for 60 seconds and try again")
                    #    time.sleep(60)
                    #else:
                    #    raise

    except Exception, e:
        die(e)

    makelink(opt.build_root, 'last-completed-run')

    info('\n\nAll done!')
    summary(build_env)
