#!/usr/bin/env python

from __future__ import print_function

import os
import os.path as P
import re

from glob import glob
from BinaryBuilder import CMakePackage, GITPackage, Package, stage, warn, PackageError

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

class gdal(Package):
    src     = 'http://download.osgeo.org/gdal/gdal-1.8.0.tar.gz'
    chksum  = 'e5a2802933054050c6fb0b0a0e1f46b5dd195b0a'
    patches = 'patches/gdal'

    def __init__(self, env):
        super(gdal, self).__init__(env)
        j, self.env = strip_flag('-j(\d+)', 'MAKEOPTS', self.env)
        if j:
            j = int(j.group(1))
            if j > 16: j = 16
            self.env.append('MAKEOPTS', '-j%s' % j)

    def configure(self):
        w = ['threads', 'libtiff=internal', 'libgeotiff=internal', 'jpeg', 'png', 'zlib', 'pam']
        wo = \
          '''bsb cfitsio curl dods-root dwg-plt dwgdirect ecw epsilon expat expat-inc expat-lib fme
             geos gif grass hdf4 hdf5 idb ingres jasper jp2mrsid kakadu libgrass
             macosx-framework mrsid msg mysql netcdf oci oci-include oci-lib odbc ogdi pcidsk
             pcraster perl pg php pymoddir python ruby sde sde-version spatialite sqlite3
             static-proj4 xerces xerces-inc xerces-lib'''.split()

        self.helper('./autogen.sh')
        super(gdal,self).configure(with_=w, without=wo, disable='static', enable='shared')

class ilmbase(Package):
    src     = 'http://download.savannah.nongnu.org/releases/openexr/ilmbase-1.0.2.tar.gz'
    chksum  = 'fe6a910a90cde80137153e25e175e2b211beda36'
    patches = 'patches/ilmbase'

    def configure(self):
        self.env['AUTOHEADER'] = 'true'
        # XCode in snow leopard removed this flag entirely (way to go, guys)
        self.helper('sed', '-ibak', '-e', 's/-Wno-long-double//g', 'configure.ac')
        self.helper('autoreconf', '-fvi')
        super(ilmbase, self).configure(disable='static')

class openexr(Package):
    src     = 'http://download.savannah.nongnu.org/releases/openexr/openexr-1.6.1.tar.gz'
    chksum  = 'b3650e6542f0e09daadb2d467425530bc8eec333'
    patches = 'patches/openexr'

    def configure(self):
        self.env['AUTOHEADER'] = 'true'
        # XCode in snow leopard removed this flag entirely (way to go, guys)
        self.helper('sed', '-ibak', '-e', 's/-Wno-long-double//g', 'configure.ac')
        self.helper('autoreconf', '-fvi')
        super(openexr,self).configure(with_=('ilmbase-prefix=%(INSTALL_DIR)s' % self.env),
                                      disable=('ilmbasetest', 'imfexamples', 'static'))

class proj(Package):
    src     = 'http://download.osgeo.org/proj/proj-4.7.0.tar.gz'
    chksum  = 'bfe59b8dc1ea0c57e1426c37ff2b238fea66acd7'

    def configure(self):
        super(proj,self).configure(disable='static')

class curl(Package):
    src     = 'http://curl.haxx.se/download/curl-7.15.5.tar.gz'
    chksum  = '32586c893e7d9246284af38d8d0f5082e83959af'

    def configure(self):
        super(curl,self).configure(disable='static', without=['ssl','libidn'])

class stereopipeline(GITPackage):
    src     = 'http://github.com/NeoGeographyToolkit/StereoPipeline.git'
    def configure(self):
        self.helper('./autogen')

        disable_apps = 'aligndem bundleadjust demprofile geodiff isisadjustcameraerr isisadjustcnetclip plateorthoproject reconstruct results rmax2cahvor rmaxadjust stereogui'
        enable_apps  = 'bundlevis disparitydebug hsvmerge isisadjust orbitviz orthoproject point2dem point2mesh stereo mer2camera'
        disable_modules  = 'photometrytk controlnettk mpi'
        enable_modules   = 'core spiceio isisio sessions'

        noinstall_pkgs = 'spice qwt gsl geos xercesc kakadu protobuf'.split()
        install_pkgs   = 'boost vw_core vw_math vw_image vw_fileio vw_camera \
                          vw_stereo vw_cartography vw_interest_point openscenegraph flapack arbitrary_qt curl'.split()

        if self.arch.os == 'linux':
            noinstall_pkgs += ['superlu']

        w = [i + '=%(INSTALL_DIR)s'   % self.env for i in install_pkgs] \
          + [i + '=%(NOINSTALL_DIR)s' % self.env for i in noinstall_pkgs] \
          + ['isis=%s' % self.env['ISISROOT']]

        includedir = P.join(self.env['NOINSTALL_DIR'], 'include')

        with file(P.join(self.workdir, 'config.options'), 'w') as config:
            for pkg in install_pkgs + noinstall_pkgs:
                ldflags=[]
                ldflags.append('-L%s -L%s' % (self.env['ISIS3RDPARTY'], P.join(self.env['INSTALL_DIR'], 'lib')))

                if self.arch.os == 'osx':
                    ldflags.append('-F%s -F%s' % (self.env['ISIS3RDPARTY'], P.join(self.env['INSTALL_DIR'], 'lib')))

                print('PKG_%s_LDFLAGS="%s"' % (pkg.upper(), ' '.join(ldflags)), file=config)

            qt_pkgs = 'QtCore QtGui QtNetwork QtSql QtSvg QtXml QtXmlPatterns'

            if self.arch.os == 'osx':
                libload = '-framework '
            else:
                libload = '-l'

            print('QT_ARBITRARY_MODULES="%s"' % qt_pkgs, file=config)

            qt_cppflags=['-I%s' % includedir]
            qt_libs=[]

            for module in qt_pkgs.split():
                qt_cppflags.append('-I%s/%s' % (includedir, module))
                qt_libs.append('%s%s' % (libload, module))

            print('PKG_ARBITRARY_QT_CPPFLAGS="%s"' %  ' '.join(qt_cppflags), file=config)
            print('PKG_ARBITRARY_QT_LIBS="%s"' %  ' '.join(qt_libs), file=config)
            print('PKG_ARBITRARY_QT_MORE_LIBS="-lpng -lz"', file=config)

            if self.arch.os == 'linux':
                print('PKG_SUPERLU_STATIC_LIBS=%s' % glob(P.join(self.env['ISIS3RDPARTY'], 'libsuperlu*.a'))[0], file=config)
            elif self.arch.os == 'osx':
                print('HAVE_PKG_SUPERLU=no', file=config)

            print('PKG_GEOS_LIBS=-lgeos-3.2.0', file=config)

        super(stereopipeline, self).configure(
            other   = ['docdir=%s/doc' % self.env['INSTALL_DIR']],
            with_   = w,
            without = ['clapack', 'slapack'],
            disable = ['pkg_paths_default', 'static', 'qt-qmake']
                      + ['app-' + a for a in disable_apps.split()]
                      + ['module-' + a for a in disable_modules.split()],
            enable  = ['debug=ignore', 'optimize=ignore']
                      + ['app-' + a for a in enable_apps.split()]
                      + ['module-' + a for a in enable_modules.split()])

class visionworkbench(GITPackage):
    src     = 'http://github.com/visionworkbench/visionworkbench.git'

    def configure(self):
        self.helper('./autogen')

        enable_modules  = 'camera mosaic interestpoint cartography hdr stereo geometry tools bundleadjustment'.split()
        disable_modules = 'gpu plate python gui photometry'.split()
        install_pkgs = 'jpeg png gdal proj4 z ilmbase openexr boost flapack protobuf flann'.split()

        w  = [i + '=%(INSTALL_DIR)s' % self.env for i in install_pkgs]
        w.append('protobuf=%(INSTALL_DIR)s' % self.env)

        with file(P.join(self.workdir, 'config.options'), 'w') as config:
            for pkg in install_pkgs:
                print('PKG_%s_CPPFLAGS="-I%s -I%s"' % (pkg.upper(), P.join(self.env['NOINSTALL_DIR'],   'include'),
                                                                    P.join(self.env['INSTALL_DIR'], 'include')), file=config)
                print('PKG_%s_LDFLAGS="-L%s -L%s"'  % (pkg.upper(), self.env['ISIS3RDPARTY'], P.join(self.env['INSTALL_DIR'], 'lib')), file=config)
            # Specify executables we use
            print('PROTOC=%s' % (P.join(self.env['INSTALL_DIR'], 'bin', 'protoc')))

        super(visionworkbench, self).configure(with_   = w,
                                               without = ('tiff hdf cairomm zeromq rabbitmq_c tcmalloc x11 clapack slapack qt opencv cg'.split()),
                                               disable = ['pkg_paths_default','static', 'qt-qmake'] + ['module-' + a for a in disable_modules],
                                               enable  = ['debug=ignore', 'optimize=ignore', 'as-needed', 'no-undefined'] + ['module-' + a for a in enable_modules])

class lapack(Package):
    src     = 'http://www.netlib.org/lapack/lapack-3.2.1.tgz'
    chksum  = 'c75223fdef3258c461370af5d2b889d580d7f38a'
    patches = 'patches/lapack'

    def __init__(self, env):
        super(lapack, self).__init__(env)
        self.env['NOOPT_FFLAGS'] = '-O'

    def unpack(self):
        super(lapack, self).unpack()
        self.helper('cp', 'make.inc.example', 'make.inc')
        self.helper('sed', '-i',
            '-e', 's:g77:gfortran:',
            '-e', r's:LOADOPTS =:LOADOPTS = ${LDFLAGS}:',
            '-e', 's:../../blas\$(PLAT).a:-L%(ISIS3RDPARTY)s -lblas:' % self.env,
            '-e', 's:lapack\$(PLAT).a:SRC/.libs/liblapack.a:',
            'make.inc')

        self.helper('sed', '-i',
                    '-e', 's:LIBADD.*:& -L%(ISIS3RDPARTY)s -lblas:' % self.env,
                    '-e', 's:.*LDFLAGS.*::',
                    P.join('SRC', 'Makefile.am'))

        self.helper('autoreconf' , '--force' , '--verbose', '--install')


    def configure(self):
        super(lapack, self).configure(disable='static', with_='blas=-L%s -lblas' % self.env['ISIS3RDPARTY'])

class boost(Package):
    src    = 'http://downloads.sourceforge.net/boost/boost_1_39_0.tar.gz'
    chksum = 'fc0f98aea163f2edd8d74e18eafc4704d7d93d07'
    patches = 'patches/boost'

    def __init__(self, env):
        super(boost, self).__init__(env)
        self.env['NO_BZIP2'] = '1'
        self.env['NO_ZLIB']  = '1'

    @stage
    def configure(self):
        with file(P.join(self.workdir, 'user-config.jam'), 'w') as f:
            if self.arch.os == 'linux':
                toolkit = 'gcc'
            elif self.arch.os == 'osx':
                toolkit = 'darwin'

            print('variant myrelease : release : <optimization>none <debug-symbols>none ;', file=f)
            print('variant mydebug : debug : <optimization>none ;', file=f)
            args = [toolkit] + list(self.env.get(i, ' ') for i in ('CXX', 'CXXFLAGS', 'LDFLAGS'))
            print('using %s : : %s : <cxxflags>"%s" <linkflags>"%s -ldl" ;' % tuple(args), file=f)

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
            '-q', 'variant=myrelease', '--user-config=%s/user-config.jam' % self.workdir,
            '--prefix=%(INSTALL_DIR)s' % self.env, '--layout=versioned',
            'threading=multi', 'link=shared', 'runtime-link=shared',
            '--without-mpi', '--without-python', '--without-wave',
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

class gsl_headers(HeaderPackage):
    src = 'ftp://ftp.gnu.org/gnu/gsl/gsl-1.3.tar.gz',
    chksum = 'ecde676adb997adbd507a7a7974bb7f6f69f9d87',

class geos_headers(HeaderPackage):
    src = 'http://download.osgeo.org/geos/geos-3.2.0.tar.bz2',
    chksum = 'e6925763fb06fa6a7f358ede49bb89f96535b3ef',
    def configure(self):
        super(geos_headers, self).configure(disable=('python', 'ruby'))

class superlu_headers(HeaderPackage):
    src = 'http://crd.lbl.gov/~xiaoye/SuperLU/superlu_3.0.tar.gz',
    chksum = '65a35df64b01ae1e454dd793c668970a2cf41604',
    def configure(self): pass
    def install(self):
        d = P.join('%(NOINSTALL_DIR)s' % self.env, 'include', 'SRC')
        self.helper('mkdir', '-p', d)
        cmd = ['cp', '-vf'] + glob(P.join(self.workdir, 'SRC', '*.h')) + [d]
        self.helper(*cmd)

class xercesc_headers(HeaderPackage):
    src = 'http://download.nextag.com/apache//xerces/c/3/sources/xerces-c-3.1.1.tar.gz'
    chksum = '177ec838c5119df57ec77eddec9a29f7e754c8b2'

class qt_headers(HeaderPackage):
    src = 'http://get.qt.nokia.com/qt/source/qt-everywhere-opensource-src-4.6.2.tar.gz'
    chksum = '977c10b88a2230e96868edc78a9e3789c0fcbf70'
    def __init__(self, env):
        super(qt_headers, self).__init__(env)

    @stage
    def configure(self):
        args = './configure -opensource -fast -confirm-license -nomake demos -nomake examples -nomake docs -nomake tools -nomake translations'.split()
        if self.arch.os == 'osx':
            args.append('-no-framework')
        self.helper(*args)

    @stage
    def install(self):
        include = ['--include=%s' % i for i in '**/include/** *.h */'.split()]
        self.copytree(self.workdir + '/', self.env['NOINSTALL_DIR'] + '/', delete=False, args=['-m', '--copy-unsafe-links'] + include + ['--exclude=*'])

class qwt_headers(HeaderPackage):
    src = 'http://downloads.sourceforge.net/qwt/qwt-5.2.0.tar.bz2',
    chksum = '8830498b87d99d4b7e95ee643f1f7ff178204ba9',
    def configure(self): pass
    def install(self):
        cmd = ['cp', '-vf'] + glob(P.join(self.workdir, 'src', '*.h')) + [P.join('%(NOINSTALL_DIR)s' % self.env, 'include')]
        self.helper(*cmd)

class zlib(Package):
    src     = 'http://www.zlib.net/zlib-1.2.5.tar.gz'
    chksum  = '8e8b93fa5eb80df1afe5422309dca42964562d7e'

    def unpack(self):
        super(zlib, self).unpack()
        self.helper('sed', '-i',
                    r's|\<test "`\([^"]*\) 2>&1`" = ""|\1 2>/dev/null|', 'configure')

    def configure(self):
        super(zlib,self).configure(other=('--shared',))

class zlib_headers(HeaderPackage):
    src     = 'http://www.zlib.net/zlib-1.2.5.tar.gz'
    chksum  = '8e8b93fa5eb80df1afe5422309dca42964562d7e'
    def configure(self):
        super(zlib_headers,self).configure(other=['--shared'])
    def install(self):
        include_dir = P.join(self.env['NOINSTALL_DIR'], 'include')
        self.helper('mkdir', '-p', include_dir)
        self.helper('cp', '-vf', 'zlib.h', 'zconf.h', include_dir)

class jpeg(Package):
    src     = 'http://www.ijg.org/files/jpegsrc.v8a.tar.gz'
    chksum  = '78077fb22f0b526a506c21199fbca941d5c671a9'
    patches = 'patches/jpeg8'

    def configure(self):
        super(jpeg, self).configure(enable=('shared',), disable=('static',))

class jpeg_headers(HeaderPackage):
    src     = 'http://www.ijg.org/files/jpegsrc.v8a.tar.gz'
    chksum  = '78077fb22f0b526a506c21199fbca941d5c671a9'
    patches = 'patches/jpeg8'

    def configure(self):
        super(jpeg_headers, self).configure(enable=('shared',), disable=('static',))

class png(Package):
    src    = 'http://downloads.sourceforge.net/libpng/libpng-1.2.43.tar.gz'
    chksum = '44c1231c74f13b4f3e5870e039abeb35c7860a3f'

    def configure(self):
        super(png,self).configure(disable='static')

class png_headers(HeaderPackage):
    src    = 'http://downloads.sourceforge.net/libpng/libpng-1.2.43.tar.gz'
    chksum = '44c1231c74f13b4f3e5870e039abeb35c7860a3f'

class cspice_headers(HeaderPackage):
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
    )

    def __init__(self, env):
        super(cspice_headers, self).__init__(env)
        self.pkgname += '_' + self.arch.osbits
        self.src    = self.PLATFORM[self.arch.osbits]['src']
        self.chksum = self.PLATFORM[self.arch.osbits]['chksum']
    def configure(self, *args, **kw): pass
    def install(self):
        d = P.join('%(NOINSTALL_DIR)s' % self.env, 'include', 'naif')
        self.helper('mkdir', '-p', d)
        cmd = ['cp', '-vf'] + glob(P.join(self.workdir, 'include', '*.h')) + [d]
        self.helper(*cmd)

class protobuf(Package):
    src = 'http://protobuf.googlecode.com/files/protobuf-2.3.0.tar.gz'
    chksum = 'd0e7472552e5c352ed0afbb07b30dcb343c96aaf'

    def __init__(self, env):
        super(protobuf, self).__init__(env)
        if self.arch.os == 'osx':
            # This was the only way I could get it to linke 32 bit
            # mode.
            self.env.append('CC', ' '.join(["-arch %s" % i for i in self.env['OSX_ARCH'].split(';')]))
            self.env.append('CXX', ' '.join(["-arch %s" % i for i in self.env['OSX_ARCH'].split(';')]))

class isis(Package):

    ### ISIS 3.3.0 Needs:
    # geos-3.2.0
    # gsl-1.13 (1.14 and 1.15 on other platforms, hopefully backwards compat)
    # kakadu-6.3.1?
    # protobuf-2.3.0
    # qt-4.6.2
    # qwt-5.2.0
    # spice-0064
    # superlu-3.0
    # xerces-c-3.1.1

    PLATFORM = dict(
        linux64 = 'isisdist.wr.usgs.gov::x86-64_linux_RHEL/isis/',
        linux32 = 'isisdist.wr.usgs.gov::x86_linux_RHEL/isis/',
        osx32   = 'isisdist.wr.usgs.gov::x86_darwin_OSX/isis/',
    )

    def __init__(self, env):
        super(isis, self).__init__(env)
        self.pkgname  += '_' + self.arch.osbits
        self.src       = self.PLATFORM[self.arch.osbits]
        self.localcopy = P.join(env['DOWNLOAD_DIR'], 'rsync', self.pkgname)


    def _fix_dev_symlinks(self, Dir):
        if self.arch.os != 'linux':
            return

        for lib in glob(P.join(Dir, '*.so.*')):
            if P.islink(lib):
                continue
            devsep = lib.partition('.so.')
            dev = devsep[0] + '.so'
            if not P.exists(dev):
                warn('Creating isis dev symlink %s for %s' % (P.basename(dev), P.basename(lib)))
                self.helper('ln', '-sf', P.basename(lib), dev)

    @stage
    def fetch(self, skip=False):
        if not os.path.exists(self.localcopy):
            if skip: raise PackageError(self, 'Fetch is skipped and no src available')
            os.makedirs(self.localcopy)
        if skip: return
        self.copytree(self.src, self.localcopy + '/', ['-zv', '--exclude', 'doc/*', '--exclude', '*/doc/*'])

    @stage
    def unpack(self):
        output_dir = P.join(self.env['BUILD_DIR'], self.pkgname)
        self.remove_build(output_dir)
        self.workdir = P.join(output_dir, self.pkgname)
        if not P.exists(self.workdir):
            os.makedirs(self.workdir)
        self.copytree(self.localcopy + '/', self.workdir, ['--link-dest=%s' % self.localcopy])
        self._apply_patches()

    @stage
    def configure(self): pass
    @stage
    def compile(self): pass

    @stage
    def install(self):
        self.copytree(self.workdir + '/', self.env['ISISROOT'], ['--link-dest=%s' % self.localcopy])
        self._fix_dev_symlinks(self.env['ISIS3RDPARTY'])


class isis_local(isis):
    ''' This isis package just uses the isis in ISISROOT (it's your job to make sure the deps are correct) '''

    def __init__(self, env):
        super(isis_local, self).__init__(env)
        self.localcopy = None

    @stage
    def fetch(self, skip=False): pass
    @stage
    def unpack(self): pass
    @stage
    def configure(self): pass
    @stage
    def compile(self): pass
    @stage
    def install(self): pass

class osg(CMakePackage):
    src = 'http://www.openscenegraph.org/downloads/stable_releases/OpenSceneGraph-2.8.3/source/OpenSceneGraph-2.8.3.zip'
    chksum = '90502e4cbd47aac1689cc39d25ab62bbe0bba9fc'
    patches = 'patches/osg'

    def configure(self):
        super(osg, self).configure(
                with_='GDAL GLUT JPEG OpenEXR PNG ZLIB'.split(),
                without='COLLADA CURL FBX FFmpeg FLTK FOX FreeType GIFLIB Inventor ITK Jasper LibVNCServer OpenAL OpenVRML OurDCMTK Performer Qt3 Qt4 SDL TIFF wxWidgets Xine XUL'.split(),
                other=['-DBUILD_OSG_APPLICATIONS=ON'])

class flann(CMakePackage):
    src = 'http://people.cs.ubc.ca/~mariusm/uploads/FLANN/flann-1.6.8-src.zip'
    chksum = '35e8ca5dd76a1c36652e3c41fc3591a3d6f542c2'
    patches = 'patches/flann'

    def configure(self):
        super(flann, self).configure(other=['-DBUILD_C_BINDINGS=OFF -DBUILD_MATLAB_BINDINGS=OFF -DBUILD_PYTHON_BINDINGS=OFF'])

# vim:foldmethod=indent
