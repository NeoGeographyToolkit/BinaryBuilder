#!/usr/bin/env python

from __future__ import print_function
import os, shutil
import os.path as P
import re, sys
from glob import glob
import subprocess
from BinaryBuilder import CMakePackage, GITPackage, Package, stage, warn, \
     PackageError, HelperError, SVNPackage, Apps, write_vw_config, write_asp_config, \
     replace_line_in_file, run, get, program_paths
from BinaryDist import fix_install_paths, lib_ext

class ccache(Package):
    src     = 'https://www.samba.org/ftp/ccache/ccache-3.1.12.tar.bz2'
    chksum  = '64c4bbe08187a448bc3526b1e657f1cbd1aff855'

class m4(Package):
    src     = 'http://ftp.gnu.org/gnu/m4/m4-1.4.17.tar.gz'
    chksum  = '4f80aed6d8ae3dacf97a0cb6e989845269e342f0'

    def configure(self):
        self.env['CPPFLAGS'] += ' -fgnu89-inline' # Needed for CentOS 5
        super(m4, self).configure()

class libtool(Package):
    src     = 'http://ftpmirror.gnu.org/libtool/libtool-2.4.2.tar.gz'
    chksum  = '22b71a8b5ce3ad86e1094e7285981cae10e6ff88'

class autoconf(Package):
    src='http://ftp.gnu.org/gnu/autoconf/autoconf-2.69.tar.gz'
    chksum  = '562471cbcb0dd0fa42a76665acf0dbb68479b78a'

class automake(Package):
    src='ftp://ftp.gnu.org/gnu/automake/automake-1.14.1.tar.gz'
    chksum  = '0bb1714b78d70cab9907d2013082978a28f48a46'

class cmake(Package):
    src     = 'http://www.cmake.org/files/v3.2/cmake-3.2.3.tar.gz'
    chksum  = 'fa176cc5b1ccf2e98196b50908432d0268323501'
    def configure(self):
        opts = []
        if self.arch.os == 'osx':
            opts = ['--system-curl']
        super(cmake, self).configure(
            other = opts
            )

    # cmake pollutes the doc folder
    @stage
    def install(self):
        super(cmake, self).install()
        cmd = ['rm', '-vrf'] + glob(P.join( self.env['INSTALL_DIR'], 'doc', 'cmake*' ))
        self.helper(*cmd)

class chrpath(Package):
    src     = 'http://ftp.debian.org/debian/pool/main/c/chrpath/chrpath_0.13.orig.tar.gz'
    chksum  = '11ff3e3dda2acaf1e529475f394f74f2ef7a8204'
    # chrpath pollutes the doc folder
    @stage
    def install(self):
        super(chrpath, self).install()
        cmd = ['rm', '-vrf'] + glob(P.join( self.env['INSTALL_DIR'], 'doc', 'chrpath*' ))
        self.helper(*cmd)

class bzip2(Package):
    src     = 'http://www.bzip.org/1.0.6/bzip2-1.0.6.tar.gz'
    chksum  = '3f89f861209ce81a6bab1fd1998c0ef311712002'

    def configure(self):
        # Not doing anything here so add this option (required for ImageMagick) while we are here
        self.env['MAKEOPTS'] += ''' CFLAGS="-fPIC"'''

    @stage
    def install(self):
        # Copy just the things we need.
        self.helper(*['mkdir','-p',P.join(self.env['INSTALL_DIR'],'include')]);
        self.helper(*['mkdir','-p',P.join(self.env['INSTALL_DIR'],'lib')]);
        self.helper(*['mkdir','-p',P.join(self.env['INSTALL_DIR'],'bin')]);
        cmd = ['cp', '-vf'] + glob(P.join(self.workdir, '*.h')) + \
              [P.join(self.env['INSTALL_DIR'], 'include')]
        self.helper(*cmd)
        cmd = ['cp', '-vf'] + glob(P.join(self.workdir, 'lib*')) + \
              [P.join(self.env['INSTALL_DIR'], 'lib')]
        self.helper(*cmd)
        cmd = ['cp', '-vf', P.join(self.workdir, 'bzip2'),
               P.join(self.env['INSTALL_DIR'], 'bin')]
        self.helper(*cmd)

class pbzip2(Package):
    src     = 'http://compression.ca/pbzip2/pbzip2-1.1.6.tar.gz'
    chksum  = '3b4d0ffa3ac362c3702793cc5d9e61664d468aeb'
    def configure(self): pass
    def compile(self):
        self.helper('sed','-ibak','-e','s# g++# %s#g' % self.env['CXX'],
                    'Makefile');
        cflags = 'CFLAGS = -I' + P.join(self.env['INSTALL_DIR'], 'include') + \
                 ' -L' + P.join(self.env['INSTALL_DIR'], 'lib') + ' '
        self.helper('sed','-ibak','-e','s#CFLAGS = #%s#g' % cflags, 'Makefile')
        super(pbzip2, self).compile()
    def install(self):
        # Copy just the things we need.
        cmd = ['cp', '-vf', P.join(self.workdir, 'pbzip2'),
               P.join(self.env['INSTALL_DIR'], 'bin')]
        self.helper(*cmd)

class parallel(Package):
    src     = 'http://ftp.gnu.org/gnu/parallel/parallel-20130822.tar.bz2'
    chksum  = 'd493a8982837d49806fd05d9d474aa8e9afbddf3'

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
    patches = 'patches/tnt'

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
    # Note: Upgrading to a newer openjpeg causes problems with dem_geoid.
    # The solution may be to convert the old jp2 geoid to the new
    # jp2 format perhaps.
    src     = 'https://github.com/uclouvain/openjpeg/archive/version.2.0.tar.gz'
    chksum  = 'a2e65326289a5836b82ed8567a2de8a283d722cd'

    @stage
    def configure(self):
        curr_include = '-I' + self.workdir + '/src/bin/common'
        self.env['CPPFLAGS'] = curr_include + ' ' + self.env['CPPFLAGS']
        super(openjpeg2, self).configure(other=['-DBUILD_SHARED_LIBS=ON'])

class tiff(Package):
    src     = 'http://download.osgeo.org/libtiff/tiff-4.0.8.tar.gz'
    chksum  = '88717c97480a7976c94d23b6d9ed4ac74715267f'

    def configure(self):
        super(tiff, self).configure(
            with_ = ['jpeg', 'png', 'zlib'],
            without = ['x'],
            enable=('shared',),
            disable = ['static', 'lzma', 'cxx', 'logluv'])

class libgeotiff(CMakePackage):
    src='http://download.osgeo.org/geotiff/libgeotiff/libgeotiff-1.4.0.tar.gz'
    chksum='4c6f405869826bb7d9f35f1d69167e3b44a57ef0'
    def configure(self):
        super(libgeotiff, self).configure( other=['-DBUILD_SHARED_LIBS=ON',
                                                  '-DBUILD_STATIC_LIBS=OFF'] )

class gdal(Package):
    src     = 'http://download.osgeo.org/gdal/2.0.2/gdal202.zip'
    chksum  = '91c1ce0e5156ab0e2671ae9133324e52f12c73b8'
    patches = 'patches/gdal'

    @stage
    def configure(self):
        # Parts of GDAL will attempt to load libproj manual (something
        # we can't see or correct in the elf tables). This sed should
        # correct that problem.
        self.env['LDFLAGS'] += ' -Wl,-rpath -Wl,%(INSTALL_DIR)s/lib -ljpeg -lproj' % self.env
        self.helper('sed', '-ibak', '-e', 's/libproj./libproj.0./g', 'ogr/ogrct.cpp')

        w = ['threads', 'libtiff', 'geotiff=' + self.env['INSTALL_DIR'],
             'jpeg=' + self.env['INSTALL_DIR'],
             'png', 'zlib', 'pam',
             'openjpeg=' + self.env['INSTALL_DIR'],
             'geos=yes',
             'curl']
        wo = \
            '''bsb cfitsio dods-root dwg-plt dwgdirect ecw epsilon expat expat-inc expat-lib fme
               gif grass hdf4 hdf5 idb ingres jasper jp2mrsid kakadu libgrass
               macosx-framework mrsid msg mysql netcdf oci oci-include oci-lib odbc ogdi pcidsk
               pcraster perl pg php pymoddir python ruby sde sde-version spatialite sqlite3
               static-proj4 xerces xerces-inc xerces-lib libiconv-prefix libiconv xml2 pcre
               freexl'''.split()

        self.helper('./autogen.sh')
        super(gdal,self).configure(with_=w, without=wo, disable='static', enable='shared')

    @stage
    def install(self):
        super(gdal, self).install()
        # Copy gdal_translate and gdalinfo to libexec, as we want it
        # to be hidden there in the released ASP distribution.
        progs = ['gdalinfo', 'gdal_translate']
        libexec = P.join( self.env['INSTALL_DIR'], 'libexec' )
        self.helper('mkdir', '-p', libexec)
        for prog in progs:
            cmd = ['cp', '-vf', P.join( self.env['INSTALL_DIR'], 'bin',
                                        prog ), libexec]
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
        # XCode in snow leopard removed this flag entirely
        self.helper('sed', '-ibak', '-e', 's/-Wno-long-double//g', 'configure.ac')
        self.helper('autoupdate', 'configure.ac')
        self.helper('autoreconf', '-fvi')
        super(openexr,self).configure(with_=('ilmbase-prefix=%(INSTALL_DIR)s' % self.env),
                                      disable=('ilmbasetest', 'imfexamples', 'static'))

class proj(Package):
    src     = 'http://download.osgeo.org/proj/proj-4.8.0.tar.gz'
    chksum  = '5c8d6769a791c390c873fef92134bf20bb20e82a'
    def install(self):
        super(proj, self).install()
        # Copy extra files which are needed by libgeotiff to compile.
        cmd = ['cp', '-vf'] + glob(P.join(self.workdir, 'src/*.h')) + \
              [P.join(self.env['INSTALL_DIR'], 'include')]
        self.helper(*cmd)

    @stage
    def configure(self):
        super(proj,self).configure(disable='static', without='jni')

class openssl(Package):
    src = 'https://github.com/openssl/openssl/archive/OpenSSL_1_1_0e.tar.gz'
    chksum = '14eaed8edc7e48fe1f01924fa4561c1865c9c8ac'

    @stage
    def configure(self):
        cmd = ('./config --prefix=%s --openssldir=%s --with-zlib-include=%s --with-zlib-lib=%s' 
               % (self.env['INSTALL_DIR'], self.env['BUILD_DIR'], 
                  self.env['INSTALL_DIR']+'/include', self.env['INSTALL_DIR']+'/lib'))

        args = cmd.split()
        self.helper(*args)

class curl(Package):
    src     = 'http://curl.haxx.se/download/curl-7.33.0.tar.bz2'
    chksum  = 'b0dc79066f31a000190fd8a15277738e8c1940aa'

    @stage
    def configure(self):
        w = ['zlib='+self.env['INSTALL_DIR'], 'ssl='+self.env['INSTALL_DIR']]
        wo = 'libidn'.split()
        super(curl,self).configure(
            with_=w, without=wo, disable=['static','ldap','ldaps'])

class liblas(CMakePackage):
    src     = 'http://download.osgeo.org/liblas/libLAS-1.8.0.tar.bz2'
    chksum  = '73a29a97dfb8373d51c5e36bdf12a825c44fa398'

    @stage
    def configure(self):
        # Remove the pedantic flag. Latest boost is not compliant.
        self.helper('sed', '-ibak', '-e', 's/-pedantic//g', 'CMakeLists.txt')

        self.env['LDFLAGS'] += ' -Wl,-rpath -Wl,%(INSTALL_DIR)s/lib' % self.env

        super(liblas, self).configure(other=[
            '-DBoost_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include','boost-'+boost.version),
            '-DBoost_LIBRARY_DIRS=' + P.join(self.env['INSTALL_DIR'],'lib'),
            '-DWITH_LASZIP=true',
            '-DLASZIP_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include'),
            '-DWITH_GDAL=true',
            '-DGDAL_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include'),
            '-DWITH_GEOTIFF=true',
            '-DGEOTIFF_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include')
            ])

    @stage
    def install(self):
        super(liblas, self).install()
        # Copy lasinfo to libexec, as we want it
        # to be hidden there in the released ASP distribution.
        progs = ['lasinfo']
        libexec = P.join( self.env['INSTALL_DIR'], 'libexec' )
        self.helper('mkdir', '-p', libexec)
        for prog in progs:
            cmd = ['cp', '-vf', P.join( self.env['INSTALL_DIR'], 'bin',
                                        prog ), libexec]
            self.helper(*cmd)

class laszip(CMakePackage):
    src     = 'http://download.osgeo.org/laszip/laszip-2.1.0.tar.gz'
    chksum  = 'bbda26b8a760970ff3da3cfac97603dd0ec4f05f'

class geoid(Package):
    src     = 'https://github.com/NeoGeographyToolkit/StereoPipeline/releases/download/geoid1.0/geoids.tgz'
    chksum  = 'e6e3961d6a84e10b4c49039b9a84098d57bd2206'

    @stage
    def configure(self): pass

    def compile(self):
        self.helper(self.env['F77'], '-c','-fPIC','interp_2p5min.f')
        if self.arch.os == 'osx':
            flag = '-dynamiclib'
        else:
            flag = '-shared'
        self.helper(self.env['F77'], flag, '-o', 'libegm2008.so', 'interp_2p5min.o')

    def install(self):
        cmd = ['cp'] + glob(P.join(self.workdir, 'libegm2008.*')) \
              + [P.join(self.env['INSTALL_DIR'], 'lib')]
        self.helper(*cmd)
        geoidDir = P.join(self.env['INSTALL_DIR'], 'share/geoids')
        self.helper('mkdir', '-p', geoidDir)
        cmd = ['cp'] + glob(P.join(self.workdir, '*tif')) \
        + glob(P.join(self.workdir, '*jp2')) + [geoidDir]
        self.helper(*cmd)

class hdf5(Package):
    src     = 'https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-1.8/hdf5-1.8.16/src/hdf5-1.8.16.tar.bz2'
    chksum  = 'a7b631778cb289edec670f665d2c3265983a0d53'
    def configure(self):
        super(hdf5, self).configure(enable=('cxx'), disable = ['static'])

# Build our copy of the ISIS code...
class isis(GITPackage, CMakePackage):
    src = 'https://github.com/NeoGeographyToolkit/IsisCMake.git'
    chksum = '2eee0ec'
    patches = 'patches/isis'

    # For now we are using our CMake copy of the ISIS code but this will
    #  change some time in the future.

    #def __init__(self, env):
    #    super(isis, self).__init__(env)
    #    self.isis_localcopy = P.join(env['DOWNLOAD_DIR'], 'rsync', self.pkgname)
    #    # We download the source code from the OSX branch, should be same code
    #    # as on the Linux side.
    #    self.isis_src = "isisdist.astrogeology.usgs.gov::x86-64_darwin_OSX/isis/"

    #    # Fetch the ISIS version. We will rebuild it each time
    #    # the version changes.
    #    cmd = ['rsync', self.isis_src +'version', '.']
    #    self.helper(*cmd)
    #    f = open('version','r')
    #    self.chksum = f.readline().strip()
    #    if self.chksum == "":
    #        raise PackageError(self, 'Could not find the ISIS version')

    @stage
    def configure(self):
        # Copy the version file to the install folder
        #cmd = ['cp', P.join(self.workdir, 'version'), self.env['INSTALL_DIR']]

        #curr_include = '-I' + P.join(self.env['INSTALL_DIR'],'include','boost-'+boost.version)
        #self.env['CPPFLAGS'] = curr_include + ' ' + self.env['CPPFLAGS']

        # Run the default configure process
        
        super(isis, self).configure(other=['-DbuildMissions=ON','-DbuildTests=OFF','-DbuildApps=OFF'])

class stereopipeline(GITPackage):
    src     = 'https://github.com/NeoGeographyToolkit/StereoPipeline.git'
    def configure(self):

        # Skip config in fast mode if config file exists
        config_file = P.join(self.workdir, 'config.options')
        if self.fast and os.path.isfile(config_file): return

        self.helper('./autogen')

        use_env_flags = True
        prefix        = self.env['INSTALL_DIR']
        installdir    = prefix
        vw_build      = prefix
        arch          = self.arch
        write_asp_config(use_env_flags, prefix, installdir, vw_build,
                         arch, geoid, config_file)

        super(stereopipeline, self).configure(
            other   = ['docdir=%s/doc' % prefix],
            without = ['clapack', 'slapack', 'tcmalloc'],
            disable = ['pkg_paths_default', 'static', 'qt-qmake'],
            enable  = ['debug=ignore', 'optimize=ignore']
            )

    @stage
    def compile(self, cwd=None):
        super(stereopipeline, self).compile(cwd)
        # Run unit tests. If the ISIS env vars are not set,
        # the ISIS-related tests will be skipped.
        # Make install must happen before 'make check',
        # otherwise the old installed library is linked.
        cmd = ('make', 'install')
        self.helper(*cmd)
        if self.fast or self.arch.os == 'osx' or int(self.env['SKIP_TESTS']) == 1:
            # The tests on the Mac do not compile, looks like a clang/gtest conflict.
            print("Skipping tests for OSX or in fast mode.")
        else:
            cmd = ('make', 'check')
            self.helper(*cmd)

class visionworkbench(GITPackage):
    src = 'https://github.com/visionworkbench/visionworkbench.git'

    def __init__(self,env):
        super(visionworkbench,self).__init__(env)

    @stage
    def configure(self):
        # Skip config in fast mode if config file exists
        config_file  = P.join(self.workdir, 'config.options')
        if self.fast and os.path.isfile(config_file): return

        self.helper('./autogen')

        arch         = self.arch
        installdir   = self.env['INSTALL_DIR']
        prefix       = installdir
        write_vw_config(prefix, installdir, arch, config_file)       
        fix_install_paths(installdir, arch) # this is needed for Mac for libgeotiff
        super(visionworkbench, self).configure()

    @stage
    def compile(self, cwd=None):
        super(visionworkbench, self).compile(cwd)
        # Run unit tests
        # Make install must happen before 'make check',
        # otherwise the old installed library is linked.
        cmd = ('make', 'install')
        self.helper(*cmd)
        if self.fast or self.arch.os == 'osx' or int(self.env['SKIP_TESTS']) == 1:
            # The tests on the Mac do not even compile, looks like a clang/gtest conflict
            print("Skipping tests for OSX or in fast mode.")
        else:
            cmd = ('make', 'check')
            self.helper(*cmd)

class lapack(CMakePackage):
    src     = 'http://www.netlib.org/lapack/lapack-3.5.0.tgz'
    chksum  = '5870081889bf5d15fd977993daab29cf3c5ea970'

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
    version = '1_59' # variable is used in class liblas, libnabo, etc.
    src     = 'http://downloads.sourceforge.net/boost/boost_' + version + '_0.tar.bz2'
    chksum  = 'b94de47108b2cdb0f931833a7a9834c2dd3ca46e'
    patches = 'patches/boost'

    def __init__(self, env):
        super(boost, self).__init__(env)
        self.env['NO_BZIP2'] = '1'
        #self.env['NO_ZLIB']  = '1'
        if self.arch.os == 'osx':
            self.env['PATH'] = '/usr/bin:' + self.env['PATH'] # to use the right libtool

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

    @stage
    def install(self):
        self.env['BOOST_ROOT'] = self.workdir
        cmd = ['./bjam'] + self.args + ['install']
        self.helper(*cmd)

class gsl(Package):
    src = 'ftp://ftp.gnu.org/gnu/gsl/gsl-1.15.tar.gz',
    chksum = 'd914f84b39a5274b0a589d9b83a66f44cd17ca8e',

    def configure(self):
        super(gsl, self).configure(disable=('static'))

class geos(Package):
    src = 'http://download.osgeo.org/geos/geos-3.5.1.tar.bz2'
    chksum = '83373542335c2f20c22d5420ba01d99f645f0c61'

    def __init__(self, env):
        super(geos, self).__init__(env)
        if self.arch.os == 'linux':
            # Bugfix for SuSE, skip using ccache
            self.env['CXX']='g++'
            self.env['CC']='gcc'

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

        if self.arch.os == 'linux':
            # This is a bugfix, that took long to investigate. For some versions of Linux,
            # the FLIBS in configure contains the -R option, which confuses the compiler.
            # This value is determined dynamically. So we really have no choice but
            # to edit configure to modify this value before being used.
            line_in  = 'FLIBS="$ac_cv_f77_libs"'
            line_out = 'FLIBS=$(echo "$ac_cv_f77_libs" | perl -pi -e "s/ -R/ -Wl,-R/g")'
            configure_file = P.join(self.workdir, 'configure')
            replace_line_in_file(configure_file, line_in, line_out)
            
        super(superlu,self).configure(with_=('blas=%s') % blas,
                                      disable=('static'))
    
    @stage
    def install(self):
        super(superlu, self).install()

        # Need to comment out a few lines in the include files to get ISIS to compile with clang!!
        file_list = ['slu_cdefs.h', 'slu_ddefs.h', 'slu_sdefs.h', 'slu_zdefs.h']
        target_list = ['extern void    countnz',
                       'extern void    ilu_countnz',
                       'extern void    fixupL',
                       'extern void    PrintPerf',
                       'extern void    check_tempv']
        # Use sed to add // before every instance of these targets in these files
        for f in file_list:
            full_path = P.join(self.env['INSTALL_DIR'],'include', 'superlu', f)
            for target in target_list: 
                cmd = ['sed', '-i', '-e', 
                       "s#"+target+"#//"+target+"#g",
                       full_path]
                self.helper(*cmd)


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
    src    = 'http://archive.apache.org/dist/xerces/c/3/sources/xerces-c-3.1.3.tar.gz'
    chksum = 'ad0c6c93f90abbcfb692c2da246a8934ece03e95'

    @stage
    def configure(self):
        super(xercesc,self).configure(with_=['curl=%s' % glob(P.join(self.env['INSTALL_DIR'],'lib','libcurl.*'))[0],
                                             'icu=no'],
                                      disable = ['static', 'msgloader-iconv', 'msgloader-icu', 'network'])

class qt(Package):
    src     = 'http://download.qt-project.org/official_releases/qt/5.6/5.6.2/single/qt-everywhere-opensource-src-5.6.2.tar.gz'
    chksum  = '4385b53f78665ac340ea2a709ebecf1e776efdc2' #SHA-1 Hash
    #patches = 'patches/qt'
    #patch_level = '-p0'

    @stage
    def configure(self):

        # Modify the min OSX version
        config_path = self.workdir + '/qtbase/mkspecs/macx-clang/qmake.conf'
        self.helper('sed', '-ibak', '-e',
                    's/QMAKE_MACOSX_DEPLOYMENT_TARGET = 10.7/QMAKE_MACOSX_DEPLOYMENT_TARGET = 10.11/g',
                    config_path)

        ## The default confs override our compiler choices.
        cmd = './configure -c++std c++11  -opensource -confirm-license -nomake tools -nomake examples  -prefix %(INSTALL_DIR)s  -no-openssl -no-libjpeg  -no-libpng -no-cups -no-openvg -no-sql-psql -no-pulseaudio -skip webengine -skip macextras -skip serialbus -skip serialport -skip qtsensors -skip androidextras' % self.env

        # TODO: Make sure static libraries are not built!  Causes linker error in ASP in OSX. 
        args = cmd.split()
        if self.arch.os == 'osx':
            args.append('-no-framework')
            args.append('-no-xcb')
            args.append('-no-pch') # Required to avoid weird redefinition errors, but slows down compilation.
            args.extend(['-skip', 'x11extras'])
            args.extend(['-platform', 'macx-clang'])
        else:
            args.append('-qt-xcb') # Not needed on OSX
        self.helper(*args)

        if self.arch.os == 'osx':
            # Create a script to do a mass edit of all .pro files
            # to make them compile. Add some flags, and the -lc++ library.
            # Then execute the script.
            script = self.workdir + '/edit_pro.sh'
            print("script is ", script)
            f = open(script, 'w')
            f.write('#!/bin/bash\n'                                     + \
                    'cd ' + self.workdir + '\n'                         + \
                    'for f in $(find . -name \*pro); do\n'              + \
                    '  echo Editing $f\n'                               + \
                    '  cat $f > tmp.txt\n'                              + \
                    '  echo "CONFIG += c++11" > $f\n'                   + \
                    '  echo "QMAKE_CXXFLAGS += -stdlib=libc++ -std=c++11" >> $f\n' + \
                    '  echo "QMAKE_LDLAGS += -stdlib=libc++ -std=c++11"   >> $f\n' + \
                    '  cat tmp.txt >> $f\n'                             + \
                    '  perl -pi -e \'s#(QMAKE_LIBS\s+\+=\s)#$1 -lc++ #g\' $f\n' + \
                    'done\n')
            f.close()
            cmd = ['chmod', 'u+x', script]
            self.helper(*cmd)
            cmd=[script]
            self.helper(*cmd)

    @stage
    def install(self):
        super(qt, self).install()

        # Wipe some odd things in the .la file which I could not
        # figure out where they are coming from
        if self.arch.os == 'osx':
            cmd=['perl', '-pi', '-e',
                 's#-framework\s*(Security|Foundation|ApplicationServices' + \
                 '|IOKit|DiskArbitration)##g']                             + \
                 glob(P.join(self.env['INSTALL_DIR'], 'lib/', '*Qt*.la'))
            self.helper(*cmd)

        # Add a Prefix entry to INSTALL_DIR/bin/qt.conf so that qmake
        #       finds the correct QT install location!
        config_path = os.path.join(self.env['INSTALL_DIR'], 'bin/qt.conf')
        print(config_path)
        with open(config_path, "w") as f:
            f.write('[Paths]\n')
            f.write('Plugins=../lib/plugins/\n')
            f.write('Prefix='+self.env['INSTALL_DIR']+'\n')

class qwt(Package):
    src     = 'http://downloads.sourceforge.net/qwt/qwt-6.1.3.tar.bz2',
    chksum  = '90ec21bc42f7fae270482e1a0df3bc79cb10e5c7',
    patches = 'patches/qwt'

    def configure(self):

        installDir = self.env['INSTALL_DIR']

        # Wipe old installation, otherwise qwt refuses to install
        cmd = ['rm', '-vf'] + glob(P.join(installDir, 'lib/', 'libqwt.*'))
        self.helper(*cmd)

        cmd = [installDir + '/bin/qmake','-spec']
        if self.arch.os == 'osx':
            cmd.append(P.join(installDir,'mkspecs','macx-clang'))
        else:
            cmd.append(P.join(installDir,'mkspecs','linux-g++'))
        self.helper(*cmd)

        # Turn of designer option in config file
        config_path = 'qwtconfig.pri'
        self.helper('sed', '-ibak', '-e',
                    's/QWT_CONFIG     += QwtDesigner/#QWT_CONFIG     += QwtDesigner/g',
                    config_path)

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

class jpeg(Package):
    src     = 'http://www.ijg.org/files/jpegsrc.v8d.tar.gz'
    chksum  = 'f080b2fffc7581f7d19b968092ba9ebc234556ff'
    patches = 'patches/jpeg8'

    def configure(self):
        super(jpeg, self).configure(enable=('shared',), disable=('static',))

class png(Package):
    src    = 'http://downloads.sourceforge.net/libpng/libpng-1.6.24.tar.gz'
    chksum = 'bdd5a59136c6b1e4cc94de12268122796e24036a'

    def configure(self):
        super(png,self).configure(disable='static', 
                                  other=['--with-zlib-prefix='+self.env['INSTALL_DIR']])

class cspice(Package):
    # Note: Version 66 has been released which incorporates the dsk library!
    # This will break when they release a new version BECAUSE THEY USE UNVERSIONED TARBALLS.
    PLATFORM = dict(
        linux64 = dict(
            src    = 'ftp://naif.jpl.nasa.gov/pub/naif/toolkit/C/PC_Linux_GCC_64bit/packages/cspice.tar.Z',
            chksum = 'bb1bee61522e4fac18b68364362270b4eb2f3fd8', # N0065
            ),
        osx64   = dict(
            src    = 'ftp://naif.jpl.nasa.gov/pub/naif/toolkit/C/MacIntel_OSX_AppleC_64bit/packages/cspice.tar.Z',
            chksum = 'ec3fd214facf14f72908c11cc865d4c8579baf3d', # N0066
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

class dsk(Package):
    # TODO: This library has been folded into cspice and is no longer available!
    # This will break when they release a new version BECAUSE THEY USE UNVERSIONED TARBALLS.
    PLATFORM = dict(
        linux64 = dict(
            src    = 'ftp://naif.jpl.nasa.gov/pub/naif/misc/alpha_dsk/C/PC_Linux_GCC_64bit/packages/alpha_dsk_c.tar.Z',

            chksum = '01f258d3233ba7cb7025df012b56b02a14611643',
            ),
        osx64   = dict(
            src    = 'ftp://naif.jpl.nasa.gov/pub/naif/misc/alpha_dsk/C/MacIntel_OSX_AppleC_64bit/packages/alpha_dsk_c.tar.Z',
            chksum = 'd574fe46fcb3a12c0c64d982503c383fd6f2b355',
            ),
        )

    def __init__(self, env):
        super(dsk, self).__init__(env)
        self.pkgname += '_' + self.arch.osbits
        self.src    = self.PLATFORM[self.arch.osbits]['src']
        self.chksum = self.PLATFORM[self.arch.osbits]['chksum']
        if self.arch.os == "osx":
            self.patches = 'patches/dsk_osx'
        else:
            self.patches = 'patches/dsk_linux'
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
        cmd = ['cp', '-vf'] + glob(P.join(self.workdir, 'src', 'dsklib_c', '*.h')) + [d]
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
    src = 'https://github.com/google/protobuf/releases/download/v2.6.1/protobuf-2.6.1.tar.bz2'
    chksum = '6421ee86d8fb4e39f21f56991daa892a3e8d314b'
    @stage
    def configure(self):
        
        # Our builtin curl, which we need for xerces, does not have
        # ssl and cannot be used here.  So try every curl we can find
        # in the path, hoping one works.
        success = False
        curl_paths = program_paths("curl")
        for curl_path in curl_paths:
            curl_dir=os.path.dirname(curl_path)
            self.env['PATH'] = curl_dir + ':' + self.env['PATH']  # change the path for this package
            try:
                print("Trying to use: " + curl_path)
                self.helper('./autogen.sh')
                super(protobuf, self).configure(disable=('static'), 
                    other=(['cflags="-stdlib=libc++"' 'cxxflags="-stdlib=libc++"', 'linkflags="-stdlib=libc++"']))
                success=True
                break
            except Exception, e:
                print("Bad version of curl.")
                print(str(e))

        if not success:
            raise PackageError(self, 'Could not find a good curl to use.')
            
class suitesparse(Package):
    src = 'http://faculty.cse.tamu.edu/davis/SuiteSparse/SuiteSparse-4.2.1.tar.gz'
    chksum = '2fec3bf93314bd14cbb7470c0a2c294988096ed6'

    # Note: Currently this is archive only. They don't have the option
    # of using shared (probably for performance reasons). If we want
    # shared, we'll have make then a build system.

    @stage
    def configure(self):
        pass

    @stage
    def install(self):
        inc = P.join(self.env['INSTALL_DIR'],'include')
        lib = P.join(self.env['INSTALL_DIR'],'lib')
        self.helper('make','install',
                    'INSTALL_INCLUDE=' + inc,
                    'INSTALL_LIB=' + lib
                    )

class osg3(CMakePackage):
    src = 'http://trac.openscenegraph.org/downloads/developer_releases/OpenSceneGraph-3.2.0.zip'
    chksum = 'c20891862b5876983d180fc4a3d3cfb2b4a3375c'
    patches = 'patches/osg3'

    def configure(self):
        other_flags = ['-DBUILD_OSG_APPLICATIONS=ON', '-DCMAKE_VERBOSE_MAKEFILE=ON', '-DOSG_USE_QT=OFF', '-DBUILD_DOCUMENTATION=OFF']
        if self.arch.os == 'osx':
            other_flags.extend(['-DOSG_DEFAULT_IMAGE_PLUGIN_FOR_OSX=imageio','-DOSG_WINDOWING_SYSTEM=Cocoa'])
        super(osg3, self).configure(
            with_='GDAL GLUT JPEG OpenEXR PNG ZLIB'.split(),
            without='CURL QuickTime CoreVideo QTKit COLLADA FBX FFmpeg FLTK FOX FreeType GIFLIB Inventor ITK Jasper LibVNCServer OpenAL OpenVRML OurDCMTK Performer Qt3 Qt4 SDL TIFF wxWidgets Xine XUL RSVG NVTT DirectInput GtkGL Poppler-glib GTA'.split(),
            other=other_flags)


class flann(GITPackage, CMakePackage):
    src = 'https://github.com/mariusmuja/flann.git'
    chksum = 'b8a442f'

    @stage
    def configure(self):
        super(flann, self).configure(other=['-DBUILD_C_BINDINGS=OFF','-DBUILD_MATLAB_BINDINGS=OFF','-DBUILD_PYTHON_BINDINGS=OFF','-DBUILD_CUDA_LIB=OFF','-DUSE_MPI=OFF','-DUSE_OPENMP=OFF'])

    @stage
    def install(self):
        super(flann, self).install()
        cmd = ['rm' ] +glob(P.join(self.env['INSTALL_DIR'], 'lib', 'libflann*.a'))
        self.helper(*cmd)

class eigen(CMakePackage):
    src = 'http://bitbucket.org/eigen/eigen/get/3.2.5.tar.bz2'
    chksum = 'aa4667f0b134f5688c5dff5f03335d9a19aa9b3d'

    def configure(self):
        super(eigen, self).configure(other=[
            '-DBoost_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include','boost-'+boost.version),
            '-DBoost_LIBRARY_DIRS=' + P.join(self.env['INSTALL_DIR'],'lib'),
            '-DCMAKE_BUILD_TYPE=RelWithDebInfo'
            ])

class glog(GITPackage, CMakePackage):
    src     = 'https://github.com/google/glog.git'
    chksum  = '0472b91' 
    def configure(self):
        ext = lib_ext(self.arch.os)
        if self.arch.os == 'osx':
            other_flags = []#'CFLAGS=-m64', 'CXXFLAGS=-m64',]
        else:
            other_flags = []

        other_flags += ['-DGFLAGS_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include/gflags'),
                        '-DGFLAGS_LIBRARY=' + P.join(self.env['INSTALL_DIR'],'lib/libgflags'+ext),
                        '-DBUILD_SHARED_LIBS=ON']

        super(glog, self).configure(other = other_flags)

class ceres(CMakePackage):
    src = 'http://ceres-solver.org/ceres-solver-1.11.0.tar.gz'
    chksum = '5e8683bfb410b1ba8b8204eeb0ec1fba009fb2d0'

    def configure(self):

        ext = lib_ext(self.arch.os)
        super(ceres, self).configure(other=[
            '-DEIGEN_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include/eigen3'),
            '-DBoost_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include','boost-'+boost.version),
            '-DBoost_LIBRARY_DIRS=' + P.join(self.env['INSTALL_DIR'],'lib'),
            '-DGFLAGS_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include/gflags'),
            '-DGFLAGS_LIBRARY=' + P.join(self.env['INSTALL_DIR'],'lib/libgflags'+ext),
            '-DGLOG_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include'),
            '-DGLOG_LIBRARY=' + P.join(self.env['INSTALL_DIR'],'lib/libglog'+ext),
            '-DCMAKE_VERBOSE_MAKEFILE=ON', '-DSHARED_LIBS=ON', '-DMINIGLOG=OFF',
            '-DSUITESPARSE=ON', '-DLAPACK=ON',
            '-DLIB_SUFFIX=', '-DBUILD_EXAMPLES=OFF', '-DBUILD_SHARED_LIBS=ON', '-DBUILD_TESTING=OFF'
            ])

class libnabo(GITPackage, CMakePackage):
    src = 'https://github.com/ethz-asl/libnabo.git'
    patches = 'patches/libnabo'
    chksum = '2df86e0'

    def configure(self):

        installDir = self.env['INSTALL_DIR']
        
        # Remove python bindings, tests, and examples
        self.helper('sed', '-ibak', '-e', 's/add_subdirectory(python)//g', '-e', 's/add_subdirectory(tests)//g', '-e', 's/add_subdirectory(examples)//g', 'CMakeLists.txt')
        options = [
            '-DCMAKE_CXX_FLAGS=-g -O3',
            '-DCMAKE_PREFIX_PATH=' + installDir,
            '-DEIGEN_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include/eigen3'),
            '-DBoost_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include',
                                            'boost-'+boost.version),
            '-DBoost_LIBRARY_DIRS=' + P.join(self.env['INSTALL_DIR'],'lib'),
            '-DBoost_DIR=' + P.join(self.env['INSTALL_DIR'],'lib'),
            '-DCMAKE_VERBOSE_MAKEFILE=ON',
            '-DSHARED_LIBS=ON',
            '-DCMAKE_BUILD_TYPE=Release',
            '-DCMAKE_PREFIX_PATH=' + installDir,
            ]
        
        # Bugfix for wrong boost dir being found
        if self.arch.os == 'linux':
            options += [
                '-DBoost_DIR=' + os.getcwd() + '/settings/boost',
                '-DMY_BOOST_VERSION=' + boost.version,
                '-DMY_BOOST_DIR=' + installDir
                ]
        super(libnabo, self).configure(other=options)

class libpointmatcher(GITPackage, CMakePackage):
    src   = 'https://github.com/ethz-asl/libpointmatcher'
    #src   = 'https://github.com/oleg-alexandrov/libpointmatcher.git'
    chksum = 'bcf4b04'
    # We apply a non-trivial patch to libpointmatcher to make
    # it a bit more efficient. These changes seem to be custom
    # enough that would not make sense to be merged upstream.
    patches = 'patches/libpointmatcher'

    # A patch can be re-generated with
    # f=patches/libpointmatcher/0001_custom_lib_changes.patch 
    # git diff hash1 hash2 > $f 
    # perl -pi -e "s# (a|b)/# #g" $f
    # perl -pi -e "s#--- pointmatcher#--- libpointmatcher/pointmatcher#g" $f
    # perl -pi -e "s#\+\+\+ pointmatcher#+++ libpointmatcher/pointmatcher#g" $f

    def configure(self):
        installDir = self.env['INSTALL_DIR']

        # Ensure we use the header files from the just fetched code,
        # rather than its older version in the install dir.
        curr_include = '-I' + self.workdir + '/pointmatcher'
        self.env['CPPFLAGS'] = curr_include + ' ' + self.env['CPPFLAGS']
        curr_include = '-I' + self.workdir
        self.env['CPPFLAGS'] = curr_include + ' ' + self.env['CPPFLAGS']

        # bugfix for lunokhod2
        boost_dir = P.join(installDir,'include','boost-'+boost.version)
        self.env['CXXFLAGS'] += ' -I' + boost_dir

        # OSX clang does not support fopenmp as of 10.11
        ## Use OpenMP to speed up a bit the calculation.
        #self.env['CPPFLAGS'] += ' -fopenmp'

        options = [
            '-DCMAKE_CXX_FLAGS=-g -O3 -I' + boost_dir,
            '-DBoost_INCLUDE_DIR=' + boost_dir,
            '-DBoost_LIBRARY_DIRS=' + P.join(installDir,'lib'),
            '-DEIGEN_INCLUDE_DIR=' + P.join(installDir,'include/eigen3'),
            '-DCMAKE_VERBOSE_MAKEFILE=ON',
            '-DCMAKE_PREFIX_PATH=' + installDir,
            '-DSHARED_LIBS=ON',
            '-DUSE_SYSTEM_YAML_CPP=OFF', # Use the yaml code included with LPM
            '-DCMAKE_BUILD_TYPE=Release'
            ]
        # Bugfix for lunokhod2. This has problems on Mac OSX 10.6.
        if self.arch.os == 'linux':
            options += [
                '-DBoost_DIR=' + os.getcwd() + '/settings/boost',
                '-DMY_BOOST_VERSION=' + boost.version,
                '-DMY_BOOST_DIR=' + installDir
                ]
        super(libpointmatcher, self).configure(other=options)

# We would like to fetch this very source code. This is used
# in the nightly builds and regressions.
class binarybuilder(GITPackage):
    src     = 'https://github.com/NeoGeographyToolkit/BinaryBuilder.git'
    def configure(self): pass

    @stage
    def compile(self, cwd=None): pass

    @stage
    def install(self): pass

class opencv(CMakePackage):
    src     = 'https://github.com/opencv/opencv/archive/3.1.0.tar.gz'
    chksum  = '6bbe804d2b5de17cff73a5f56aa025e8b1e7f1fd'
    #patches = 'patches/opencv'

    def configure(self):
        # Help OpenCV finds the libraries it needs to link to
        # - Turn off a lot of OpenCV 3rd party stuff we don't need to cut down on the size.
        # - We had to turn some of it back on to get the calibration sample to compile.
        self.env['LDFLAGS'] += ' -Wl,-rpath -Wl,%(INSTALL_DIR)s/lib -ljpeg -ltiff -lpng' % self.env

        # Manually fetch the contributor tarball - Needed for SIFT etc
        print(self.env['BUILD_DIR'])
        tar_path     = os.path.join(self.env['BUILD_DIR'], 'opencv/opencv-3.1.0/opencv_contrib.tar.gz')
        contrib_path = os.path.join(self.env['BUILD_DIR'], 'opencv/opencv-3.1.0/opencv_contrib-3.1.0/modules')
        get('https://github.com/opencv/opencv_contrib/archive/3.1.0.tar.gz', tar_path)
        # Unpack the contributor tarball
        cmd = 'tar -xf ' + tar_path + ' -C ' +  os.path.join(self.env['BUILD_DIR'], 'opencv/opencv-3.1.0')
        os.system(cmd)

        ## Manually fetch this required file        
        #print(self.env['BUILD_DIR'])
        #ipp_tar_path = os.path.join(self.env['BUILD_DIR'], 
        #  'opencv/opencv-3.1.0/3rdparty/ippicv/downloads/linux-808b791a6eac9ed78d32a7666804320e/ippicv_linux_20151201.tgz')
        #print(ipp_tar_path)
        #cmd = 'wget https://github.com/opencv/opencv_3rdparty/blob/ippicv/master_20151201/ippicv/ippicv_linux_20151201.tgz ' +                ipp_tar_path
        #self.helper(cmd)

        options_list = ['-DBUILD_opencv_apps=OFF',
                        '-DBUILD_opencv_video=ON',
                        '-DBUILD_opencv_ts=OFF',
                        '-DBUILD_opencv_videostab=OFF',
                        '-DBUILD_opencv_java=OFF',
                        '-DBUILD_opencv_highgui=ON',
                        '-DBUILD_opencv_adas=OFF',
                        '-DBUILD_opencv_bgsegm=OFF',
                        '-DBUILD_opencv_bioinspired=OFF',
                        '-DBUILD_opencv_ccalib=OFF',
                        '-DBUILD_opencv_cvv=OFF',
                        '-DBUILD_opencv_datasets=OFF',
                        '-DBUILD_opencv_datasettools=OFF',
                        '-DBUILD_opencv_face=OFF',
                        '-DBUILD_opencv_latentsvm=OFF',
                        '-DBUILD_opencv_line_descriptor=OFF',
                        '-DBUILD_opencv_matlab=OFF',
                        '-DBUILD_opencv_optflow=OFF',
                        '-DBUILD_opencv_reg=ON',
                        '-DBUILD_opencv_rgbd=OFF',
                        '-DBUILD_opencv_saliency=OFF',
                        '-DBUILD_opencv_surface_matching=ON',
                        '-DBUILD_opencv_text=OFF',
                        '-DBUILD_opencv_tracking=OFF',
                        '-DBUILD_opencv_ximgproc=ON',
                        '-DBUILD_opencv_xobjdetect=ON',
                        '-DBUILD_opencv_xphoto=ON',
                        '-DBUILD_opencv_fuzzy=OFF',
                        '-DBUILD_opencv_dnn=OFF',
                        '-DBUILD_opencv_python2=OFF',
                        '-DBUILD_opencv_python3=OFF',
                        '-DINSTALL_C_EXAMPLES=OFF',
                        '-DINSTALL_PYTHON_EXAMPLES=OFF',
                        '-DWITH_FFMPEG=OFF',
                        '-DWITH_DSHOW=OFF',
                        '-DWITH_GSTREAMER=OFF',
                        '-DBUILD_ANDROID_EXAMPLES=OFF',
                        '-DBUILD_DOCS=OFF',
                        '-DBUILD_TESTS=OFF',
                        '-DBUILD_PERF_TESTS=OFF',
                        '-DBUILD_EXAMPLES=OFF',
                        '-DBUILD_WITH_DEBUG_INFO=OFF',
                        '-DWITH_JASPER=OFF',
                        '-DWITH_JPEG=OFF',
                        '-DWITH_PNG=OFF',
                        '-DWITH_QT=OFF',
                        '-DWITH_TIFF=OFF',
                        '-DWITH_OPENEXR=OFF',
                        '-DWITH_CUDA=OFF',
                        '-DWITH_OPENGL=OFF',
                        '-DWITH_OPENCLAMDFFT=OFF',
                        '-DWITH_OPENCLAMDBLAS=OFF',
                        '-DWITH_OPENCL=OFF',
                        '-DWITH_GPHOTO2=OFF',
                        '-DWITH_V4L=OFF',
                        '-DWITH_VTK=OFF',
                        '-DWITH_LIBV4L=OFF',
                        '-DOPENCV_EXTRA_MODULES_PATH='+contrib_path,
                        '-DWITH_IPP=OFF'] # TODO: Re-enable this to get more speed!  Needs some help installing.

        super(opencv, self).configure( other=options_list )

class gflags(CMakePackage):
    src     = 'https://github.com/gflags/gflags/archive/v2.1.2.tar.gz'
    chksum  = '8bdbade9d041339dc14b4ab426e2354a5af38478'
    def configure(self):
        options = ['-DCMAKE_CXX_FLAGS=-fPIC', 
                   '-DBUILD_SHARED_LIBS=ON',
                   '-DBUILD_STATIC_LIBS=OFF',
                   '-DINSTALL_HEADERS=ON'
                   '-DGFLAGS_BUILD_SHARED_LIBS=ON']
        super(gflags, self).configure(other=options)

class imagemagick(Package):
    src     = 'http://downloads.sourceforge.net/project/imagemagick/old-sources/6.x/6.8/ImageMagick-6.8.6-10.tar.gz'
    chksum  = '6ea9dfc1042bb2057f8aa08e81e18c0c83451109'

    # Turn off lzma to simplify linking
    def configure(self):
        super(imagemagick, self).configure(without = ['lzma'])


class theia(GITPackage, CMakePackage):
    src     = 'https://github.com/sweeneychris/TheiaSfM.git'
    chksum  = '231f597'
    patches = 'patches/theia'

    @stage
    def configure(self):

        # Need this to avoid looking into the old installed version of
        # theia's include in build_asp/install/include
        curr_include = '-I' + self.workdir + '/src -I' + self.workdir + '/include '
        self.env['CPPFLAGS'] = curr_include + ' ' + self.env['CPPFLAGS']

        ext = lib_ext(self.arch.os)
        options = ['-DGFLAGS_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include/gflags'),
                   '-DGFLAGS_LIBRARY=' + P.join(self.env['INSTALL_DIR'],'lib/libgflags'+ext),
                   '-DGLOG_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include'),
                   '-DGLOG_LIBRARY=' + P.join(self.env['INSTALL_DIR'],'lib/libglog'+ext),
                   '-DENABLE_TESTING=OFF',
                   '-DBUILD_DOCUMENTATION=OFF']

        super(theia, self).configure(other=options)

class xz(Package):
    src     = 'http://tukaani.org/xz/xz-5.2.2.tar.gz'
    chksum  = '14663612422ab61386673be78fbb2556f50a1f08'

