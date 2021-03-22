#!/usr/bin/env python

from __future__ import print_function
import os, shutil
import os.path as P
import re, sys
from glob import glob
import subprocess
from BinaryBuilder import CMakePackage, GITPackage, Package, stage, warn, \
     PackageError, HelperError, SVNPackage, Apps, write_vw_config, write_asp_config, \
     replace_line_in_file, run, get, program_paths, get_platform, find_file, get_cores
from BinaryDist import lib_ext, which

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
    src     = 'https://github.com/Kitware/CMake/releases/download/v3.14.5/cmake-3.14.5.tar.gz'
    chksum  = 'a4c021c4fa91e812b87d9c88fdd047ead4201a2f'

    def __init__(self, env):
        super(cmake, self).__init__(env)

        #if self.arch.os == 'linux':
        #    # Bugfix, skip using ccache
        #    self.env['CXX']='g++'
        #    self.env['CC']='gcc'
            
        self.env['LDFLAGS'] += ' -Wl,-rpath -Wl,%(INSTALL_DIR)s/lib' % self.env
                
    def configure(self):
        opts = ['--system-curl', '--parallel=%d' % get_cores() ]
        super(cmake, self).configure(other = opts)

    def compile(self):
        cmd = ['gmake',  '-j%d' % get_cores() ]
        self.helper(*cmd)

    # cmake pollutes the doc folder
    @stage
    def install(self):
        super(cmake, self).install()
        cmd = ['rm', '-vrf'] + glob(P.join( self.env['INSTALL_DIR'], 'doc', 'cmake*' ))
        self.helper(*cmd)

class chrpath(Package):
    src     = 'http://ftp.debian.org/debian/pool/main/c/chrpath/chrpath_0.16.orig.tar.gz'
    chksum  = '174bb38c899229f4c928734b20e730f61191795a'
    # chrpath pollutes the doc folder
    @stage
    def install(self):
        super(chrpath, self).install()
        cmd = ['rm', '-vrf'] + glob(P.join( self.env['INSTALL_DIR'], 'doc', 'chrpath*' ))
        self.helper(*cmd)

class bzip2(Package):
    src     = 'https://downloads.sourceforge.net/project/bzip2/bzip2-1.0.6.tar.gz'
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
    src     = 'https://launchpad.net/pbzip2/1.1/1.1.6/+download/pbzip2-1.1.6.tar.gz'
    chksum  = '46cbdcf95b06e72be576d3bd12643de4aa27af5f'

    def configure(self): pass
    def compile(self):
        # Force it to use our compiler and flags
        self.helper('sed','-ibak','-e','s# g++# %s#g' % self.env['CXX'],
                    'Makefile');
        cflags = 'CFLAGS = -I' + P.join(self.env['INSTALL_DIR'], 'include') + \
                 ' -L' + P.join(self.env['INSTALL_DIR'], 'lib') + ' ' + self.env['CFLAGS'] + ' '
        self.helper('sed','-ibak','-e','s#CFLAGS = #%s#g' % cflags, 'Makefile')
        self.helper('sed','-ibak','-e','s#LDFLAGS =#LDFLAGS = %s#g' % self.env['LDFLAGS'],
                    'Makefile')
        super(pbzip2, self).compile()
    def install(self):
        # Copy just the things we need.
        cmd = ['cp', '-vf', P.join(self.workdir, 'pbzip2'),
               P.join(self.env['INSTALL_DIR'], 'bin')]
        self.helper(*cmd)

class parallel(Package):
    src     = 'http://ftp.gnu.org/gnu/parallel/parallel-20170722.tar.bz2'
    chksum  = '98bbaa8df35e0d6050ae76d6cb7d8a2e9e26ab8d'

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
        asp_deps_dir = self.env['ASP_DEPS_DIR']
        self.env['LDFLAGS'] += ' -Wl,-rpath -Wl,%s/lib -L%s/lib' % (asp_deps_dir, asp_deps_dir)
        super(openjpeg2, self).configure(other=[
            '-DCMAKE_CXX_FLAGS=-O3',
            '-DCMAKE_C_FLAGS=-O3',
            '-DBUILD_SHARED_LIBS=ON',
            '-DCMAKE_VERBOSE_MAKEFILE=ON',
            ])

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
        super(libgeotiff, self).configure( other=[
            '-DCMAKE_CXX_FLAGS=-O3',
            '-DCMAKE_C_FLAGS=-O3',
            '-DCMAKE_VERBOSE_MAKEFILE=ON',
            '-DBUILD_SHARED_LIBS=ON',
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
        asp_deps_dir = self.env['ASP_DEPS_DIR']
        self.env['LDFLAGS'] += ' -Wl,-rpath -Wl,%s/lib -L%s/lib -ljpeg -lproj' % (asp_deps_dir, asp_deps_dir)
        # TODO: This may no longer be necessary.
        self.helper('sed', '-ibak', '-e', 's/libproj./libproj.0./g', 'ogr/ogrct.cpp')

        w = ['threads', 'libtiff', 'geotiff=' + self.env['ASP_DEPS_DIR'],
             'jpeg=' + self.env['ASP_DEPS_DIR'],
             'png', 'zlib', 'pam',
             'openjpeg=' + self.env['ASP_DEPS_DIR'],
             'geos=' + self.env['ASP_DEPS_DIR'],
             'liblzma='+ self.env['ASP_DEPS_DIR'],
             'curl']
        wo = \
            '''bsb cfitsio dods-root dwg-plt dwgdirect ecw epsilon expat expat-inc expat-lib fme
               gif grass hdf4 hdf5 idb ingres jasper jp2mrsid kakadu libgrass
               macosx-framework mrsid msg mysql netcdf oci oci-include oci-lib odbc ogdi pcidsk
               pcraster perl pg php pymoddir python sde sde-version spatialite sqlite3
               static-proj4 xerces xerces-inc xerces-lib libiconv-prefix libiconv xml2 pcre
               freexl json-c kea libkml'''.split()

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

    @stage
    def configure(self):
    
        # Download some data files
        # - There appear to be duplicate files in the extra tarballs???
        base_dir = os.path.join(self.env['BUILD_DIR'], 'proj')
        os.system('mkdir -p ' + base_dir)
        main_tar_path    = os.path.join(base_dir, 'main_grids.tar.gz'   )
        na_tar_path      = os.path.join(base_dir, 'na_grids.tar.gz'     )
        oceania_tar_path = os.path.join(base_dir, 'oceania_grids.tar.gz')
        europe_tar_path  = os.path.join(base_dir, 'europe_grids.tar.gz' )
        get('https://github.com/OSGeo/proj-datumgrid/archive/1.7.tar.gz',               main_tar_path   )
        #get('https://github.com/OSGeo/proj-datumgrid/archive/north-america-1.0.tar.gz', na_tar_path     )
        #get('https://github.com/OSGeo/proj-datumgrid/archive/oceania-1.0.tar.gz',       oceania_tar_path)
        #get('https://github.com/OSGeo/proj-datumgrid/archive/europe-1.0.tar.gz',        europe_tar_path )

        # Extract the data files
        os.system('tar -xf ' + main_tar_path    + ' -C ' + base_dir)
        #os.system('tar -xf ' + na_tar_path      + ' -C ' + base_dir)
        #os.system('tar -xf ' + oceania_tar_path + ' -C ' + base_dir)
        #os.system('tar -xf ' + europe_tar_path  + ' -C ' + base_dir)

        super(proj,self).configure(disable='static', without='jni')   
    
    @stage
    def install(self):
        super(proj, self).install()
        # Copy extra files which are needed by libgeotiff to compile.
        cmd = ['cp', '-vf'] + glob(P.join(self.workdir, 'src/*.h')) + \
              [P.join(self.env['INSTALL_DIR'], 'include')]
        self.helper(*cmd)
        
        # Copy grid files to the share folder
        unpack_folder = os.path.join(self.env['BUILD_DIR'], 'proj', 'proj-datumgrid-1.7')
        share_folder  = os.path.join(self.env['INSTALL_DIR'], 'share', 'proj')

        # First delete some extra files we don't want
        os.system('rm -rf ' + os.path.join(share_folder, 'europe',        '.github'))
        os.system('rm -rf ' + os.path.join(share_folder, 'north-america', '.github'))

        # Larger files are skipped to keep the ASP tarball size down.
        grid_list = ('alaska europe null prvi stlrnc  WI BETA2007.gsb conus FL ntf_r93.gsb nzgd2kgrid0005.gsb stpaul  WO' +
                     ' egm96_15.gtx hawaii MD ntv1_can.dat stgeorge TN').split()
        for f in grid_list:
            try:
                shutil.move(os.path.join(unpack_folder, f), share_folder)
            except:
                pass # Skip existing files

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
    src     = 'http://curl.haxx.se/download/curl-7.57.0.tar.bz2'
    chksum  = '7f47469324bf22cc9ffd1d3a201aa3c76ab626b8'

    @stage
    def configure(self):
        w = ['zlib='+self.env['INSTALL_DIR'], 'ssl='+self.env['INSTALL_DIR']]
        wo = 'libidn '.split() # Turn this off so this is not auto-included, our packages don't need it.
        super(curl,self).configure(
            with_=w, without=wo, disable=['static','ldap','ldaps'])

class liblas(CMakePackage):
    src     = 'http://download.osgeo.org/liblas/libLAS-1.8.1.tar.bz2'
    chksum  = 'e30c1efb3df4bcdc7119d7c42638e7a01b14f236'
    patches = 'patches/liblas'

    @stage
    def configure(self):
        # Remove the pedantic flag. Latest boost is not compliant.
        self.helper('sed', '-ibak', '-e', 's/-pedantic//g', 'CMakeLists.txt')
        asp_deps_dir = self.env['ASP_DEPS_DIR']

        # bugfix for linux
        asp_deps_dir = self.env['ASP_DEPS_DIR']
        boost_dir = P.join(asp_deps_dir,'include')
        self.env['CXXFLAGS'] += ' -I' + boost_dir
        self.env['LDFLAGS'] += ' -pthread -Wl,-rpath -Wl,%s/lib -L%s/lib -llzma -pthread' % (asp_deps_dir, asp_deps_dir)

        ext = lib_ext(self.arch.os)
        super(liblas, self).configure(other=[
            '-DCMAKE_CXX_FLAGS=-O3',
            '-DCMAKE_C_FLAGS=-O3',
            '-DBoost_INCLUDE_DIR=' + boost_dir,
            #'-DBoost_INCLUDE_DIR='  + P.join(self.env['INSTALL_DIR'],
            #'include','boost-'+boost.version),            
            #'-DBoost_LIBRARY_DIRS=' + P.join(self.env['INSTALL_DIR'],'lib'),
            '-DBoost_LIBRARY_DIRS=' + P.join(asp_deps_dir,'lib'),
            '-DWITH_LASZIP=true',
            '-DLASZIP_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include'),
            '-DWITH_GDAL=true',
            '-DGDAL_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include'),
            '-DWITH_GEOTIFF=true',
            '-DGEOTIFF_INCLUDE_DIR=' + P.join(asp_deps_dir,'include'),
            '-DTIFF_INCLUDE_DIR=' + P.join(asp_deps_dir,'include'),
            '-DTIFF_LIBRARY_RELEASE=' + P.join(asp_deps_dir,'lib', 'libtiff'+ ext),
            '-DZLIB_LIBRARY_RELEASE=' + P.join(asp_deps_dir,'lib', 'libz'+ ext),
            #'-DGEOTIFF_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include'),
            #'-DBoost_USE_STATIC_LIBS=OFF',
            '-DBUILD_SHARED_LIBS=ON',
            '-DBoost_NO_BOOST_CMAKE=OFF',
            '-DCMAKE_VERBOSE_MAKEFILE=ON',
            '-DBoost_DEBUG=ON',
            '-DBoost_DETAILED_FAILURE_MSG=ON',
            '-DBoost_NO_SYSTEM_PATHS=ON' # don't use system boost
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
    @stage
    def configure(self):
        asp_deps_dir = self.env['ASP_DEPS_DIR']

        # bugfix for linux
        asp_deps_dir = self.env['ASP_DEPS_DIR']
        boost_dir = P.join(asp_deps_dir,'include')
        self.env['CXXFLAGS'] += ' -I' + boost_dir + ' -pthread'

        ext = lib_ext(self.arch.os)
        super(laszip, self).configure(other=[
            '-DCMAKE_CXX_FLAGS=-O3',
            '-DCMAKE_C_FLAGS=-O3',
            '-DBoost_INCLUDE_DIR=' + boost_dir,
            #'-DBoost_INCLUDE_DIR='  + P.join(self.env['INSTALL_DIR'],
            #'include','boost-'+boost.version),            
            #'-DBoost_LIBRARY_DIRS=' + P.join(self.env['INSTALL_DIR'],'lib'),
            '-DBoost_LIBRARY_DIRS=' + P.join(asp_deps_dir,'lib'),
            '-DWITH_LASZIP=true',
            '-DLASZIP_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include'),
            '-DWITH_GDAL=true',
            '-DGDAL_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include'),
            '-DWITH_GEOTIFF=true',
            '-DGEOTIFF_INCLUDE_DIR=' + P.join(asp_deps_dir,'include'),
            '-DTIFF_INCLUDE_DIR=' + P.join(asp_deps_dir,'include'),
            '-DTIFF_LIBRARY_RELEASE=' + P.join(asp_deps_dir,'lib', 'libtiff'+ ext),
            '-DZLIB_LIBRARY_RELEASE=' + P.join(asp_deps_dir,'lib', 'libz'+ ext),
            #'-DGEOTIFF_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include'),
            #'-DBoost_USE_STATIC_LIBS=OFF',
            '-DBUILD_SHARED_LIBS=ON',
            '-DBoost_NO_BOOST_CMAKE=OFF',
            '-DCMAKE_VERBOSE_MAKEFILE=ON',
            '-DBoost_DEBUG=ON',
            '-DBoost_DETAILED_FAILURE_MSG=ON',
            '-DBoost_NO_SYSTEM_PATHS=ON' # don't use system boost
            ])

class geoid(Package):
    src     = 'https://github.com/NeoGeographyToolkit/StereoPipeline/releases/download/geoid1.0/geoids.tgz'
    chksum  = 'e6e3961d6a84e10b4c49039b9a84098d57bd2206'

    @stage
    def configure(self): pass

    def compile(self):
        self.helper(self.env['GFORTRAN'], '-c','-fPIC','interp_2p5min.f')
        if self.arch.os == 'osx':
            flag = '-dynamiclib'
            ext  = '.dylib'
        else:
            flag = '-shared'
            ext  = '.so'
        
        self.helper(self.env['GFORTRAN'], flag, '-o', 'libegm2008'+ext, 'interp_2p5min.o')

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
    # This must be synched up with ISIS's hdf5 package in miniconda.
    # TODO: Could use just that if our whitelist was able to pick things
    # from Minconda's directory.
    src     = 'https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-1.8/hdf5-1.8.18/src/hdf5-1.8.18.tar.bz2'
    chksum  = 'd7e008cbfcf5cb6913b5327a81bbcaf34cc9436d'
    def configure(self):
        super(hdf5, self).configure(enable=('cxx'), disable = ['static'])

class armadillo(CMakePackage):
    src    = 'http://sourceforge.net/projects/arma/files/armadillo-9.100.5.tar.xz'
    chksum = 'c4f9bf2c0d0650ba7814ae746e0da088211accfd'
    patches = 'patches/armadillo'

    @stage
    def configure(self):
        super(armadillo, self).configure(other=['-DDETECT_HDF5=OFF'])

# Build our copy of the ISIS code...
class isis(GITPackage, CMakePackage):
    src = 'https://github.com/USGS-Astrogeology/ISIS3.git'
    chksum = 'f6beda24b408a6e352f3a8aeb87505874c555691'  # version 4.1
    patches = 'patches/isis'

    def __init__(self, env):
        super(isis, self).__init__(env)

    @stage
    def configure(self):
        # The code is stored one folder down
        self.workdir = os.path.join(self.workdir, 'isis')

        # Follow the ISIS convention of where the build should be
        self.builddir = os.path.join(self.workdir, '../build')

        self.env['CONDA_PREFIX'] = self.env['ASP_DEPS_DIR']

        # Do not configure as we will fetch the binaries with conda,
        # we need only the headers
        return 

        ext = lib_ext(self.arch.os)
        super(isis, self).configure(other= [
            '-DCMAKE_FIND_ROOT_PATH=' + self.env['ASP_DEPS_DIR'] + ':' \
            + self.env['INSTALL_DIR'],
            '-DCMAKE_CXX_COMPILER=' + which(self.env['CXX']),
            '-DCMAKE_C_COMPILER=' + which(self.env['CC']),
            '-DCMAKE_CXX_FLAGS=-O3 -std=c++11',
            '-DCMAKE_C_FLAGS=-O3',
            '-DPNG_LIBRARY=' + P.join(self.env['ASP_DEPS_DIR'],'lib/libpng' + ext),
            '-DCSPICE_LIBRARY=' + P.join(self.env['ASP_DEPS_DIR'],'lib/libcspice' + ext),
            '-DX11_LIBRARY=' + P.join(self.env['ASP_DEPS_DIR'],'lib/libX11' + ext),
            '-Dpybindings=Off',
            '-DJP2KFLAG=OFF',
            '-DbuildTests=OFF',
            '-DBUILD_TESTING=OFF',
            '-GNinja',
            '-DCMAKE_VERBOSE_MAKEFILE=ON',
            ])

    @stage
    def compile(self):
        # Do not build as we will fetch the binaries with conda,
        # so we need only the headers (one day they will upload those too)
        return

        self.env['ISISROOT'] = self.builddir # Per the ISIS documentation
        super(isis, self).compile()
        cmd = ('ninja', 'install', '-v')
        self.helper(*cmd, cwd=self.builddir)

    @stage
    def install(self):
        # Copy all header files. Some are repeated, but hoping
        # for the best. This is a temporary solution.

        dest_dir = P.join(self.env['INSTALL_DIR'],'include/isis')
        cmd = ['mkdir','-p', dest_dir]
        self.helper(*cmd)

        src_dir = os.path.join(self.workdir, 'src')
        if not os.path.isdir(src_dir):
            raise Exception("Cannot find directory: " + src_dir)

        header_files = []
        print("Copying header files in " + src_dir + " to " + dest_dir)
        for root, dirs, files in os.walk(src_dir):
            for file_name in files:
                if file_name.endswith(".h"):
                    header_file = os.path.join(root, file_name)
                    shutil.copy(header_file, dest_dir)

# USGS Community sensor model
# TODO: Make it install in lib and not in lib64 like everything else.
class usgscsm(GITPackage, CMakePackage):
    src = 'https://github.com/USGS-Astrogeology/usgscsm'
    chksum = 'a53f9cfe30f595809917013c277698a413c32443'

    def unpack(self):
        super(usgscsm, self).unpack()
        cmd = ('git', 'submodule', 'update', '--init', '--recursive')
        self.helper(*cmd)

    def configure(self):
        #         # The code is stored one folder down
        # self.helper('./autogen')
        #self.workdir = os.path.join(self.workdir, 'usgscsm')
        super(usgscsm, self).configure(other=[
            '-DCMAKE_VERBOSE_MAKEFILE=ON',
            '-DCMAKE_CXX_FLAGS=-O3',
            '-DCMAKE_C_FLAGS=-O3',
            ]) #-DNinja

class stereopipeline(GITPackage, CMakePackage):
    src     = 'https://github.com/NeoGeographyToolkit/StereoPipeline.git'
    def configure(self):

        ## Skip config in fast mode if config file exists
        #config_file = P.join(self.workdir, 'config.options')
        #if self.fast and os.path.isfile(config_file): return

        #self.helper('./autogen')

        asp_deps_dir = self.env['ASP_DEPS_DIR']
        boost_dir = P.join(asp_deps_dir,'include')

        # TODO: Just remove the bad arguments!
        if self.arch.os == 'osx':
            self.env['LDFLAGS'] = '-Wl,-headerpad_max_install_names'
        else:
            self.env['LDFLAGS'] += ' -Wl,-O1 -Wl,--enable-new-dtags -Wl,--hash-style=both -m64'

        #use_env_flags = False # TODO: What is this?
        prefix        = self.env['INSTALL_DIR']
        installdir    = prefix
        #vw_build      = prefix
        #arch          = self.arch
        #write_asp_config(use_env_flags, prefix, installdir, vw_build,
        #                 arch, geoid, config_file)
        
        #super(stereopipeline, self).configure(
        #    other   = ['docdir=%s/doc' % prefix],
        #    without = ['clapack', 'slapack', 'tcmalloc'],
        #    disable = ['pkg_paths_default', 'static', 'qt-qmake'],
        #    enable  = ['debug=ignore', 'optimize=ignore']
        #    )
        super(stereopipeline, self).configure(other=[
            '-DBINARYBUILDER_INSTALL_DIR=' + installdir,
            '-DASP_DEPS_DIR=' + asp_deps_dir,
            '-DVISIONWORKBENCH_INSTALL_DIR=' + installdir,
            '-DCMAKE_VERBOSE_MAKEFILE=ON',
            ])

    @stage
    def compile(self):
        super(stereopipeline, self).compile()
        # Run unit tests. If the ISIS env vars are not set,
        # the ISIS-related tests will be skipped.
        # Make install must happen before 'make check',
        # otherwise the old installed library is linked.
        #cmd = ('make', 'install')
        #self.helper(*cmd)
        super(stereopipeline, self).install()

        if self.fast or int(self.env['SKIP_TESTS']) == 1:
            print("Skipping tests in fast mode.")
        else:
            cmd = ('make', 'gtest_all')
            buildDir = os.path.join(self.workdir, 'build_binarybuilder')
            self.helper(*cmd, cwd=buildDir)

    @stage
    def install(self):
        pass # We installed during the compile step so skip this.

class visionworkbench(GITPackage, CMakePackage):
    src = 'https://github.com/visionworkbench/visionworkbench.git'

    def __init__(self,env):
        super(visionworkbench,self).__init__(env)

    @stage
    def configure(self):
        ## Skip config in fast mode if config file exists
        #config_file  = P.join(self.workdir, 'config.options')
        #if self.fast and os.path.isfile(config_file): return

        #self.helper('./autogen')

        asp_deps_dir = self.env['ASP_DEPS_DIR']

        # TODO: Just remove the bad arguments!
        if self.arch.os == 'osx':
            self.env['LDFLAGS'] = '-Wl,-headerpad_max_install_names'
        else:
            self.env['LDFLAGS'] += ' -Wl,-O1 -Wl,--enable-new-dtags -Wl,--hash-style=both -m64'

        arch         = self.arch
        installdir   = self.env['INSTALL_DIR']
        super(visionworkbench, self).configure(other=[
            '-DASP_DEPS_DIR=' + asp_deps_dir,
            '-DBINARYBUILDER_INSTALL_DIR=' + installdir,
            '-DCMAKE_VERBOSE_MAKEFILE=ON',
            # -DVW_ENABLE_SSE=0 #  on pfe
            ])

    @stage
    def compile(self):
        super(visionworkbench, self).compile()
        # Run unit tests
        # Make install must happen before 'make check',
        # otherwise the old installed library is linked.
        #cmd = ('make', 'install')
        #self.helper(*cmd)
        super(visionworkbench, self).install()

        if self.fast or int(self.env['SKIP_TESTS']) == 1:
            print("Skipping tests in fast mode.")
        else:
            cmd = ('make', 'gtest_all')
            buildDir = os.path.join(self.workdir, 'build_binarybuilder')
            self.helper(*cmd, cwd=buildDir)

    @stage
    def install(self):
        pass # We installed during the compile step so skip this.


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
    version = '1_67' # variable is used in class liblas, libnabo, etc.
    src     = 'http://downloads.sourceforge.net/boost/boost_' + version + '_0.tar.bz2'
    chksum  = '694ae3f4f899d1a80eb7a3b31b33be73c423c1ae'
    patches = 'patches/boost'

    def __init__(self, env):
        super(boost, self).__init__(env)
        self.env['NO_BZIP2'] = '1'
        #self.env['NO_ZLIB']  = '1'
        if self.arch.os == 'osx':
            self.env['PATH'] = '/usr/bin:' + self.env['PATH'] # to use the right libtool

    @stage
    def configure(self):
        with open(P.join(self.workdir, 'user-config.jam'), 'w') as f:
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
            '--without-mpi', '--without-python', '--without-wave',  'stage',
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
    # This version must be synched up with what ISIS needs.
    # Their conda packages provide geos for Linux but not for Mac.
    src = 'http://download.osgeo.org/geos/geos-3.5.1.tar.bz2'
    chksum = '83373542335c2f20c22d5420ba01d99f645f0c61'

    def __init__(self, env):
        super(geos, self).__init__(env)
        #if self.arch.os == 'linux':
        #    # Bugfix for SuSE, skip using ccache
        #self.env['CXX']='g++'
        #self.env['CC']='gcc'

    def configure(self):
        super(geos, self).configure(disable=('python', 'ruby', 'static'))

class superlu(Package):
    # TODO: This may need some tweaks.
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
            asp_deps_dir = self.env['ASP_DEPS_DIR']
            self.env['LDFLAGS'] += ' -Wl,-rpath -Wl,%s/lib -L%s/lib' % (asp_deps_dir, asp_deps_dir)
            blas = glob(P.join(self.env['ASP_DEPS_DIR'],'lib','libblas.dylib*'))[0]
            #blas = '"-framework vecLib"'
        else:
            blas = glob(P.join(self.env['ASP_DEPS_DIR'],'lib','libblas.so*'))[0]

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
                       'extern void    check_tempv',
                       'double, double, double ', # Hit the lines following the PrintPerf line
                       'complex, complex, complex ',
                       'float, float, float ',
                       'doublecomplex, doublecomplex, doublecomplex '
                      ]
        # Use sed to add // before every instance of these targets in these files
        for f in file_list:
            full_path = P.join(self.env['INSTALL_DIR'],'include', 'superlu', f)
            for target in target_list: 
                cmd = ['sed', '-i', '-e', 
                       "s#"+target+"#//"+target+"#g",
                       full_path]
                self.helper(*cmd)


class gmm(Package):
    src     = 'http://download-mirror.savannah.gnu.org/releases/getfem/stable/gmm-4.2.tar.gz'
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
    src    = 'http://archive.apache.org/dist/xerces/c/3/sources/xerces-c-3.1.3.tar.xz'
    chksum = '44aa39f8b9ccbfcaf58771634761cbea1084e8f1'

    @stage
    def configure(self):
        super(xercesc,self).configure(with_=['curl=%s' % glob(P.join(self.env['INSTALL_DIR'],'lib','libcurl.*'))[0],
                                             'icu=no'],
                                      disable = ['static', 'msgloader-iconv', 'msgloader-icu', 'network'])

class qt(Package):
    src     = 'http://download.qt.io/official_releases/qt/5.6/5.6.3/single/qt-everywhere-opensource-src-5.6.3.tar.xz'
    chksum  = 'ca7a752bff079337876ca6ab70b0dec17b47e70f' #SHA-1 Hash
    patches = 'patches/qt'
    #patch_level = '-p0'

    @stage
    def configure(self):

        # Modify the min OSX version
        config_path = self.workdir + '/qtbase/mkspecs/macx-clang/qmake.conf'
        self.helper('sed', '-ibak', '-e',
                    's/QMAKE_MACOSX_DEPLOYMENT_TARGET = 10.7/QMAKE_MACOSX_DEPLOYMENT_TARGET = 10.12/g',
                    config_path)

        ## The default confs override our compiler choices.
        cmd = ("./configure -c++std c++11  -opensource -confirm-license -release -nomake tools -nomake examples  "
               "-prefix %(INSTALL_DIR)s  "
               "-no-openssl -no-libjpeg  -no-libpng -no-cups -no-openvg -no-sql-psql -no-pulseaudio "
               "-skip qt3d "
               "-skip qtactiveqt "
               "-skip qtandroidextras "
               "-skip qtconnectivity "
               "-skip qtlocation "
               "-skip qtmacextras "
               "-skip qtquickcontrols "
               "-skip qtquickcontrols2 "
               "-skip qtsensors "
               "-skip qtserialbus "
               "-skip qtserialport "
               "-skip qtwayland "
               "-skip qtwebchannel "
               "-skip qtwebengine "
               "-skip qtwebview "
               "-skip qtwinextras "
               ) % self.env

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
    #src    = 'https://www.ijg.org/files/jpegsrc.v8d.tar.gz' # does not work
    src     = 'https://download.videolan.org/contrib/jpeg/jpegsrc.v8d.tar.gz' 
    chksum  = 'f080b2fffc7581f7d19b968092ba9ebc234556ff'
    patches = 'patches/jpeg8'

    def configure(self):
        super(jpeg, self).configure(enable=('shared',), disable=('static',))

class png(Package):
    src    = 'http://downloads.sourceforge.net/libpng/libpng-1.6.37.tar.gz'
    chksum = 'bdd5a59136c6b1e4cc94de12268122796e24036a'  # fix here

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
            except Exception as e:
                print("Bad version of curl.")
                print(str(e))

        if not success:
            raise PackageError(self, 'Could not find a good curl to use.')
            
class suitesparse(Package):
    src = 'http://faculty.cse.tamu.edu/davis/SuiteSparse/SuiteSparse-4.4.5.tar.gz'
    chksum = '7666883423f56de760546a8be8795d5ac9d66c19'
    patches = 'patches/suitesparse'
    
    # TODO: This build fails unless run manually from the build folder!

    # Note: Currently this is archive only. They don't have the option
    # of using shared (probably for performance reasons). If we want
    # shared, we'll have make then a build system.

    def __init__(self, env):
        super(suitesparse, self).__init__(env)

        #if self.arch.os == 'linux':
        #    # Bugfix, skip using ccache
        #    self.env['CXX']='g++'
        #    self.env['CC']='gcc'
    @stage
    def configure(self):
        if self.arch.os == 'osx':
            # Swap the config file
            self.helper('mv', 'SuiteSparse_config/SuiteSparse_config_Mac.mk',
                              'SuiteSparse_config/SuiteSparse_config.mk')

    @stage
    def install(self):
        inc = P.join(self.env['INSTALL_DIR'],'include')
        lib = P.join(self.env['INSTALL_DIR'],'lib')
        self.helper('make','install',
                    'INSTALL_INCLUDE=' + inc,
                    'INSTALL_LIB=' + lib
                    )

class osg3(CMakePackage):
    src = 'https://github.com/openscenegraph/OpenSceneGraph/archive/OpenSceneGraph-3.2.0.zip'
    chksum = '5435de08cd7f67691f6be7cfa0d36b80f04bcb34'
    patches = 'patches/osg3'

    def configure(self):
        other_flags = [
            '-DCMAKE_CXX_FLAGS=-O3',
            '-DCMAKE_C_FLAGS=-O3',
            '-DBUILD_OSG_APPLICATIONS=ON',
            '-DCMAKE_VERBOSE_MAKEFILE=ON',
            '-DOSG_USE_QT=OFF',
            '-DBUILD_DOCUMENTATION=OFF']
        if self.arch.os == 'osx':
            other_flags.extend([
                '-DOSG_DEFAULT_IMAGE_PLUGIN_FOR_OSX=imageio',
                '-DOSG_WINDOWING_SYSTEM=Cocoa'
                ])
        super(osg3, self).configure(
            with_='GDAL GLUT JPEG OpenEXR PNG ZLIB'.split(),
            without='CURL QuickTime CoreVideo QTKit COLLADA FBX FFmpeg FLTK FOX FreeType GIFLIB Inventor ITK Jasper LibVNCServer OpenAL OpenVRML OurDCMTK Performer Qt3 Qt4 SDL TIFF wxWidgets Xine XUL RSVG NVTT DirectInput GtkGL Poppler-glib GTA'.split(),
            other=other_flags)

class flann(GITPackage, CMakePackage):
    src = 'https://github.com/mariusmuja/flann.git'
    chksum = 'b8a442f'
    patches = 'patches/flann'

    def __init__(self, env):
        super(flann, self).__init__(env)

        #if self.arch.os == 'linux':
        #    # Bugfix, skip using ccache
        #    self.env['CXX']='g++'
        #    self.env['CC']='gcc'
            
    @stage
    def configure(self):
        self.helper('touch', P.join(self.workdir,'src/cpp/empty.cpp'))
        super(flann, self).configure(other=[
            '-DCMAKE_CXX_FLAGS=-O3',
            '-DCMAKE_C_FLAGS=-O3',
            '-DBUILD_C_BINDINGS=OFF',
            '-DBUILD_MATLAB_BINDINGS=OFF',
            '-DBUILD_PYTHON_BINDINGS=OFF',
            '-DBUILD_CUDA_LIB=OFF',
            '-DUSE_MPI=OFF',
            '-DUSE_OPENMP=OFF',
            '-DCMAKE_VERBOSE_MAKEFILE=ON',
            ])

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

class glog(CMakePackage):
    src     = 'https://github.com/google/glog/archive/v0.3.5.tar.gz'
    chksum  = '61067502c5f9769d111ea1ee3f74e6ddf0a5f9cc'

    def configure(self):
        ext = lib_ext(self.arch.os)
        if self.arch.os == 'osx':
            other_flags = []#'CFLAGS=-m64', 'CXXFLAGS=-m64',]
        else:
            other_flags = []

        other_flags += [
            '-DCMAKE_CXX_FLAGS=-O3',
            '-DCMAKE_C_FLAGS=-O3',
            '-DGFLAGS_INCLUDE_DIR=' + P.join(self.env['INSTALL_DIR'],'include/gflags'),
            '-DGFLAGS_LIBRARY=' + P.join(self.env['INSTALL_DIR'],'lib/libgflags'+ext),
            '-DBUILD_SHARED_LIBS=ON',
            '-DCMAKE_VERBOSE_MAKEFILE=ON',
            ]

        super(glog, self).configure(other = other_flags)

class ceres(CMakePackage):
    src = 'http://ceres-solver.org/ceres-solver-1.14.0.tar.gz'
    chksum = '57b61c28d67ca3eb814c5605120ae614be465b7c'

    def configure(self):
        ext = lib_ext(self.arch.os)
        asp_deps_dir = self.env['ASP_DEPS_DIR']
        install_dir = self.env['INSTALL_DIR']
        super(ceres, self).configure(other=[
            '-DCMAKE_FIND_ROOT_PATH=' + self.env['ASP_DEPS_DIR'],
            '-DCMAKE_CXX_FLAGS=-O3',
            '-DCMAKE_C_FLAGS=-O3',
            '-DEIGEN_INCLUDE_DIR='   + P.join(asp_deps_dir,'include/eigen3'),
            '-DGFLAGS_INCLUDE_DIR='  + P.join(asp_deps_dir,'include/gflags'),
            '-DGFLAGS_LIBRARY='      + P.join(asp_deps_dir,'lib/libgflags'+ext),
            '-DGLOG_INCLUDE_DIR='    + P.join(asp_deps_dir,'include/glog'),
            '-DGLOG_LIBRARY='        + P.join(asp_deps_dir,'lib/libglog'+ext),
            '-DCMAKE_INSTALL_RPATH=' + P.join(asp_deps_dir,'lib') + ':' \
                                     + P.join(install_dir,'lib'),
            '-DCMAKE_VERBOSE_MAKEFILE=ON',
            '-DSHARED_LIBS=ON',
            '-DMINIGLOG=OFF',
            '-DSUITESPARSE=ON',
            '-DLAPACK=ON',
            '-DLIB_SUFFIX=',
            '-DBUILD_EXAMPLES=OFF',
            '-DBUILD_SHARED_LIBS=ON',
            '-DBUILD_TESTING=OFF'
            ])

class libnabo(GITPackage, CMakePackage):
    src = 'https://github.com/ethz-asl/libnabo.git'
    patches = 'patches/libnabo'
    chksum = '2df86e0'

    def configure(self):

        installDir = self.env['INSTALL_DIR']
        asp_deps_dir = self.env['ASP_DEPS_DIR']
        
        # Remove python bindings, tests, and examples
        self.helper('sed', '-ibak', '-e', 's/add_subdirectory(python)//g', '-e', 's/add_subdirectory(tests)//g', '-e', 's/add_subdirectory(examples)//g', 'CMakeLists.txt')

        options = [
            '-DCMAKE_CXX_FLAGS=-O3 -std=c++11',
            '-DCMAKE_C_FLAGS=-O3',
            '-DCMAKE_FIND_ROOT_PATH=' + self.env['ASP_DEPS_DIR'] + ':' + self.env['INSTALL_DIR'],
            '-DCMAKE_PREFIX_PATH=' + installDir,
            '-DEIGEN_INCLUDE_DIR=' + P.join(asp_deps_dir,'include/eigen3'),
            '-DBoost_INCLUDE_DIR=' + P.join(asp_deps_dir,'include'),
            #'-DBoost_LIBRARY_DIRS=' + P.join(self.env['INSTALL_DIR'],'lib'),
            #'-DBoost_DIR=' + P.join(self.env['INSTALL_DIR'],'lib'),
            '-DSHARED_LIBS=ON',
            '-DCMAKE_BUILD_TYPE=Release',
            '-DCMAKE_PREFIX_PATH=' + installDir,
            '-DCMAKE_VERBOSE_MAKEFILE=ON',
            ]
        
        # Bugfix for wrong boost dir being found
        #if self.arch.os == 'linux':
        #    options += [
        #        '-DBoost_DIR=' + os.getcwd() + '/settings/boost',
        #        '-DMY_BOOST_VERSION=' + boost.version,
        #        '-DMY_BOOST_DIR=' + installDir
        #        ]
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
        asp_deps_dir = self.env['ASP_DEPS_DIR']

        # Turn off the unit tests which don't build on OSX10.12
        self.helper('sed', '-ibak', '-e',
                    's/add_subdirectory(utest)/#add_subdirectory(utest)/g',
                    'CMakeLists.txt')

        # Ensure we use the header files from the just fetched code,
        # rather than its older version in the install dir.
        curr_include = '-I' + self.workdir + '/pointmatcher'
        self.env['CPPFLAGS'] = curr_include + ' ' + self.env['CPPFLAGS']
        curr_include = '-I' + self.workdir
        self.env['CPPFLAGS'] = curr_include + ' ' + self.env['CPPFLAGS']

        # bugfix for lunokhod2
        boost_dir = P.join(asp_deps_dir,'include')
        #boost_dir = P.join(self.env['INSTALL_DIR'], 'include','boost-'+boost.version)
        #self.env['CXXFLAGS'] += ' -I' + boost_dir

        # OSX clang does not support fopenmp as of 10.11
        if self.arch.os == 'linux':
            self.env['CPPFLAGS'] += ' -fopenmp'

        options = [
            '-DCMAKE_CXX_FLAGS=-O3 -std=c++11 -I' + boost_dir,
            '-DCMAKE_C_FLAGS=-O3',
            '-DBoost_INCLUDE_DIR='  + boost_dir,            
            '-DCMAKE_FIND_ROOT_PATH=' + self.env['ASP_DEPS_DIR'] + ':' + self.env['INSTALL_DIR'],
            #'-DBoost_LIBRARY_DIRS=' + P.join(installDir,'lib'),
            '-DEIGEN_INCLUDE_DIR=' + P.join(asp_deps_dir,'include/eigen3'),
            '-DCMAKE_VERBOSE_MAKEFILE=ON',
            '-DCMAKE_PREFIX_PATH=' + installDir,
            '-DSHARED_LIBS=ON',
            '-DUSE_SYSTEM_YAML_CPP=OFF', # Use the yaml code included with LPM
            '-DCMAKE_BUILD_TYPE=Release',
            '-DBoost_NO_BOOST_CMAKE=OFF',
            '-DCMAKE_VERBOSE_MAKEFILE=ON',
            '-DBoost_DEBUG=ON',
            '-DBoost_DETAILED_FAILURE_MSG=ON',
            '-DCMAKE_CXX_COMPILER_ARCHITECTURE_ID=x64',
            '-DBoost_NO_SYSTEM_PATHS=ON' # don't use system boost
            ]
        # Bugfix for lunokhod2. This has problems on Mac OSX 10.6.
        #if self.arch.os == 'linux':
        #    options += [
        #        '-DBoost_DIR=' + os.getcwd() + '/settings/boost',
        #        '-DMY_BOOST_VERSION=' + boost.version,
        #        '-DMY_BOOST_DIR=' + installDir
        #        ]
        super(libpointmatcher, self).configure(other=options)

# FastGlobalRegistration
class fgr(GITPackage, CMakePackage):
    src   = 'https://github.com/IntelVCL/FastGlobalRegistration.git'
    chksum = 'bfcb9f9'

    @stage
    def configure(self):
        asp_deps_dir = self.env['ASP_DEPS_DIR']
        options = [
            '-DCMAKE_CXX_FLAGS='
            + '-I' + P.join(asp_deps_dir,'include') + ' '
            + '-I' + P.join(asp_deps_dir,'include/eigen3') + ' '
            + '-L' + P.join(asp_deps_dir,'lib') + ' -lflann_cpp'
            + ' -O3',
            '-DCMAKE_C_FLAGS=-O3',
            '-DFastGlobalRegistration_LINK_MODE=SHARED'
            ]
        self.workdir = P.join(self.workdir, 'source')
        super(fgr, self).configure(other=options)
        
    @stage
    def install(self):
        # Install the header file
        destDir = P.join(self.env['INSTALL_DIR'], 'include', 'FastGlobalRegistration')
        self.helper('mkdir', '-p', destDir)
        self.helper('cp', P.join(self.workdir, 'FastGlobalRegistration/app.h'), destDir)

        # Install the library
        if self.arch.os == 'osx':
            ext  = '.dylib'
        else:
            ext  = '.so'
        lib = P.join(self.builddir, 'FastGlobalRegistration', 'libFastGlobalRegistrationLib'+ext)
        self.helper('cp', lib,  P.join(self.env['INSTALL_DIR'], 'lib'))
        
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
    if get_platform().os == 'osx':
        src     = 'https://github.com/opencv/opencv/archive/3.3.1.tar.gz'
        chksum  = '79dba99090a5c48308fe91db8336ec2931e06b57'
    else:
        src     = 'https://github.com/opencv/opencv/archive/3.1.0.tar.gz'
        chksum  = '31dd36c5d59c76f6b7982a64d6ffc0993736d7ea'
    #patches = 'patches/opencv'

    # NOTE: OSX 10.12 seems to require a newer version (3.3.1 works) but that does not work on CentOS 6.
    #  - To get it to build on CentOS 6, a newer CMake is needed (with SSL/HTTPS support) to perform
    #    the file fetching steps in the OpenCV 3.3.1 CMake files.  Unfortunately there is some
    #    weird problem with the newer CMake build and OpenCV which causes it to not find its header files.
    #    for now the OSX build is abandoned and CMake/OpenCV are reverted to their old versions.
    #    Maybe all that is needed is an intermediate version of CMake.

    # TODO: Trying a workaround but clean this up in the future =)

    def configure(self):
        # Help OpenCV finds the libraries it needs to link to
        # - Turn off a lot of OpenCV 3rd party stuff we don't need to cut down on the size.
        self.env['LDFLAGS'] += ' -Wl,-rpath -Wl,%(INSTALL_DIR)s/lib -ljpeg -ltiff -lpng' % self.env

        # Manually fetch the contributor tarball - Needed for SIFT etc
        if self.arch.os == 'osx':
            tar_path     = os.path.join(self.env['BUILD_DIR'], 'opencv/opencv-3.3.1/opencv_contrib.tar.gz')
            contrib_path = os.path.join(self.env['BUILD_DIR'], 'opencv/opencv-3.3.1/opencv_contrib-3.3.1/modules')
        else:
            tar_path     = os.path.join(self.env['BUILD_DIR'], 'opencv/opencv-3.1.0/opencv_contrib.tar.gz')
            contrib_path = os.path.join(self.env['BUILD_DIR'], 'opencv/opencv-3.1.0/opencv_contrib-3.1.0/modules')

        # The centos VM is having trouble downloading files properly so we first check if we
        #  have an already downloaded file available to unpack.
        if os.path.exists('/home/pipeline/projects/3.1.0.tar.gz'):
            if self.arch.os == 'osx':
                os.system('cp  /home/pipeline/projects/3.3.1.tar.gz ' + tar_path)
            else:
                os.system('cp  /home/pipeline/projects/3.1.0.tar.gz ' + tar_path)
        else:
            if self.arch.os == 'osx':
                get('https://github.com/opencv/opencv_contrib/archive/3.3.1.tar.gz', tar_path)
            else:
                get('https://github.com/opencv/opencv_contrib/archive/3.1.0.tar.gz', tar_path)

        # Unpack the contributor tarball
        if self.arch.os == 'osx':
            cmd = 'tar -xf ' + tar_path + ' -C ' +  os.path.join(self.env['BUILD_DIR'], 'opencv/opencv-3.3.1')
        else:
            cmd = 'tar -xf ' + tar_path + ' -C ' +  os.path.join(self.env['BUILD_DIR'], 'opencv/opencv-3.1.0')
        os.system(cmd)

        # TODO: In Version 3.3.1 this contributor module does not have a flag to turn it off so just remove it!
        #os.system('rm -rf ' + os.path.join(contrib_path, 'dnn_modern'))

        ## Manually fetch this required file        
        #print(self.env['BUILD_DIR'])
        #ipp_tar_path = os.path.join(self.env['BUILD_DIR'], 
        #  'opencv/opencv-3.1.0/3rdparty/ippicv/downloads/linux-808b791a6eac9ed78d32a7666804320e/ippicv_linux_20151201.tgz')
        #print(ipp_tar_path)
        #cmd = 'wget https://github.com/opencv/opencv_3rdparty/blob/ippicv/master_20151201/ippicv/ippicv_linux_20151201.tgz ' +                ipp_tar_path
        #self.helper(cmd)

        # The following lists are up to date for version 3.3.1

        # Add a flag like: -DBUILD_opencv_<name>=ON
        build_on_list  = ['video', 'highgui', 'reg', 'surface_matching', 'ximgproc', 'xobjdetect',
                          'xphoto']
        # Add a flag like: -DBUILD_opencv_<name>=OFF
        build_off_list = ['apps', 'ts', 'videostab', 'java', 'adas',
                          'bgsegm', 'bioinspired', 'ccalib', 'cvv', 'datasets', 'datasettools',
                          'face', 'latentsvm', 'line_descriptor', 'matlab', 'optflow',
                          'rgbd', 'saliency', 'text', 'tracking', 'fuzzy', 'dnn',
                          'python2', 'python3', 'aruco', 'cnn_3dobj', 'dnns_easily_fooled',
                          'dpm', 'freetype', 'ovis', 'plot', 'sfm', 'stereo', 'structured_light',
                          'dnn_modern']

        # Add a flag like: -DWITH_<name>=ON
        with_on_list = ['EIGEN', 'JPEG']
        # Add a flag like: -DWITH_<name>=OFF
        with_off_list = ['JASPER', 'PNG', 'QT', 'TIFF', 'OPENEXR', 'CUDA', 'OPENGL',
                         'OPENCLAMDFFT', 'OPENCLAMDBLAS', 'OPENCL', 'GPHOTO2', 'V4L', 'VTK',
                         'LIBV4L', 'WEBP', 'ITT', 'IPP']

        # Other options
        eigen_include_path = os.path.join(self.env['INSTALL_DIR'],'include/eigen3')
        options_list = ['-DINSTALL_C_EXAMPLES=OFF',
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
                        '-DENABLE_PRECOMPILED_HEADERS=OFF',
                        '-DEIGEN_INCLUDE_PATH='+eigen_include_path,
                        '-DOPENCV_EXTRA_MODULES_PATH='+contrib_path
                        ] # TODO: Re-enable this to get more speed!  Needs some help installing.

        for item in build_on_list:
            options_list.append('-DBUILD_opencv_'+item+'=ON')
        for item in build_off_list:
            options_list.append('-DBUILD_opencv_'+item+'=OFF')

        super(opencv, self).configure( other=options_list, with_=with_on_list, without=with_off_list )

class gflags(CMakePackage):
    src     = 'https://github.com/gflags/gflags/archive/v2.2.1.tar.gz'
    chksum  = 'b1c82261c8b9c87fb2fb5de6bdf70121ad1cca58'

    def configure(self):
        options = [
            '-DCMAKE_CXX_FLAGS=-O3 -fPIC',
            '-DCMAKE_C_FLAGS=-O3',
            '-DBUILD_SHARED_LIBS=ON',
            '-DBUILD_STATIC_LIBS=OFF',
            '-DINSTALL_HEADERS=ON'
            '-DGFLAGS_BUILD_SHARED_LIBS=ON',
            '-DCMAKE_VERBOSE_MAKEFILE=ON'
            ]
        super(gflags, self).configure(other=options)

class imagemagick(Package):
    src     = 'http://downloads.sourceforge.net/project/imagemagick/old-sources/6.x/6.8/ImageMagick-6.8.6-10.tar.gz'
    chksum  = '6ea9dfc1042bb2057f8aa08e81e18c0c83451109'

    def __init__(self, env):
        super(imagemagick, self).__init__(env)
        asp_deps_dir = self.env['ASP_DEPS_DIR']
        # temporary include dirs
        self.env['CFLAGS'] = '-I' + asp_deps_dir + '/include ' + self.env['CFLAGS']
        self.env['CXXFLAGS'] = '-I' + asp_deps_dir + '/include ' + self.env['CXXFLAGS']
        self.env['LDFLAGS'] += ' -Wl,-rpath -Wl,%s/lib -L%s/lib -ljpeg -pthread' % (asp_deps_dir, asp_deps_dir)

    def configure(self):
        # Turn off some packages to simplify linking
        super(imagemagick, self).configure(without = [
            'lzma', 'fontconfig', 'freetype', 'pango', 'webp', 'openexr', 'xml', 'jbig', 'fftw'
            ])

class theia(GITPackage, CMakePackage):
    src     = 'git@github.com:oleg-alexandrov/TheiaSfM.git'
    chksum  = 'f5d93f5'

    @stage
    def configure(self):

        #if self.arch.os == 'linux':
        #    # Bugfix, skip using ccache
        #    self.env['CXX']='g++'
        #    self.env['CC']='gcc'
            
        # Need this to avoid looking into the old installed version of
        # theia's include in build_asp/install/include
        curr_include = '-I' + self.workdir + '/src -I' + self.workdir + '/include '
        self.env['CPPFLAGS'] = curr_include + ' ' + self.env['CPPFLAGS']

        # Per https://github.com/sweeneychris/TheiaSfM/issues/208.
        # Also note the patch in patches/theia/0005-fix_flann.patch
        # self.helper('touch', P.join(self.workdir,'libraries/flann/src/cpp/empty.cpp'))

        ext = lib_ext(self.arch.os)
        options = [
            '-DCMAKE_CXX_FLAGS=-O3 -fPIC -L' + self.env['ASP_DEPS_DIR'] + '/lib',
            '-DCMAKE_FIND_ROOT_PATH=' + self.env['ASP_DEPS_DIR'] + ':' + self.env['INSTALL_DIR'],
            '-DCMAKE_C_FLAGS=-O3 -fPIC',
            '-DGFLAGS_INCLUDE_DIR=' + P.join(self.env['ASP_DEPS_DIR'],'include/gflags'),
            '-DGFLAGS_LIBRARY=' + P.join(self.env['ASP_DEPS_DIR'],'lib/libgflags'+ext),
            '-DGLOG_INCLUDE_DIR=' + P.join(self.env['ASP_DEPS_DIR'],'include'),
            '-DGLOG_LIBRARY=' + P.join(self.env['ASP_DEPS_DIR'],'lib/libglog'+ext),
            '-DPNG_LIBRARY_RELEASE=' + P.join(self.env['ASP_DEPS_DIR'],'lib/libpng' + ext),
            '-DBUILD_SHARED_LIBS=ON', '-DBUILD_TESTING=OFF',
            '-DBUILD_DOCUMENTATION=OFF',
            '-DCMAKE_VERBOSE_MAKEFILE=ON',
            '-DTBB_LIBRARIES=' + self.env['ASP_DEPS_DIR'] + '/lib/libtbb.so.2',
            '-DTBB_MALLOC_LIB=' + self.env['ASP_DEPS_DIR'] + '/lib/libtbbmalloc.so.2',
            ]
        
        super(theia, self).configure(other=options)

        # Remove this linker tag which just breaks things        
        output_dir = P.join(self.env['BUILD_DIR'], self.pkgname)
        build_dir  = P.join(output_dir, self.pkgname + '-git', 'build')
        cmd = "find "+build_dir+" -name link.txt -exec sed -i -e 's#-lgflags-shared##g' {} \;"
        print(cmd)
        os.system(cmd)


class xz(Package):
    # This must be synched up with ISIS's miniconda's liblzma.5.2.4
    src     = 'http://tukaani.org/xz/xz-5.2.4.tar.gz'
    chksum  = '63ca380029597b951ce9afc6dec28f44f70bb5bd'

class bullet(CMakePackage):
    src    = 'https://github.com/bulletphysics/bullet3/archive/2.86.1.tar.gz'
    chksum = 'd0a4878ccc166902f0dcb822669d1a8e4ccc8642'

    @stage
    def configure(self):
        # The include files are with the rest of the source code
        curr_include = '-I' + self.workdir + '/src'
        self.env['CPPFLAGS'] = curr_include + ' ' + self.env['CPPFLAGS']

        self.env['MAKEOPTS'] += ''' CFLAGS="-fPIC"''' # Needed for ISIS
        
        # Turn off extra stuff
        options = ['-DCMAKE_CXX_FLAGS=-fPIC',
                   '-DCMAKE_C_FLAGS=-O3',
                   '-DBUILD_CPU_DEMOS=OFF',
                   '-DBUILD_OPENGL3_DEMOS=OFF',
                   '-DBUILD_BULLET2_DEMOS=OFF',
                   '-DBUILD_EXTRAS=OFF',
                   '-DBUILD_UNIT_TESTS=OFF']
        super(bullet, self).configure(other=options)

class embree(CMakePackage):
    src    = 'https://github.com/embree/embree/archive/v2.15.0.tar.gz'
    chksum = 'd9e9a7eb2ead012cf56847002551c83f488122f8'

    @stage
    def configure(self):

        # The include files are with the rest of the source code
        curr_include = '-I' + self.workdir + '/build'
        self.env['CPPFLAGS'] = curr_include + ' ' + self.env['CPPFLAGS']

        # Turn off extra stuff
        options = ['-DEMBREE_ISPC_SUPPORT=OFF',
                   '-DEMBREE_TUTORIALS=OFF',
                   '-DEMBREE_TASKING_SYSTEM=INTERNAL',
                   '-DEMBREE_MAX_ISA=AVX']
        super(embree, self).configure(other=options)

class nanoflann(GITPackage, CMakePackage):
    src    = 'https://github.com/jlblancoc/nanoflann.git'
    chksum = '3740943'

    # A single file header only library

    @stage
    def configure(self):
        pass

    @stage
    def compile(self):
        pass

    @stage
    def install(self):
        self.helper('cp', P.join(self.workdir,'include/nanoflann.hpp'), P.join(self.env['INSTALL_DIR'], 'include'))

class nn(GITPackage):
    src    = 'https://github.com/sakov/nn-c.git'
    chksum = '343c778'
    
    @stage
    def configure(self):
        self.workdir = os.path.join(self.workdir, 'nn')
        super(nn, self).configure()

class pcl(CMakePackage):
    src    = 'https://github.com/PointCloudLibrary/pcl/archive/pcl-1.8.1.tar.gz'
    chksum = '6813478c27566da3eb5835b384524fd775115465'
    
    @stage
    def configure(self):

        include_dir = P.join(self.env['INSTALL_DIR'],'include')

        # Include folder are spread out amoung folders at the top level =(
        folders = ['2d', 'kdtree', 'registration', 'surface',
                   'features', 'keypoints', 'sample_consensus',
                   'common', 'filters', 'search',
                   'geometry', 'ml', 'people', 'segmentation', 'tracking',
                    'cuda', 'gpu', 'octree', 'simulation', 'visualization',
                    'io', 'outofcore', 'recognition', 'stereo', 'build']
        for f in folders:
            curr_include = '-I' + P.join(self.workdir,f,'include')
            self.env['CPPFLAGS'] = curr_include + ' ' + self.env['CPPFLAGS']

        # Not being included for some reason
        curr_include = '-I' + P.join(include_dir, 'eigen3')
        self.env['CPPFLAGS'] = curr_include + ' ' + self.env['CPPFLAGS']
        boost_dir = P.join(include_dir,'boost-'+boost.version)
        self.env['CXXFLAGS'] += ' -I' + boost_dir

        # Turn off extra stuff
        options = ['-DBUILD_global_tests=OFF',
                   '-DBUILD_visualization=OFF',
                   '-DBOOST_ROOT='+P.join(self.env['INSTALL_DIR']),
                   '-DBoost_INCLUDE_DIR='+P.join(include_dir, 'boost-'+boost.version),
                   '-DBoost_LIBRARY_DIRS='+P.join(self.env['INSTALL_DIR'],'lib')]
        super(pcl, self).configure(other=options, 
                                   without=['CUDA', 'QT', 'VTK', 'QHULL', 'PCAP',
                                            'OPENGL', 'GLUT', 'LIBUSB'])

class htdp(Package):
    src    = 'http://www.ngs.noaa.gov/TOOLS/Htdp/HTDP-download.zip'
    chksum = '5ebdfda5e2cf29760727ba14ba1194daa5afd2af'
    
    @stage
    def unpack(self):
        output_dir = P.join(self.env['BUILD_DIR'], self.pkgname)

        self.remove_build(output_dir) # Throw out the old content
        os.system('mkdir -p ' + output_dir)
        self.helper('unzip', '-d', output_dir, self.tarball)     
        self.workdir = output_dir
            
    @stage
    def configure(self):
        return # Nothing to do here.
    
    @stage
    def compile(self):
        # Just compile the fortran script.
        fortran_path = find_file(self.env['GFORTRAN'], self.env['PATH'])
        cmd = fortran_path +' ' + os.path.join(self.workdir, 'htdp.f') + ' -o ' + os.path.join(self.workdir, 'htdp')
        print(cmd)
        os.system(cmd)
        
    @stage
    def install(self):
        # Copy the binary file to the libexec folder.
        libexec = P.join( self.env['INSTALL_DIR'], 'libexec' )
        self.helper('mkdir', '-p', libexec)
        cmd = ['cp', '-vf', P.join(self.workdir, 'htdp'), libexec]
        self.helper(*cmd)
        return    


    
