#!/usr/bin/env python

from __future__ import print_function

from BinaryDist import grep, DistManager, Prefix, run

import time
import os.path as P
import logging
from optparse import OptionParser
from BinaryBuilder import get_platform, die
import sys
from glob import glob

# These are the SONAMES for libs we're allowed to get from the base system
# (most of these are frameworks, and therefore lack a dylib/so)
LIB_SYSTEM_LIST = '''
    AGL.framework/Versions/A/AGL
    Accelerate.framework/Versions/A/Accelerate
    ApplicationServices.framework/Versions/A/ApplicationServices
    Carbon.framework/Versions/A/Carbon
    Cocoa.framework/Versions/A/Cocoa
    CoreFoundation.framework/Versions/A/CoreFoundation
    CoreServices.framework/Versions/A/CoreServices
    GLUT.framework/Versions/A/GLUT
    OpenGL.framework/Versions/A/OpenGL
    QuickTime.framework/Versions/A/QuickTime
    vecLib.framework/Versions/A/vecLib

    libobjc.A.dylib
    libSystem.B.dylib
    libmathCommon.A.dylib

    libGL.so.1
    libGLU.so.1
    libICE.so.6
    libSM.so.6
    libX11.so.6
    libXext.so.6
    libXi.so.6
    libXmu.so.6
    libXrandr.so.2
    libXt.so.6
    libc.so.6
    libdl.so.2
    libglut.so.3
    libm.so.6
    libpthread.so.0
    librt.so.1
'''.split()

# prefixes of libs that we always ship (on linux, anyway)
if get_platform().os == 'linux':
    LIB_SHIP_PREFIX = ''' libstdc++.  libgcc_s. libgfortran. '''.split()
else:
    LIB_SHIP_PREFIX = ''' libgfortran. libgcc_s. '''.split()
    LIB_SYSTEM_LIST.extend(['libstdc++.6.dylib'])

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
    # Check if this is versioning the ISIS3.3.0 way
    if P.isfile(P.join(isisroot,'version')):
        f = open(P.join(isisroot,'version'),'r')
        version = f.readline().strip().split('.')
        return ".".join(version[0:3])
    header = P.join(isisroot, 'src/base/objs/Constants/Constants.h')
    m = grep('version\("(.*?)"', header)
    if not m:
        raise Exception('Unable to locate ISIS version header (expected at %s). Perhaps your ISISROOT (%s) is incorrect?' % (header, isisroot))
    return m[0].group(1)

if __name__ == '__main__':
    parser = OptionParser(usage='%s installdir' % sys.argv[0])
    parser.add_option('--debug',       dest='loglevel',  default=logging.INFO, action='store_const', const=logging.DEBUG, help='Turn on debug messages')
    parser.add_option('--include',     dest='include',   default='./whitelist', help='A file that lists the binaries for the dist')
    parser.add_option('--keep-temp',   dest='keeptemp',  default=False, action='store_true', help='Keep tmp distdir around for debugging')
    parser.add_option('--set-version', dest='version',   default=None, help='Set the version number to use for the generated tarball')
    parser.add_option('--set-name',    dest='name',      default='StereoPipeline', help='Tarball name for this dist')
    parser.add_option('--isisroot',    dest='isisroot',  default=None, help='Use a locally-installed isis at this root')

    global opt
    (opt, args) = parser.parse_args()

    def usage(msg, code=-1):
        parser.print_help()
        print('\n%s' % msg)
        sys.exit(code)

    if not args:
        usage('Missing required argument: installdir')
    installdir = P.realpath(args[0])
    if not (P.exists(installdir) and P.isdir(installdir)):
        usage('Invalid installdir %s (not a directory)' % installdir)
    if opt.isisroot is not None and not P.isdir(opt.isisroot):
        parser.print_help()
        die('\nIllegal argument to --isisroot: path does not exist')

    logging.basicConfig(level=opt.loglevel)

    mgr = DistManager(tarball_name())

    try:
        INSTALLDIR = Prefix(installdir)
        ISISROOT   = P.join(INSTALLDIR)
        SEARCHPATH = [INSTALLDIR.lib()]
        if opt.isisroot is not None:
            ISISROOT = opt.isisroot

        if opt.include == 'all':
            mgr.add_directory(INSTALLDIR, hardlink=True)
            mgr.make_tarball()
            sys.exit(0)
        else:
            print('Adding requested files')
            sys.stdout.flush()
            with file(opt.include, 'r') as f:
                for line in f:
                    mgr.add_glob(line.strip(), INSTALLDIR)

        print('Adding Libraries referred to by ISIS Plugins')
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
            mgr.add_glob( library, INSTALLDIR )

        print('Adding ISIS version check')
        sys.stdout.flush()
        with mgr.create_file('libexec/constants.sh') as f:
            print('BAKED_ISIS_VERSION="%s"' % isis_version(ISISROOT), file=f)

        print('Adding libraries')

        print('\tAdding forced-ship libraries')
        print('Dependencies %s' % mgr.deplist.keys())
        # Handle the shiplist separately
        for copy_lib in LIB_SHIP_PREFIX:
            found = None
            for soname in mgr.deplist.keys():
                if soname.startswith(copy_lib):
                    found = soname
                    break
            if found:
                mgr.add_library(mgr.deplist[found])
                mgr.remove_deps([found])

        print('\tRemoving system libs')
        mgr.remove_deps(LIB_SYSTEM_LIST)

        print('\tFinding deps in search path')
        mgr.resolve_deps(nocopy = [P.join(ISISROOT, 'lib'), P.join(ISISROOT, '3rdParty', 'lib')],
                           copy = [INSTALLDIR.lib()])
        if mgr.deplist:
            raise Exception('Failed to find some libs in any of our dirs:\n\t%s' % '\n\t'.join(mgr.deplist.keys()))

        print('Adding files in dist-add and docs')
        #XXX Don't depend on cwd
        for dir in 'dist-add', INSTALLDIR.doc():
            if P.exists(dir):
                mgr.add_directory(dir)

        print('Baking RPATH and stripping binaries')
        mgr.bake(map(lambda path: P.relpath(path, INSTALLDIR), SEARCHPATH))

        debuglist = mgr.find_filter('-name', '*.debug')

        mgr.make_tarball(exclude = [debuglist.name])
        if P.getsize(debuglist.name) > 0:
            mgr.make_tarball(include = debuglist.name, name = '%s-debug.tar.gz' % mgr.tarname)
    finally:
        if not opt.keeptemp:
            mgr.remove_tempdir()
