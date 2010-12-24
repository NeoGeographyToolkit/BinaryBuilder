#!/usr/bin/env python

from __future__ import print_function

from BinaryDist import grep, DistManager, Prefix

import time
import os.path as P
import logging
from optparse import OptionParser
from BinaryBuilder import get_platform, run
from sys import exit

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
        return '%s-%s-%s-%s' % (opt.name, opt.version, arch.machine, arch.prettyos)
    else:
        return '%s-%s-%s-%s' % (opt.name, arch.machine, arch.prettyos, time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime()))

def sibling_to(dir, name):
    ''' get a pathname for a directory 'name' which is a sibling of directory 'dir' '''
    return P.join(P.dirname(dir), P.basename(name))

# Keep this in sync with the function in libexec-funcs.sh
def isis_version(isisroot):
    header = P.join(isisroot, 'src/base/objs/Constants/Constants.h')
    m = grep('version\("(.*?)"', header)
    if not m:
        raise Exception('Unable to locate ISIS version header (expected at %s). Perhaps your ISISROOT ($s) is incorrect?' % (header, isisroot))
    return m[0].group(1)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('--base',        dest='base',      default=[], action='append', help='Provide a tarball to use as a base system')
    parser.add_option('--debug',       dest='loglevel',  default=logging.INFO, action='store_const', const=logging.DEBUG, help='Turn on debug messages')
    parser.add_option('--include',     dest='include',   default='./whitelist', help='A file that lists the binaries for the dist')
    parser.add_option('--prefix',      dest='prefix',    default='/tmp/build/base/install', help='Root of the installed files')
    parser.add_option('--set-version', dest='version',   default=None, help='Set the version number to use for the generated tarball')
    parser.add_option('--set-name',    dest='name',      default='StereoPipeline', help='Tarball name for this dist')

    global opt
    (opt, args) = parser.parse_args()

    logging.basicConfig(level=opt.loglevel)

    mgr = DistManager(tarball_name())
    INSTALLDIR = Prefix(opt.prefix)
    ISISROOT   = sibling_to(INSTALLDIR, 'isis')
    SEARCHPATH = [P.join(ISISROOT, 'lib'), P.join(ISISROOT, '3rdParty', 'lib'), INSTALLDIR.lib()]

    if opt.base:
        print('Untarring base system')

    for base in opt.base:
        run('tar', 'xf', base, '-C', mgr.distdir, '--strip-components', '1')
    baselist = mgr.find_filter('-type', 'f')

    if opt.include == 'all':
        mgr.add_directory(INSTALLDIR, hardlink=True)
        mgr.make_tarball(exclude = baselist.name)
        exit(0)
    else:
        print('Adding requested files')
        with file(opt.include, 'r') as f:
            for line in f:
                mgr.add_glob(line.strip(), INSTALLDIR)

    print('Adding ISIS version check')
    with mgr.create_file('libexec/constants.sh') as f:
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

    print('Adding files in dist-add and docs')
    #XXX Don't depend on cwd
    for dir in 'dist-add', INSTALLDIR.doc():
        if P.exists(dir):
            mgr.add_directory(dir)

    print('Baking RPATH and stripping binaries')
    mgr.bake(map(lambda path: P.relpath(path, INSTALLDIR), SEARCHPATH))

    debuglist = mgr.find_filter('-name', '*.debug')

    mgr.make_tarball(exclude = [debuglist.name, baselist.name])
    if P.getsize(debuglist.name) > 0:
        mgr.make_tarball(include = debuglist.name, exclude = baselist.name, name = '%s-debug.tar.gz' % mgr.tarname)
