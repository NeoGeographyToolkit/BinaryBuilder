#!/usr/bin/env python

from __future__ import print_function
import os, shutil
import os.path as P
import re, sys
from glob import glob
import subprocess
from BinaryBuilder import CMakePackage, GITPackage, Package, stage, warn, PackageError, HelperError, SVNPackage, Apps

def strip_flag(flag, key, env):
    ret = []
    hit = None
    if not key in env:
        return
    for test in env[key].split():
        m = re.search(flag, test)
        if m:
            hit = m
        else:
            ret.append(test)
    if ret:
        env[key] = ' '.join(ret).strip()
    else:
        del env[key]
    return hit, env

class ccache(Package):
    src     = 'http://samba.org/ftp/ccache/ccache-3.1.9.tar.bz2'
    chksum  = 'e80a5cb7301e72f675097246d722505ae56e3cd3'

class cmake(Package):
    src     = 'http://www.cmake.org/files/v2.8/cmake-2.8.11.2.tar.gz'
    chksum  = '31f217c9305add433e77eff49a6eac0047b9e929'

class chrpath(Package):
    src     = 'http://ftp.debian.org/debian/pool/main/c/chrpath/chrpath_0.13.orig.tar.gz'
    chksum  = '11ff3e3dda2acaf1e529475f394f74f2ef7a8204'

class parallel(Package):
    src     = 'http://ftp.gnu.org/gnu/parallel/parallel-20130722.tar.bz2'
    chksum  = 'd794ac9c2c0a73d430b9ae2ebbbd07e4eb2fcaf0'

    @stage
    def install(self):
        super(parallel, self).install()
        # Copy parallel to libexec, as we want it to be hidden there in
        # the released ASP distribution.
        libexec = P.join( self.env['INSTALL_DIR'], 'libexec' )
        self.helper('mkdir', '-p', libexec)
        cmd = ['cp', '-vf', P.join( self.env['INSTALL_DIR'], 'bin', 'parallel' ),
               libexec]
        self.helper(*cmd)

class tnt(Package):
    src     = 'http://math.nist.gov/tnt/tnt_126.zip'
    chksum  = '32f628d7e28a6e373ec2ff66c70c1cb25783b946'

    def __init__(self, env):
        super(tnt, self).__init__(env)
        # Our source doesn't unpack into a directory. So our work
        # directory is just the outer containing folder.
        self.workdir = P.join(self.env['BUILD_DIR'], self.pkgname)
    def configure(self): pass
    def compile(self): pass

    @stage
    def install(self):
        d = P.join('%(INSTALL_DIR)s' % self.env, 'include', 'tnt')
        self.helper('mkdir', '-p', d)
        cmd = ['cp', '-vf'] + glob(P.join(self.workdir, '*.h')) + [d]
        self.helper(*cmd)

class jama(Package):
    src     = 'http://math.nist.gov/tnt/jama125.zip'
    chksum  = '5ca8b154d0a0c30e2c50700ffe70567315ebcf2c'

    def __init__(self, env):
        super(jama, self).__init__(env)
        self.workdir = P.join(self.env['BUILD_DIR'], self.pkgname)
    def configure(self): pass
    def compile(self): pass

    @stage
    def install(self):
        d = P.join('%(INSTALL_DIR)s' % self.env, 'include', 'jama')
        self.helper('mkdir', '-p', d)
        cmd = ['cp', '-vf'] + glob(P.join(self.workdir, '*.h')) + [d]
        self.helper(*cmd)

class openjpeg2(CMakePackage):
    src     = 'http://openjpeg.googlecode.com/files/openjpeg-2.0.0.tar.gz'
    chksum  = '0af78ab2283b43421458f80373422d8029a9f7a7'

    @stage
    def configure(self):
        super(openjpeg2, self).configure(other=['-DBUILD_SHARED_LIBS=ON'])

class gdal(Package):
    src     = 'http://download.osgeo.org/gdal/1.10.0/gdal-1.10.0.tar.gz'
    chksum  = 'e522b95056905e4c41047fdb42c0ca172ef3ad25'
    patches = 'patches/gdal'

    @stage
    def configure(self):
        # Parts of GDAL will attempt to load libproj manual (something
        # we can't see or correct in the elf tables). This sed should
        # correct that problem.
        self.helper('sed', '-ibak', '-e', 's/libproj./libproj.0./g', 'ogr/ogrct.cpp')

        w = ['threads', 'libtiff', 'geotiff=internal', 'jpeg', 'png', 'zlib', 'pam','openjpeg=' + self.env['INSTALL_DIR']]
        wo = \
            '''bsb cfitsio curl dods-root dwg-plt dwgdirect ecw epsilon expat expat-inc expat-lib fme
             geos gif grass hdf4 hdf5 idb ingres jasper jp2mrsid kakadu libgrass
             macosx-framework mrsid msg mysql netcdf oci oci-include oci-lib odbc ogdi pcidsk
             pcraster perl pg php pymoddir python ruby sde sde-version spatialite sqlite3
             static-proj4 xerces xerces-inc xerces-lib libiconv-prefix libiconv xml2 pcre freexl'''.split()

        self.helper('./autogen.sh')
        super(gdal,self).configure(with_=w, without=wo, disable='static', enable='shared')

    @stage
    def install(self):
        super(gdal, self).install()
        # Copy gdal_translate to libexec, as we want it to be hidden there in
        # the released ASP distribution.
        libexec = P.join( self.env['INSTALL_DIR'], 'libexec' )
        self.helper('mkdir', '-p', libexec)
        cmd = ['cp', '-vf', P.join( self.env['INSTALL_DIR'], 'bin', 'gdal_translate' ),
               libexec]
        self.helper(*cmd)

class ilmbase(Package):
    src     = 'http://download.savannah.nongnu.org/releases/openexr/ilmbase-1.0.2.tar.gz'
    chksum  = 'fe6a910a90cde80137153e25e175e2b211beda36'
    patches = 'patches/ilmbase'

    @stage
    def configure(self):
        self.env['AUTOHEADER'] = 'true'
        # XCode in snow leopard removed this flag entirely (way to go, guys)
        self.helper('sed', '-ibak', '-e', 's/-Wno-long-double//g', 'configure.ac')
        self.helper('autoupdate', 'configure.ac')
        self.helper('autoreconf', '-fvi')
        super(ilmbase, self).configure(disable='static')

class openexr(Package):
    src     = 'http://download.savannah.nongnu.org/releases/openexr/openexr-1.7.0.tar.gz'
    chksum  = '91d0d4e69f06de956ec7e0710fc58ec0d4c4dc2b'
    patches = 'patches/openexr'

    @stage
    def configure(self):
        self.env['AUTOHEADER'] = 'true'
        # XCode in snow leopard removed this flag entirely (way to go, guys)
        self.helper('sed', '-ibak', '-e', 's/-Wno-long-double//g', 'configure.ac')
        self.helper('autoupdate', 'configure.ac')
        self.helper('autoreconf', '-fvi')
        super(openexr,self).configure(with_=('ilmbase-prefix=%(INSTALL_DIR)s' % self.env),
                                      disable=('ilmbasetest', 'imfexamples', 'static'))

class proj(Package):
    src     = 'http://download.osgeo.org/proj/proj-4.8.0.tar.gz'
    chksum  = '5c8d6769a791c390c873fef92134bf20bb20e82a'

    @stage
    def configure(self):
        super(proj,self).configure(disable='static', without='jni')

class curl(Package):
    src     = 'http://curl.haxx.se/download/curl-7.31.0.tar.bz2'
    chksum  = '9333b1fc63ded189b6014afe7bb415fa1f22ae10'

    @stage
    def configure(self):
        w = ['zlib=%(INSTALL_DIR)s' % self.env]
        wo = 'ssl libidn'.split()
        super(curl,self).configure(
            with_=w, without=wo, disable=['static','ldap','ldaps'])

class laszip(CMakePackage):
    src     = 'http://download.osgeo.org/laszip/laszip-2.1.0.tar.gz'
    chksum  = 'bbda26b8a760970ff3da3cfac97603dd0ec4f05f'

class liblas(CMakePackage):
    src     = 'http://download.osgeo.org/liblas/libLAS-1.7.0.tar.gz'
    chksum  = 'f31070efdf7bb7d6675c23c6c6c84584e3a10869'

    @stage
    def configure(self):
        # Remove the pedantic flag. Latest boost is not compliant.
        self.helper('sed', '-ibak', '-e', 's/-pedantic//g', 'CMakeLists.txt')

        self.env['LDFLAGS'] += ' -Wl,-rpath -Wl,%(INSTALL_DIR)s/lib' % self.env

        super(liblas, self).configure(other=[
            '-DBoost_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include','boost-'+boost.version),
            '-DBoost_LIBRARY_DIRS=' + P.join(self.env['INSTALL_DIR'],'lib'),
            '-DWITH_LASZIP=true',
            '-DLASZIP_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include')])

class geoid(CMakePackage):

    # Warning: Must keep this version synchronized with dem_geoid.cc!
    version = "1.1"; # Used in deploy_base.py

    src     = 'https://byss.arc.nasa.gov/asp_packages/geoids-' + version + '.tar.gz'
    chksum  = '49a21acc5f821a7fad916bce68d1f12f58007927'

    @stage
    def configure(self): pass

    @stage
    def compile(self): pass

    @stage
    def install(self):
        # Copy the geoids
        d = P.join('%(INSTALL_DIR)s' % self.env, 'share')
        cmd = ['cp', '-rvf'] + [self.workdir] + [d]
        self.helper(*cmd)

# Due to legal reasons ... we are not going to download a modified
# version of ISIS from some NASA Ames server. Instead, we will
# download ISIS and then download the repo for editing ISIS. We apply
# the patch locally and then build away.
class isis(Package):
    patches = 'patches/isis/0001-fix_int.patch'
    def __init__(self, env):
        super(isis, self).__init__(env)
        self.isis_localcopy = P.join(env['DOWNLOAD_DIR'], 'rsync', self.pkgname)
        self.isisautotools_localcopy = P.join(env['DOWNLOAD_DIR'], 'git', 'AutotoolsForISIS')
        # We download the source code from the OSX branch, should be same code
        # as on the Linux side.
        self.isis_src = "isisdist.astrogeology.usgs.gov::x86-64_darwin_OSX10.8/isis/"
        self.isisautotools_src = "http://github.com/NeoGeographyToolkit/AutotoolsForISIS.git"

    @stage
    def fetch(self, skip=False):
        if not P.exists(self.isis_localcopy) or \
                not P.exists(self.isisautotools_localcopy):
            if skip: raise PackageError(self, 'Fetch is skipped and no src available')
            os.makedirs(self.isis_localcopy)
        if skip: return

        self.copytree(self.isis_src, self.isis_localcopy + '/', ['-zv', '--exclude', 'doc/*', '--exclude', '*/doc/*', '--exclude', 'bin/*', '--exclude', '3rdParty/*', '--exclude', 'lib/*'])
        if not P.exists(self.isisautotools_localcopy):
            self.helper('git', 'clone', '--mirror', self.isisautotools_src, self.isisautotools_localcopy)
        else:
            self.helper('git', '--git-dir', self.isisautotools_localcopy, 'fetch', 'origin')

    @stage
    def unpack(self):
        output_dir = P.join(self.env['BUILD_DIR'], self.pkgname)
        self.remove_build(output_dir)
        self.workdir = output_dir
        if P.exists(P.join(self.workdir, self.pkgname)):
            self.helper('rm','-rf',self.pkgname);
        if not P.exists(P.join(output_dir, 'isis_original')):
            os.makedirs(P.join(output_dir, 'isis_original'))
        self.copytree(self.isis_localcopy + '/', P.join(output_dir, 'isis_original'),
                      ['--link-dest=%s' % self.isis_localcopy])
        os.mkdir( P.join(output_dir, 'AutotoolsForISIS-git') )
        self.helper('git', 'clone', self.isisautotools_localcopy,
                    P.join(output_dir, 'AutotoolsForISIS-git'))

        # Now we actually run commands that patch ISIS with a build system
        self.helper(sys.executable,"AutotoolsForISIS-git/reformat_isis.py","--destination",
                    self.pkgname,"--isisroot","isis_original")
        self.workdir = P.join(output_dir,self.pkgname)

        self._apply_patches()

    @stage
    def configure(self):
        self.helper('./autogen')

        pkgs = 'arbitrary_qt qwt boost protobuf tnt jama xercesc spice geos gsl \
                lapack superlu gmm tiff z jpeg ufconfig amd colamd cholmod curl xercesc'.split()

        w = [i + '=%(INSTALL_DIR)s' % self.env for i in pkgs]
        includedir = P.join(self.env['INSTALL_DIR'], 'include')

        with file(P.join(self.workdir, 'config.options'), 'w') as config:
            for pkg in pkgs:
                ldflags = []
                ldflags.append('-L%s' % P.join(self.env['INSTALL_DIR'], 'lib'))
                if self.arch.os == 'osx':
                    ldflags.append('-F%s' % P.join(self.env['INSTALL_DIR'], 'lib'))
                print('PKG_%s_LDFLAGS="%s"' % (pkg.upper(), ' '.join(ldflags)), file=config)

            qt_pkgs = 'QtCore QtGui QtNetwork QtSql QtSvg QtXml QtXmlPatterns'
            print('QT_ARBITRARY_MODULES="%s"' % qt_pkgs, file=config)

            qt_cppflags=['-I%s' % includedir]
            qt_libs=['-L%s' % P.join(self.env['INSTALL_DIR'], 'lib')]

            for module in qt_pkgs.split():
                qt_cppflags.append('-I%s/%s' % (includedir, module))
                qt_libs.append('-l%s' % module)

            print('PKG_ARBITRARY_QT_CPPFLAGS="%s"' % ' '.join(qt_cppflags), file=config)
            print('PKG_ARBITRARY_QT_LIBS="%s"' %  ' '.join(qt_libs), file=config)
            print('PKG_ARBITRARY_QT_MORE_LIBS="-lpng -lz"', file=config)

            print('PROTOC=%s' % (P.join(self.env['INSTALL_DIR'], 'bin', 'protoc')), file=config)
            print('MOC=%s' % (P.join(self.env['INSTALL_DIR'], 'bin', 'moc')), file=config)
            print('HAVE_PKG_APPLE_QWT=no', file=config)
            print('HAVE_PKG_KAKADU=no', file=config)
            print('HAVE_PKG_GSL_HASBLAS=no', file=config)

        # Force the linker to do a thorough job at finding dependencies.
        # If older linkers don't like the provided flags, try again
        # without them.
        ldflag_attempts = []
        ldflag_attempts.append( self.env['LDFLAGS'] )
        if self.arch.os == 'linux':
            ld_flags1 = ' -Wl,--copy-dt-needed-entries  -Wl,--no-as-needed'
            ld_flags2 = ' -Wl,-rpath=%(INSTALL_DIR)s/lib -L%(INSTALL_DIR)s/lib -lblas -lQtXml' % self.env
            ldflag_attempts.append( ldflag_attempts[0] + ld_flags2 )
            ldflag_attempts.append( ldflag_attempts[0] + ld_flags1)
            ldflag_attempts.append( ldflag_attempts[0] )
            ldflag_attempts[0] = ldflag_attempts[0] + ld_flags1 + ld_flags2

        for ld_flags in ldflag_attempts:
            self.env['LDFLAGS'] = ld_flags
            try:
                super(isis, self).configure(
                    with_ = w,
                    without = ['clapack', 'slapack'],
                    disable = ['pkg_paths_default', 'static', 'qt-qmake'] )
                break
            except:
                print ("Unexpected error in attempt: ", ld_flags, sys.exc_info()[0])

class stereopipeline(GITPackage):
    # To do: Fix duplication in writing config.options.asp in deploy_base.py
    # and class stereopipeline in Packages.py.
    src     = 'http://github.com/NeoGeographyToolkit/StereoPipeline.git'
    def configure(self):
        self.helper('./autogen')

        disable_apps    = Apps.disable_apps
        enable_apps     = Apps.enable_apps
        disable_modules = 'controlnettk mpi'
        enable_modules  = 'core spiceio isisio sessions'
        install_pkgs    = Apps.vw_pkgs.split() + Apps.install_pkgs.split()
        w = [i + '=%(INSTALL_DIR)s'   % self.env for i in install_pkgs]

        includedir = P.join(self.env['INSTALL_DIR'], 'include')

        with file(P.join(self.workdir, 'config.options'), 'w') as config:
            for pkg in install_pkgs:
                ldflags=[]
                ldflags.append('-L%s' % (P.join(self.env['INSTALL_DIR'], 'lib')))

                if pkg == 'tiff':
                    ldflags.extend(['-ltiff','-ljpeg'])

                if self.arch.os == 'osx':
                    ldflags.append('-F%s' % (P.join(self.env['INSTALL_DIR'], 'lib')))

                if pkg == 'gdal' and self.arch.os == 'linux':
                    print('PKG_%s_LDFLAGS="-L%s -ltiff -ljpeg -lpng -lz -lopenjp2"'  % (pkg.upper(), P.join(self.env['INSTALL_DIR'], 'lib')), file=config)
                else:
                    print('PKG_%s_LDFLAGS="%s"' % (pkg.upper(), ' '.join(ldflags)), file=config)

            qt_pkgs = Apps.qt_pkgs

            print('QT_ARBITRARY_MODULES="%s"' % qt_pkgs, file=config)

            qt_cppflags=['-I%s' % includedir]
            qt_libs=['-L%s' % P.join(self.env['INSTALL_DIR'], 'lib')]

            for module in qt_pkgs.split():
                qt_cppflags.append('-I%s/%s' % (includedir, module))
                qt_libs.append('-l%s' % module)

            print('PKG_ARBITRARY_QT_CPPFLAGS="%s"' %  ' '.join(qt_cppflags), file=config)
            print('PKG_ARBITRARY_QT_LIBS="%s"' %  ' '.join(qt_libs), file=config)
            print('PKG_ARBITRARY_QT_MORE_LIBS="-lpng -lz"', file=config)

            print('PROTOC=%s' % (P.join(self.env['INSTALL_DIR'], 'bin', 'protoc')),file=config)
            print('MOC=%s' % (P.join(self.env['INSTALL_DIR'], 'bin', 'moc')),file=config)
            print('HAVE_PKG_APPLE_QWT=no', file=config)
            print('HAVE_PKG_KAKADU=no', file=config)
            print('HAVE_PKG_GSL_HASBLAS=no', file=config)

            print('PKG_EIGEN_CPPFLAGS="-I%s/eigen3"' % includedir, file=config)
            print('PKG_LIBPOINTMATCHER_CPPFLAGS="-I%s"' % includedir,
                  file=config)

        super(stereopipeline, self).configure(
            other   = ['docdir=%s/doc' % self.env['INSTALL_DIR']],
            with_   = w,
            without = ['clapack', 'slapack', 'tcmalloc'],
            disable = ['pkg_paths_default', 'static', 'qt-qmake']
            + ['app-' + a for a in disable_apps.split()]
            + ['module-' + a for a in disable_modules.split()],
            enable  = ['debug=ignore', 'optimize=ignore']
            + ['app-' + a for a in enable_apps.split()]
            + ['module-' + a for a in enable_modules.split()])

class visionworkbench(GITPackage):
    src     = 'http://github.com/visionworkbench/visionworkbench.git'

    def __init__(self,env):
        super(visionworkbench,self).__init__(env)

    @stage
    def configure(self):
        self.helper('./autogen')

        enable_modules  = 'camera mosaic interestpoint cartography hdr stereo geometry tools bundleadjustment'.split()
        disable_modules = 'gpu plate python gui'.split()
        install_pkgs = 'jpeg png gdal proj4 z ilmbase openexr boost flapack protobuf flann'.split()

        w  = [i + '=%(INSTALL_DIR)s' % self.env for i in install_pkgs]
        w.append('protobuf=%(INSTALL_DIR)s' % self.env)

        with file(P.join(self.workdir, 'config.options'), 'w') as config:
            for pkg in install_pkgs:
                print('PKG_%s_CPPFLAGS="-I%s -I%s"' % (pkg.upper(), P.join(self.env['NOINSTALL_DIR'],   'include'),
                                                       P.join(self.env['INSTALL_DIR'], 'include')), file=config)
                if pkg == 'gdal' and self.arch.os == 'linux':
                    print('PKG_%s_LDFLAGS="-L%s -ltiff -ljpeg -lpng -lz -lopenjp2"'  % (pkg.upper(), P.join(self.env['INSTALL_DIR'], 'lib')), file=config)
                else:
                    print('PKG_%s_LDFLAGS="-L%s"'  % (pkg.upper(), P.join(self.env['INSTALL_DIR'], 'lib')), file=config)
            # Specify executables we use
            print('PROTOC=%s' % (P.join(self.env['INSTALL_DIR'], 'bin', 'protoc')),file=config)
            print('MOC=%s' % (P.join(self.env['INSTALL_DIR'], 'bin', 'moc')),file=config)

        super(visionworkbench, self).configure(with_   = w,
                                               without = ('tiff hdf cairomm zeromq rabbitmq_c tcmalloc x11 clapack slapack qt opencv cg'.split()),
                                               disable = ['pkg_paths_default','static', 'qt-qmake'] + ['module-' + a for a in disable_modules],
                                               enable  = ['debug=ignore', 'optimize=ignore', 'as-needed', 'no-undefined'] + ['module-' + a for a in enable_modules])

class lapack(CMakePackage):
    src     = 'http://www.netlib.org/lapack/lapack-3.4.2.tgz'
    chksum  = '93a6e4e6639aaf00571d53a580ddc415416e868b'

    def configure(self):
        LDFLAGS_ORIG = self.env['LDFLAGS']
        LDFLAGS_CURR = []
        for i in self.env['LDFLAGS'].split(' '):
            if not i.startswith('-L'):
                LDFLAGS_CURR.append(i);
        self.env['LDFLAGS'] = ' '.join(LDFLAGS_CURR)
        super(lapack, self).configure( other=['-DBUILD_SHARED_LIBS=ON','-DBUILD_STATIC_LIBS=OFF','-DCMAKE_Fortran_FLAGS=-fPIC'] )
        self.env['LDFLAGS'] = LDFLAGS_ORIG

class boost(Package):
    version = '1_54' # variable is used in class liblas, libnabo, etc.
    src     = 'http://downloads.sourceforge.net/boost/boost_' + version + '_0.tar.bz2'
    chksum  = '230782c7219882d0fab5f1effbe86edb85238bf4'
    patches = 'patches/boost'

    def __init__(self, env):
        super(boost, self).__init__(env)
        self.env['NO_BZIP2'] = '1'
#        self.env['NO_ZLIB']  = '1'

    @stage
    def configure(self):
        with file(P.join(self.workdir, 'user-config.jam'), 'w') as f:
            if self.arch.os == 'linux':
                toolkit = 'gcc'
            elif self.arch.os == 'osx':
                toolkit = 'darwin'

            # print('variant myrelease : release : <optimization>none <debug-symbols>none ;', file=f)
            # print('variant mydebug : debug : <optimization>none ;', file=f)
            args = [toolkit] + list(self.env.get(i, ' ') for i in ('CXX', 'CXXFLAGS', 'LDFLAGS'))
            print('using %s : : %s : <cxxflags>"%s" <linkflags>"%s -ldl" ;' % tuple(args), file=f)
            print('using zlib : 1.2.8 : <include>%s <search>%s ;' %
                  (P.join(self.env['INSTALL_DIR'],'include'),P.join(self.env['INSTALL_DIR'],'lib')), file=f)
            print('option.set keep-going : false ;', file=f)

    # TODO: WRONG. There can be other things besides -j4 in MAKEOPTS
    @stage
    def compile(self):
        self.env['BOOST_ROOT'] = self.workdir

        self.helper('./bootstrap.sh')
        os.unlink(P.join(self.workdir, 'project-config.jam'))

        cmd = ['./bjam']
        if 'MAKEOPTS' in self.env:
            cmd += (self.env['MAKEOPTS'],)

        self.args = [
            '-q', '--user-config=%s/user-config.jam' % self.workdir,
            '--prefix=%(INSTALL_DIR)s' % self.env, '--layout=versioned',
            'threading=multi', 'variant=release', 'link=shared', 'runtime-link=shared',
            '--without-mpi', '--without-python', '--without-wave', '--without-log', 'stage',
            '-d+2' # Show commands as they are executed
            ]

        cmd += self.args
        self.helper(*cmd)

    # TODO: Might need some darwin path-munging with install_name_tool?
    @stage
    def install(self):
        self.env['BOOST_ROOT'] = self.workdir
        cmd = ['./bjam'] + self.args + ['install']
        self.helper(*cmd)

class HeaderPackage(Package):
    def configure(self, *args, **kw):
        kw['other'] = kw.get('other', []) + ['--prefix=%(NOINSTALL_DIR)s' % self.env,]
        super(HeaderPackage, self).configure(*args, **kw)

    @stage
    def compile(self): pass

    @stage
    def install(self):
        self.helper('make', 'install-data')

class gsl(Package):
    src = 'ftp://ftp.gnu.org/gnu/gsl/gsl-1.15.tar.gz',
    chksum = 'd914f84b39a5274b0a589d9b83a66f44cd17ca8e',

    def configure(self):
        super(gsl, self).configure(disable=('static'))

class geos(Package):
    src = 'http://download.osgeo.org/geos/geos-3.3.8.tar.bz2'
    chksum = '1743e09f37eb75d85283a684a5765c4f44d035fa'

    def configure(self):
        super(geos, self).configure(disable=('python', 'ruby', 'static'))

class superlu(Package):
    src    = ['http://sources.gentoo.org/cgi-bin/viewvc.cgi/gentoo-x86/sci-libs/superlu/files/superlu-4.3-autotools.patch','http://crd-legacy.lbl.gov/~xiaoye/SuperLU/superlu_4.3.tar.gz']
    chksum = ['c9cc1c9a7aceef81530c73eab7f599d652c1fddd','d2863610d8c545d250ffd020b8e74dc667d7cbdd']

    def __init__(self,env):
        super(superlu,self).__init__(env)
        self.patches = [P.join(env['DOWNLOAD_DIR'], 'superlu-4.3-autotools.patch'),
                        P.join(self.pkgdir,'patches','superlu','finish_autotools.patch')]

    @stage
    def configure(self):
        self.helper('mkdir', 'm4')
        self.helper('autoreconf', '-fvi')
        blas = ''
        if self.arch.os == "osx":
            blas = '"-framework vecLib"'
        else:
            blas = glob(P.join(self.env['INSTALL_DIR'],'lib','libblas.so*'))[0]
        super(superlu,self).configure(with_=('blas=%s') % blas,
                                      disable=('static'))

class gmm(Package):
    src     = 'http://download.gna.org/getfem/stable/gmm-4.2.tar.gz'
    chksum  = '3555d5a5abdd525fe6b86db33428604d74f6747c'
    patches = 'patches/gmm'

    @stage
    def configure(self):
        self.helper('autoreconf', '-fvi')
        blas = ''
        if self.arch.os == "osx":
            blas = '"-framework vecLib"'
        else:
            blas = glob(P.join(self.env['INSTALL_DIR'],'lib','libblas.so*'))[0]
        super(gmm,self).configure(with_=('blas=%s') % blas)

class xercesc(Package):
    src    = 'http://download.nextag.com/apache//xerces/c/3/sources/xerces-c-3.1.1.tar.gz'
    chksum = '177ec838c5119df57ec77eddec9a29f7e754c8b2'

    @stage
    def configure(self):
        super(xercesc,self).configure(with_=['curl=%s' % glob(P.join(self.env['INSTALL_DIR'],'lib','libcurl.*'))[0],
                                             'icu=no'],
                                      disable = ['static', 'msgloader-iconv', 'msgloader-icu', 'network'])

class qt(Package):
    src     = 'http://download.qt-project.org/official_releases/qt/4.8/4.8.5/qt-everywhere-opensource-src-4.8.5.tar.gz'
    chksum  = '745f9ebf091696c0d5403ce691dc28c039d77b9e'
    patches = 'patches/qt'
    patch_level = '-p0'

    def __init__(self, env):
        super(qt, self).__init__(env)

        # Qt can only be built on OSX with an Apple Compiler. If the
        # user overwrote the compiler choice, we must revert here. The
        # problem is -fconstant-cfstrings. Macports also gives up in
        # this situation and blacks lists all Macport built compilers.
        if self.arch.os == 'osx':
            self.env['CXX']='g++'
            self.env['CC']='gcc'

    @stage
    def configure(self):
        # The default confs override our compiler choices.
        self.helper('sed','-ibak','-e','s# g++# %s#g' % self.env['CXX'], '-e', 's# gcc# %s#g' % self.env['CC'], 'mkspecs/common/g++-base.conf')
        cmd = './configure -opensource -fast -confirm-license -nomake demos -nomake examples -nomake docs -nomake translations -no-webkit -prefix %(INSTALL_DIR)s -no-script -no-scripttools -no-openssl -no-libjpeg -no-libmng -no-libpng -no-libtiff -no-cups -no-nis -no-opengl -no-openvg -no-phonon -no-phonon-backend -no-sql-psql -no-dbus' % self.env
        args = cmd.split()
        if self.arch.os == 'osx':
            args.append('-no-framework')
            args.extend(['-arch',self.env['OSX_ARCH']])
        self.helper(*args)

    @stage
    def install(self):
        # Call the install itself afterward
        super(qt, self).install()

class qwt(Package):
    src     = 'http://downloads.sourceforge.net/qwt/qwt-6.1.0.tar.bz2',
    chksum  = '48a967038f7aa9a9c87c64bcb2eb07c5df375565',
    patches = 'patches/qwt'

    def configure(self):
        installDir = self.env['INSTALL_DIR']

        # Wipe old installation, otherwise qwt refuses to install
        cmd = ['rm', '-vf'] + glob(P.join(installDir, 'lib/', 'libqwt.*'))
        self.helper(*cmd)

        cmd = [installDir + '/bin/qmake','-spec']
        if self.arch.os == 'osx':
            cmd.append(P.join(installDir,'mkspecs','macx-g++'))
        else:
            cmd.append(P.join(installDir,'mkspecs','linux-g++'))
        self.helper(*cmd)

    # Qwt pollutes the doc folder
    @stage
    def install(self):
        super(qwt, self).install()
        cmd = ['rm', '-vrf', P.join( self.env['INSTALL_DIR'], 'doc', 'html' ) ]
        self.helper(*cmd)
        cmd = ['rm', '-vrf', P.join( self.env['INSTALL_DIR'], 'doc', 'man' ) ]
        self.helper(*cmd)

class zlib(Package):
    src     = 'http://downloads.sourceforge.net/libpng/zlib-1.2.8.tar.gz'
    chksum  = 'a4d316c404ff54ca545ea71a27af7dbc29817088'

    @stage
    def configure(self):
        super(zlib,self).configure(other=('--shared',))

    @stage
    def install(self):
        super(zlib, self).install()
        self.helper(*['rm', P.join(self.env['INSTALL_DIR'], 'lib', 'libz.a')])

class tiff(Package):
    src     = 'http://download.osgeo.org/libtiff/tiff-4.0.3.tar.gz'
    chksum  = '652e97b78f1444237a82cbcfe014310e776eb6f0'

    def configure(self):
        super(tiff, self).configure(
            with_ = ['jpeg', 'png', 'zlib'],
            without = ['x'],
            enable=('shared',),
            disable = ['static', 'lzma', 'cxx', 'logluv'])

class jpeg(Package):
    src     = 'http://www.ijg.org/files/jpegsrc.v8d.tar.gz'
    chksum  = 'f080b2fffc7581f7d19b968092ba9ebc234556ff'
    patches = 'patches/jpeg8'

    def configure(self):
        super(jpeg, self).configure(enable=('shared',), disable=('static',))

class png(Package):
    src    = 'http://downloads.sourceforge.net/libpng/libpng-1.6.2.tar.gz'
    chksum = 'd10af2004e7608425cbb8a8a99209a27af276ff7'

    def configure(self):
        super(png,self).configure(disable='static')

class cspice(Package):
    # This will break when they release a new version BECAUSE THEY USE UNVERSIONED TARBALLS.
    PLATFORM = dict(
        linux64 = dict(
            src    = 'ftp://naif.jpl.nasa.gov/pub/naif/toolkit/C/PC_Linux_GCC_64bit/packages/cspice.tar.Z',
            chksum = '29e3bdea10fd4005a4db8934b8d953c116a2cec7', # N0064
            ),
        linux32 = dict(
            src    = 'ftp://naif.jpl.nasa.gov/pub/naif/toolkit/C/PC_Linux_GCC_32bit/packages/cspice.tar.Z',
            chksum = 'df8ad284db3efef912a0a3090acedd2c4561a25f', # N0064
            ),
        osx32   = dict(
            src    = 'ftp://naif.jpl.nasa.gov/pub/naif/toolkit/C/MacIntel_OSX_AppleC_32bit/packages/cspice.tar.Z',
            chksum = '3a1174d0b5ca183168115d8259901e923b97eec0', # N0064
            ),
        osx64   = dict(
            src    = 'ftp://naif.jpl.nasa.gov/pub/naif/toolkit//C/MacIntel_OSX_AppleC_64bit/packages/cspice.tar.Z',
            chksum = 'e5546a72a2d0c7e337850a10d208014efb57d78d', # N0064
            ),
        )

    def __init__(self, env):
        super(cspice, self).__init__(env)
        self.pkgname += '_' + self.arch.osbits
        self.src    = self.PLATFORM[self.arch.osbits]['src']
        self.chksum = self.PLATFORM[self.arch.osbits]['chksum']
        if self.arch.os == "osx":
            self.patches = 'patches/cspice_osx'
        else:
            self.patches = 'patches/cspice_linux'
    def configure(self): pass

    @stage
    def compile(self):
        cmd = ['csh']
        self.args = ['./makeall.csh']
        cmd += self.args
        self.helper(*cmd)

    @stage
    def install(self):
        d = P.join('%(INSTALL_DIR)s' % self.env, 'include', 'naif')
        self.helper('mkdir', '-p', d)
        cmd = ['cp', '-vf'] + glob(P.join(self.workdir, 'include', '*.h')) + [d]
        self.helper(*cmd)

        d = P.join('%(INSTALL_DIR)s' % self.env, 'lib')
        self.helper('mkdir', '-p', d)
        # Wipe the static libraries
        cmd = ['rm' ] + glob(P.join(self.workdir,'lib', '*.a'))
        self.helper(*cmd)
        # Copy everything else, including the dynamic libraries
        cmd = ['cp', '-vf'] + glob(P.join(self.workdir, 'lib', '*')) + [d]
        self.helper(*cmd)

class protobuf(Package):
    src = 'http://protobuf.googlecode.com/files/protobuf-2.4.1.tar.bz2'
    chksum = 'df5867e37a4b51fb69f53a8baf5b994938691d6d'

    @stage
    def configure(self):
        self.helper('./autogen.sh')
        super(protobuf, self).configure(disable=('static'))

class ufconfig(Package):
    src = 'http://ftp.ucsb.edu/pub/mirrors/linux/gentoo/distfiles/UFconfig-3.6.1.tar.gz'
    chksum = '2cf8f557787b462de3427e979d1b0de82466326f'

    def configure(self):
        pass

    @stage
    def compile(self):
        compile_cmd = [self.env['CC']] + self.env['CFLAGS'].split(' ')
        compile_cmd += ['-fPIC','-c', 'UFconfig.c', '-o', 'UFconfig.lo']
        self.helper(*compile_cmd)
        link_cmd = [self.env['CC']] + self.env['LDFLAGS'].split(' ')
        link_cmd += ['-shared','UFconfig.lo']
        if self.arch.os == 'osx':
            link_cmd.extend(['-dynamiclib','-Wl,-install_name,libufconfig.3.6.1.dylib','-o','libufconfig.3.6.1.dylib'])
        else:
            link_cmd.extend(['-Wl,-soname,libufconfig.so.3.6.1','-o','libufconfig.so.3.6.1'])
        self.helper(*link_cmd)

    def build(self):
        pass

    @stage
    def install(self):
        # This is all manual since UFconfig doesn't supply a viable
        # build system.
        e = self.env.copy_set_default(prefix = self.env['INSTALL_DIR'])
        installdir = self.env['INSTALL_DIR']
        if not P.isdir(P.join(installdir,'lib')):
            os.mkdir(P.join(installdir,'lib'))
        else:
            for filename in glob(P.join(installdir,'lib','libufconfig*')):
                os.remove(filename)
        if not P.isdir(P.join(installdir,'include')):
            os.mkdir(P.join(installdir,'include'))
        else:
            if P.isfile(P.join(installdir, 'include', 'UFconfig.h')):
                os.remove(P.join(installdir,'include','UFconfig.h'))
        if self.arch.os == 'osx':
            self.helper('glibtool','--mode=install','install','-c','libufconfig.3.6.1.dylib',P.join(installdir,'lib'),env=e)
            self.helper('ln','-s','libufconfig.3.6.1.dylib',P.join(installdir,'lib','libufconfig.dylib'),env=e)
        else:
            self.helper('libtool','--mode=install','install','-c','libufconfig.so.3.6.1',P.join(installdir,'lib'),env=e)
            self.helper('ln','-s','libufconfig.so.3.6.1',P.join(installdir,'lib','libufconfig.so'),env=e)
        self.helper('install','-m','644','-c','UFconfig.h',P.join(installdir,'include'),env=e)

class amd(Package):
    src = ['http://sources.gentoo.org/cgi-bin/viewvc.cgi/gentoo-x86/sci-libs/amd/files/amd-2.2.0-autotools.patch','http://ftp.ucsb.edu/pub/mirrors/linux/gentoo/distfiles/AMD-2.2.3.tar.gz']
    chksum = ['1b452db185458c92b34634f0a88f643c4f851659','cedd6c37c7d214655a0b967a45994e7ec5c38251']
    patch_level = '-p0'

    def __init__(self, env):
        super(amd, self).__init__(env)
        self.patches = [P.join(env['DOWNLOAD_DIR'],'amd-2.2.0-autotools.patch'),
                        P.join(self.pkgdir,'patches/amd/0001-disable-fortran.patch'),
                        P.join(self.pkgdir,'patches/amd/0002-amd-libtool.patch')]

    @stage
    def configure(self):
        self.helper('mkdir','m4')
        self.helper('autoreconf','--verbose','--install')
        super(amd, self).configure(disable='static')

class colamd(Package):
    src = ['http://sources.gentoo.org/cgi-bin/viewvc.cgi/gentoo-x86/sci-libs/colamd/files/colamd-2.7.1-autotools.patch','http://ftp.ucsb.edu/pub/mirrors/linux/gentoo/distfiles/COLAMD-2.7.3.tar.gz']
    chksum = ['0c1a3c429f929b77998aec88dd5c4f5169547f9a','75d490967b180c86cc33e04daeebf217ed179987']
    patch_level = '-p0'

    def __init__(self, env):
        super(colamd, self).__init__(env)
        self.patches = [P.join(env['DOWNLOAD_DIR'],'colamd-2.7.1-autotools.patch'),
                        P.join(self.pkgdir, 'patches/colamd/0001_colamd_libtool.patch')]

    @stage
    def configure(self):
        self.helper('mkdir','m4')
        self.helper('autoreconf','--verbose','--install')
        super(colamd, self).configure(disable='static')

class cholmod(Package):
    src = ['http://ftp.ucsb.edu/pub/mirrors/linux/gentoo/distfiles/cholmod-1.7.0-autotools.patch.bz2','http://www.cise.ufl.edu/research/sparse/cholmod/CHOLMOD-1.7.3.tar.gz']
    chksum = ['0c15bc824b590d096998417f07b1849cc6f645fb','c85ce011da25337f53c0a5b11e329d855698caa0']

    def __init__(self, env):
        super(cholmod,self).__init__(env)
        self.patches = [P.join(env['DOWNLOAD_DIR'],'cholmod-1.7.0-autotools.patch'),
                        P.join(self.pkgdir,'patches/cholmod/0001-fix-cholmod-build.patch'),
                        P.join(self.pkgdir,'patches/cholmod/0002_cholamd_libtool.patch')]

    @stage
    def unpack(self):
        if P.isfile(P.join(self.env['DOWNLOAD_DIR'],'cholmod-1.7.0-autotools.patch')):
            os.remove(P.join(self.env['DOWNLOAD_DIR'],'cholmod-1.7.0-autotools.patch'))
        self.helper('bzip2','-d','-k',P.join(self.env['DOWNLOAD_DIR'],'cholmod-1.7.0-autotools.patch.bz2'))
        super(cholmod, self).unpack()

    @stage
    def configure(self):
        self.helper('mkdir','m4')
        self.helper('autoreconf','--install','--force','--verbose')
        super(cholmod, self).configure(disable=('static','mod-partition','mod-supernodal'))

    @stage
    def install(self):
        super(cholmod, self).install()

        # ISIS also demands that the CHOLMOD and family headers be
        # available in a CHOLMOD directory. Instead of editing their
        # build system .. we'll just softlink the headers into place.
        d = P.join(self.env['INSTALL_DIR'],'include')
        if P.exists( P.join(d,'CHOLMOD') ):
            self.helper('rm', '-rf', P.join(d,'CHOLMOD'))
        os.mkdir(P.join(d,'CHOLMOD'))
        headers = []
        headers.extend( glob( P.join(d,'UFconfig.h') ) )
        headers.extend( glob( P.join(d,'cholmod*.h') ) )
        for header in headers:
            os.symlink( P.relpath( header,
                                   P.join(d,'CHOLMOD') ),
                        P.join(d,'CHOLMOD',P.basename(header)) )

class osg3(CMakePackage):
    src = 'http://www.openscenegraph.org/downloads/stable_releases/OpenSceneGraph-3.0.1/source/OpenSceneGraph-3.0.1.zip'
    chksum = '13c7e39f6d62047ad944d8d28a0f0eb60384ce33'
    patches = 'patches/osg3'

    def configure(self):
        super(osg3, self).configure(
            with_='GDAL GLUT JPEG OpenEXR PNG ZLIB CURL QuickTime CoreVideo QTKit'.split(),
            without='COLLADA FBX FFmpeg FLTK FOX FreeType GIFLIB Inventor ITK Jasper LibVNCServer OpenAL OpenVRML OurDCMTK Performer Qt3 Qt4 SDL TIFF wxWidgets Xine XUL RSVG NVTT DirectInput GtkGL Poppler-glib GTA'.split(),
            other=['-DBUILD_OSG_APPLICATIONS=ON',
                   '-DCMAKE_VERBOSE_MAKEFILE=ON'
                   ])

class flann(CMakePackage):
    src = 'http://people.cs.ubc.ca/~mariusm/uploads/FLANN/flann-1.8.4-src.zip'
    chksum = 'e03d9d458757f70f6af1d330ff453e3621550a4f'

    @stage
    def configure(self):
        super(flann, self).configure(other=['-DBUILD_C_BINDINGS=OFF','-DBUILD_MATLAB_BINDINGS=OFF','-DBUILD_PYTHON_BINDINGS=OFF','-DBUILD_CUDA_LIB=OFF','-DUSE_MPI=OFF','-DUSE_OPENMP=OFF'])

    @stage
    def install(self):
        super(flann, self).install()
        cmd = ['rm' ] +glob(P.join(self.env['INSTALL_DIR'], 'lib', 'libflann*.a'))
        self.helper(*cmd)

class yaml(CMakePackage):
    src = 'http://yaml-cpp.googlecode.com/files/yaml-cpp-0.3.0.tar.gz'
    chksum = '28766efa95f1b0f697c4b4a1580a9972be7c9c41'

    def configure(self):
        super(yaml, self).configure(other=[
            '-DBoost_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include','boost-'+boost.version),
            '-DBoost_LIBRARY_DIRS=' + P.join(self.env['INSTALL_DIR'],'lib'),
            '-DCMAKE_BUILD_TYPE=RelWithDebInfo',
            '-DBUILD_SHARED_LIBS=ON'
            ])

class eigen(CMakePackage):
    src = 'http://bitbucket.org/eigen/eigen/get/3.1.3.tar.bz2'
    chksum = '07e248deaaa5d2a8822a0581a606151127fce450'

    def configure(self):
        super(eigen, self).configure(other=[
            '-DBoost_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include','boost-'+boost.version),
            '-DBoost_LIBRARY_DIRS=' + P.join(self.env['INSTALL_DIR'],'lib'),
            '-DCMAKE_BUILD_TYPE=RelWithDebInfo'
            ])

class libnabo(CMakePackage):
    # We keep this on byss as this software does not have a fixed release,
    # and getting things from github directly means at some point
    # it may change to the point where it breaks.
    src = 'https://byss.arc.nasa.gov/asp_packages/libnabo-0.0.0.tgz'
    chksum = 'bc71180748b5ebf1c3bbfe3f45a34e6d6be3dbec'

    def configure(self):
        super(libnabo, self).configure(other=[
            '-DCMAKE_CXX_FLAGS=-g -O3',
            '-DEIGEN_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include/eigen3'),
            '-DBoost_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include','boost-'+boost.version),
            '-DBoost_LIBRARY_DIRS=' + P.join(self.env['INSTALL_DIR'],'lib'),
            '-DCMAKE_VERBOSE_MAKEFILE=ON',
            '-DSHARED_LIBS=ON'
            ])

class libpointmatcher(CMakePackage):
    # We keep this on byss as we hacked it a bit to compile. Besides,
    # we'd like to have a fixed reference version rather than getting
    # it from github.
    src = 'https://byss.arc.nasa.gov/asp_packages/libpointmatcher-0.0.0.tgz'
    chksum = '434d97f3255514b3d8d26c009bde7bfc320c9c8a'
    patches = 'patches/libpointmatcher'

    def configure(self):
        installDir = self.env['INSTALL_DIR']
        boost_include = P.join(installDir,'include','boost-'+boost.version)
        self.env['CXXFLAGS'] += ' -I="' + boost_include + '"' # bugfix for lunokhod2
        super(libpointmatcher, self).configure(other=[
            '-DCMAKE_CXX_FLAGS=-g -O3 -I' + boost_include,
            '-DBoost_INCLUDE_DIR=' + boost_include,
            '-DBoost_LIBRARY_DIRS=' + P.join(installDir,'lib'),
            '-DEIGEN_INCLUDE_DIR=' + P.join(installDir,'include/eigen3'),
            '-DCMAKE_VERBOSE_MAKEFILE=ON',
            '-DCMAKE_PREFIX_PATH=' + installDir,
            '-DSHARED_LIBS=ON'
            ])
