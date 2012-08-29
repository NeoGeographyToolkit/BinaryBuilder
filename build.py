#!/usr/bin/env python

from __future__ import print_function

import os
import os.path as P
import subprocess
import sys
import errno
import string
import types
from optparse import OptionParser
from tempfile import mkdtemp, gettempdir
from distutils import version
from glob import glob

from Packages import gsl, geos, superlu, gmm, xercesc, cspice, qt, qwt, \
     zlib, tiff, png, jpeg, proj, gdal, ilmbase, openexr,   \
     boost, osg, lapack, visionworkbench, stereopipeline, protobuf, flann, curl, \
     ufconfig, amd, colamd, cholmod, tnt, jama, laszip, liblas, isis

from BinaryBuilder import Package, Environment, PackageError, die, info, get_platform, \
     findfile, run, get_gcc_version, logger, warn
from BinaryDist import is_binary, set_rpath

CC_FLAGS = ('CFLAGS', 'CXXFLAGS')
LD_FLAGS = ('LDFLAGS')
ALL_FLAGS = ('CFLAGS', 'CPPFLAGS', 'CXXFLAGS', 'LDFLAGS')

def get_cores():
    try:
        n = os.sysconf('SC_NPROCESSORS_ONLN')
        return n if n else 2
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

def verify(program):
    def is_exec(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    for path in os.environ["PATH"].split(os.pathsep):
        exec_file = os.path.join( path, program )
        if is_exec( exec_file ):
            return
    raise Exception('Cannot find executable "%s" in path' % program)

def summary(env):
    print('===== Environment =====')
    for k in sorted(env.keys()):
        print('%15s: %s' % (k,env[k]))

if __name__ == '__main__':
    parser = OptionParser()
    parser.set_defaults(mode='all')

    parser.add_option('--base',       action='append',      dest='base',         default=[],              help='Provide a tarball to use as a base system')
    parser.add_option('--no-ccache',  action='store_false', dest='ccache',       default=True,            help='Disable ccache')
    parser.add_option('--libtoolize',                       dest='libtoolize',   default=None,            help='Value to set LIBTOOLIZE, use to override if system\'s default is bad.')
    parser.add_option('--dev-env',    action='store_true',  dest='dev',          default=False,           help='Build everything but VW and ASP')
    parser.add_option('--fetch',      action='store_const', dest='mode',         const='fetch',           help='Fetch sources only, don\'t build')
    parser.add_option('--no-fetch',   action='store_const', dest='mode',         const='nofetch',         help='Build, but do not fetch (will fail if sources are missing)')
    parser.add_option('--pretend',    action='store_true',  dest='pretend',      default=False,           help='Show the list of packages without actually doing anything')
    parser.add_option('--save-temps', action='store_true',  dest='save_temps',   default=False,           help='Save build files to check include paths')
    parser.add_option('--threads',    type='int',           dest='threads',      default=get_cores(),     help='Build threads to use')
    parser.add_option('--download-dir',                     dest='download_dir', default='/tmp/tarballs', help='Where to archive source files')
    parser.add_option('--build-root',                       dest='build_root',   default=None,            help='Root of the build and install')
    parser.add_option('--resume',     action='store_true',  dest='resume',       default=False,           help='Reuse in-progress build/install dirs')

    global opt
    (opt, args) = parser.parse_args()

    info('Using %d build processes' % opt.threads)

    if opt.ccache and opt.save_temps:
        die('--ccache and --save-temps conflict. Disabling ccache.')

    if opt.resume:
        opt.build_root = grablink('last-run')

    if opt.build_root is None or not P.exists(opt.build_root):
        opt.build_root = mkdtemp(prefix='BinaryBuilder')

    # Things misbehave if the buildroot is symlinks in it
    opt.build_root = P.realpath(opt.build_root)

    # -Wl,-z,now ?
    e = Environment(
                    CC       = 'gcc',
                    CXX      = 'g++',
                    CPP      = 'cpp',
                    F77      = 'gfortran',
                    CFLAGS   = '-O3 -g',
                    CXXFLAGS = '-O3 -g',
                    LDFLAGS  = r'-Wl,-rpath,/%s' % ('a'*100),
                    MAKEOPTS='-j%s' % opt.threads,
                    DOWNLOAD_DIR = opt.download_dir,
                    BUILD_DIR    = P.join(opt.build_root, 'build'),
                    INSTALL_DIR  = P.join(opt.build_root, 'install'),
                    MISC_DIR = P.join(opt.build_root, 'misc'),
                    PATH=os.environ['PATH'] )

    arch = get_platform()

    if arch.os == 'linux':
        e.append('LDFLAGS', '-Wl,-O1 -Wl,--enable-new-dtags -Wl,--hash-style=both')
        e.append_many(ALL_FLAGS, '-m%i' % arch.bits)

    elif arch.os == 'osx':
        e.append('LDFLAGS', '-Wl,-headerpad_max_install_names')

        # Force 64bit builds. Use 10.6 SDK for 10.6 and 10.7 for
        # everything else. Not really sure if this works for 10.8.
        osx_arch = 'x86_64' #SEMICOLON-DELIMITED
        target = '10.6'

        if version.StrictVersion(arch.dist_version) >= "10.7":
            print("Forcing use of non-LLVM compiler for Darwin 10.7+ systems\n")
            e['CC'] = "gcc-4.2"
            e['CXX'] = "g++-4.2"
            e['CPP'] = "cpp-4.2"
            target = '10.7'

        # And also using the matching sdk for good measure
        sysroot = '/Developer/SDKs/MacOSX%s.sdk' % target

        # CMake needs these vars to not screw things up.
        e.append('OSX_SYSROOT', sysroot)
        e.append('OSX_ARCH', osx_arch)
        e.append('OSX_TARGET', target)

        e.append_many(ALL_FLAGS, ' '.join(['-arch ' + i for i in osx_arch.split(';')]))
        e.append_many(ALL_FLAGS, '-mmacosx-version-min=%s -isysroot %s' % (target, sysroot))
        e.append_many(ALL_FLAGS, '-m64')

        # # Resolve a bug with -mmacosx-version-min on 10.6 (see
        # # http://markmail.org/message/45nbrtxsxvsjedpn).
        # # Short version: 10.6 generates the new compact header (LD_DYLD_INFO)
        # # even when told to support 10.5 (which can't read it)
        # if version.StrictVersion(arch.dist_version) >= '10.6':
        #     e.append('LDFLAGS', '-Wl,-no_compact_linkedit')

    # if arch.osbits == 'linux32':
    #     limit_symbols = P.join(P.abspath(P.dirname(__file__)), 'glibc24.h')
    #     e.append('CPPFLAGS', '-include %s' % limit_symbols)

    compiler_dir = P.join(e['MISC_DIR'], 'mycompilers')
    if not P.exists(compiler_dir):
        os.makedirs(compiler_dir)
    acceptable_fortran_compilers = ['gfortran','g77']
    for i in range(0,10):
        acceptable_fortran_compilers.append("gfortran-mp-4.%s" % i)
    for compiler in acceptable_fortran_compilers:
        try:
            gfortran_path = findfile(compiler, e['PATH'])
            print("Found fortran at: %s" % gfortran_path)
            subprocess.check_call(['ln', '-sf', gfortran_path, P.join(compiler_dir, 'gfortran')])
            break
        except Exception:
            pass
    e['F77'] = P.join(compiler_dir, 'gfortran')
    if opt.ccache:
        new = dict(
            CC  = P.join(compiler_dir, e['CC']),
            CXX = P.join(compiler_dir, e['CXX']),
            CCACHE_DIR = P.join(opt.download_dir, 'ccache-dir'),
            CCACHE_BASEDIR = gettempdir(),
        )

        ccache_path = findfile('ccache', e['PATH'])
        subprocess.check_call(['ln', '-sf', ccache_path, new['CC']])
        subprocess.check_call(['ln', '-sf', ccache_path, new['CXX']])
        e.update(new)

    print("%s" % e['PATH'])

    if opt.save_temps:
        e.append_many(CC_FLAGS, '-save-temps')
    else:
        e.append_many(CC_FLAGS, '-pipe')

    if opt.libtoolize is not None:
        e['LIBTOOLIZE'] = opt.libtoolize

    if len(args) == 0:
        # Verify that the user has some common executables that we
        # use. We don't apply this all the time for the sake of our
        # CI.
        common_exec = ["cmake", "make", "tar", "ln", "autoreconf", "cp", "sed", "bzip2", "unzip", "patch", "gcc", "csh", "git"]
        if arch.os == 'linux':
            common_exec.extend( ["libtool", "chrpath", "gfortran"] )
        else:
            common_exec.extend( ["glibtool", "install_name_tool"] )
        for program in common_exec:
            verify( program )

        build = []
        if arch.os == 'linux':
            build.append(lapack)
        build.extend([gsl, geos, curl, xercesc, cspice, protobuf, zlib, png, jpeg, tiff,
                      superlu, gmm, proj, gdal, ilmbase, openexr, boost, osg, flann,
                      qt, qwt, ufconfig, amd, colamd, cholmod, tnt, jama, laszip, liblas, isis])

        print("build type: %s" % type(build) )

        if not opt.dev:
            build.extend([visionworkbench, stereopipeline])
    else:
        build = [globals()[pkg] for pkg in args]

    if opt.pretend:
        info('I want to build:\n%s' % ' '.join(map(lambda x: x.__name__, build)))
        summary(e)
        sys.exit(0)

    makelink(opt.build_root, 'last-run')

    if opt.base:
        print('Untarring base system')
    for base in opt.base:
        run('tar', 'xf', base, '-C', e['INSTALL_DIR'], '--strip-components', '1')
    if opt.base:
        info("Fixing Paths in Libtool files.")
        new_libdir = e['INSTALL_DIR']
        for file in glob(P.join(e['INSTALL_DIR'],'lib','*.la')):
            lines = []
            logger.debug("Fixing libtool: %s" % file )
            with open(file,'r') as f:
                lines = f.readlines()
            old_libdir = P.normpath(P.join(lines[-1][lines[-1].find("'")+1:lines[-1].rfind("'")],'..'))
            with open(file,'w') as f:
                for line in lines:
                    f.write( string.replace(line,old_libdir,new_libdir) )

        info("Fixing binary paths and libraries")
        library_ext = "so"
        if arch.os == 'osx':
            library_ext = "dylib"
        SEARCHPATH = [P.join(e['INSTALL_DIR'],'lib')]
        for curr_path in SEARCHPATH:
            for library in glob(P.join(curr_path,'*.'+library_ext+'*')):
                if not is_binary(library):
                    continue
                logger.debug('  %s' % P.basename(library))
                try:
                    set_rpath(library, e['INSTALL_DIR'], map(lambda path: P.relpath(path, e['INSTALL_DIR']), SEARCHPATH))
                except:
                    warn('  Failed rpath on %s' % P.basename(library))
        for binary in glob(P.join(e['INSTALL_DIR'],'bin','*')):
            if not is_binary(binary):
                continue
            logger.debug('  %s' % P.basename(binary))
            try:
                set_rpath(binary, e['INSTALL_DIR'], map(lambda path: P.relpath(path, e['INSTALL_DIR']), SEARCHPATH))
            except:
                    warn('  Failed rpath on %s' % P.basename(binary))

    modes = dict(
        all     = lambda pkg : Package.build(pkg, skip_fetch=False),
        fetch   = lambda pkg : pkg.fetch(),
        nofetch = lambda pkg : Package.build(pkg, skip_fetch=True))

    try:
        for pkg in build:
            modes[opt.mode](pkg(e.copy_set_default()))

    except PackageError, e:
        die(e)

    makelink(opt.build_root, 'last-completed-run')

    info('\n\nAll done!')
    summary(e)
