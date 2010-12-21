#!/usr/bin/env python

from __future__ import print_function

from BinaryDist import grep, DistManager, Prefix, run, set_rpath, strip, is_binary

import time
import os.path as P
import logging
from optparse import OptionParser
from glob import glob
from BinaryBuilder import get_platform
from tempfile import NamedTemporaryFile

# These are the SONAMES for libs we're allowed to get from the base system
# (most of these are frameworks, and therefore lack a dylib/so)
LIB_SYSTEM_LIST = '''
    AGL
    Accelerate
    AppKit
    ApplicationServices
    Carbon
    Cocoa
    CoreFoundation
    CoreServices
    GLUT
    OpenGL
    QuickTime
    vecLib

    libobjc.A.dylib
    libSystem.B.dylib

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

# prefixes of libs that we always ship
LIB_SHIP_PREFIX = '''
    libstdc++.
    libgcc_s.
'''.split()

def tarball_name():
    arch = get_platform()
    if opt.version is not None:
        return 'StereoPipeline-%s-%s-%s' % (opt.version, arch.machine, arch.prettyos)
    else:
        return 'StereoPipeline-%s-%s-%s' % (arch.machine, arch.prettyos, time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime()))

# Keep this in sync with the function in libexec-funcs.sh
def isis_version(isisroot):
    header = P.join(isisroot, 'src/base/objs/Constants/Constants.h')
    m = grep('version\("(.*?)"', header)
    if not m:
        raise Exception('Unable to locate ISIS version header (expected at %s). Perhaps your ISISROOT ($s) is incorrect?' % (header, isisroot))
    return m[0].group(1)

def bake(filename, toplevel, searchpath):
    set_rpath(filename, toplevel, searchpath)
    strip(filename)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('--set-version', dest='version',   default=None, help='Set the version number to use for the generated tarball')
    parser.add_option('--prefix',      dest='prefix',    default='/tmp/build/base/install', help='Root of the installed files')
    parser.add_option('--include',     dest='include',   default='./whitelist', help='A file that lists the binaries for the dist')
    parser.add_option('--debug',       dest='loglevel',  default=logging.INFO, action='store_const', const=logging.DEBUG, help='Turn on debug messages')

    global opt
    (opt, args) = parser.parse_args()

    logging.basicConfig(level=opt.loglevel)


    BUILDNAME  = tarball_name()
    mgr = DistManager(BUILDNAME)
    INSTALLDIR = Prefix(opt.prefix)
    DISTDIR    = mgr.distdir
    ISISROOT   = P.join(P.dirname(INSTALLDIR.base()), 'isis') # sibling to INSTALLDIR
    SEARCHPATH = [P.join(ISISROOT, 'lib'), P.join(ISISROOT, '3rdParty', 'lib'), INSTALLDIR.lib()]

    print('Adding requested files')
    with file(opt.include, 'r') as f:
        for line in f:
            relglob = line.strip()
            inpaths = glob(INSTALLDIR.base(relglob))
            assert len(inpaths) > 0, 'No matches for include list entry %s' % relglob
            for inpath in inpaths:
                mgr.add_smart(inpath, INSTALLDIR)

    print('Adding ISIS version check')
    with file(mgr.distdir.libexec('constants.sh'), 'w') as f:
        print('BAKED_ISIS_VERSION="%s"' % isis_version(ISISROOT), file=f)

    print('Adding libraries')

    print('\tAdding forced-ship libraries')
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

    #XXX Don't depend on cwd
    print('Adding files in dist-add')
    if P.exists('dist-add'): #XXX Don't depend on cwd
        mgr.add_directory('dist-add')

    print('Adding docs')
    if P.exists(INSTALLDIR.doc()):
        mgr.add_directory(INSTALLDIR.doc())

    print('Baking RPATH and stripping binaries')
    for path in mgr.distlist:
        if not is_binary(path): continue
        bake(path, DISTDIR, SEARCHPATH)

    mgr.clean_dist()

    DIST_PARENT = P.dirname(DISTDIR)

    debuglist = NamedTemporaryFile()

    run('find', BUILDNAME, '-name', '*.debug', '-fprint', debuglist.name, cwd=DIST_PARENT)

    print('Creating tarball %s.tar.gz' % BUILDNAME)
    run('tar', 'czf', '%s.tar.gz' % BUILDNAME, '-X', debuglist.name, '-C', DIST_PARENT, BUILDNAME)

    if P.getsize(debuglist.name) > 0:
        print('Creating debug tarball %s-debug.tar.gz' % BUILDNAME)
        run('tar', 'czf', '%s-debug.tar.gz' % BUILDNAME, '-T', debuglist.name, '-C', DIST_PARENT, BUILDNAME, '--no-recursion')
