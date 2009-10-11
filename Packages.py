#!/usr/bin/env python

from __future__ import print_function

from BinaryBuilder import SVNPackage, Package, stage, PackageError
import os.path as P
import os
from glob import glob
import textwrap

def get_platform(pkg):
    import platform
    system = platform.system()
    if system == 'Linux' and platform.architecture()[0] == '64bit':
        return 'linux64'
    elif system == 'Linux' and platform.architecture()[0] == '32bit':
        return 'linux32'
    elif system == 'Darwin': # ignore arch here, it seems to just return 32-bit
        return 'osx32'
    else:
        raise PackageError(pkg, 'Cannot match system to known platform')

class png(Package):
    src    = 'http://downloads.sourceforge.net/libpng/libpng-1.2.40.tar.gz'
    chksum = 'a3f2df01871da15d66f103a5b4e793601e4d1043'
    def __init__(self, env):
        super(png, self).__init__(env)
        self.env['CFLAGS'] = self.env.get('CFLAGS', '') + ' -I%(INSTALL_DIR)s/include' % self.env
        self.env['LDFLAGS'] = self.env.get('LDFLAGS', '') + ' -L%(INSTALL_DIR)s/lib' % self.env

class gdal(Package):
    src    = 'http://download.osgeo.org/gdal/gdal-1.6.2.tar.gz'
    chksum = '1d9e1d8f01f06bca99e7335d7e86dff784eee819'

    def configure(self):
        # Most of these are disabled due to external deps.
        # Gif pulls in X for some reason.
        w = ('threads', 'libtiff=internal', 'png=%(INSTALL_DIR)s' % self.env, 'jpeg=%(INSTALL_DIR)s' % self.env)
        wo = ('cfitsio', 'curl', 'dods-root', 'dwgdirect', 'dwg-plt', 'ecw',
              'expat', 'expat-inc', 'expat-lib', 'fme', 'geos', 'grass', 'hdf4',
              'hdf5', 'idb', 'ingres', 'jasper', 'jp2mrsid', 'kakadu',
              'libgrass', 'macosx-framework', 'mrsid', 'msg', 'mysql', 'netcdf',
              'oci', 'oci-include', 'oci-lib', 'odbc', 'ogdi', 'pcraster', 'perl',
              'pg', 'php', 'python', 'ruby', 'sde', 'sde-version', 'sqlite3', 'xerces',
              'xerces-inc', 'xerces-lib', 'gif')
        super(gdal,self).configure(with_=w, without=wo, disable='static')

class ilmbase(Package):
    src     = 'http://download.savannah.nongnu.org/releases/openexr/ilmbase-1.0.1.tar.gz'
    chksum  = '143adc547be83c6df75831ae957eef4b2706c9c0'
    patches = 'patches/ilmbase'

class jpeg(Package):
    #src     = 'http://www.ijg.org/files/jpegsrc.v6b.tar.gz'
    #chksum  = ''
    #patches = 'patches/jpeg6'

    src     = 'http://www.ijg.org/files/jpegsrc.v7.tar.gz'
    chksum  = '88cced0fc3dbdbc82115e1d08abce4e9d23a4b47'
    patches = 'patches/jpeg7'

    def configure(self):
        super(jpeg, self).configure(enable=('shared',), disable=('static',))

class openexr(Package):
    src     = 'http://download.savannah.nongnu.org/releases/openexr/openexr-1.6.1.tar.gz'
    chksum  = 'b3650e6542f0e09daadb2d467425530bc8eec333'
    patches = 'patches/openexr'

    def __init__(self, env):
        super(openexr, self).__init__(env)
        self.env['CFLAGS'] = self.env.get('CFLAGS', '') + ' -I%(INSTALL_DIR)s/include' % self.env
        self.env['LDFLAGS'] = self.env.get('LDFLAGS', '') + ' -L%(INSTALL_DIR)s/lib' % self.env

    def configure(self):
        super(openexr,self).configure(with_=('ilmbase-prefix=%(INSTALL_DIR)s' % self.env),
                                      disable=('ilmbasetest', 'imfexamples'))

class proj(Package):
    src     = 'http://download.osgeo.org/proj/proj-4.6.1.tar.gz'
    chksum  = 'ddfdad6cba28af5f91b14fd6690bd22bbbc79390'

class stereopipeline(SVNPackage):
    src     = 'https://babelfish.arc.nasa.gov/svn/stereopipeline/trunk'
    def configure(self):
        self.helper('./autogen')

        disable_apps = 'rmax2cahvor rmaxadjust results reconstruct'
        enable_apps  = 'stereo orthoproject bundleadjust orbitviz disparitydebug\
                         point2mesh point2dem ctximage bundlevis isisadjust'

        noinstall_pkgs = 'spice qwt gsl geos superlu xercesc'.split()
        install_pkgs   = 'boost vw_core vw_math vw_image vw_fileio vw_camera \
                          vw_stereo vw_cartography vw_interest_point openscenegraph flapack'.split()

        w = [i + '=%(INSTALL_DIR)s'   % self.env for i in install_pkgs] \
          + [i + '=%(NOINSTALL_DIR)s' % self.env for i in noinstall_pkgs] \
          + ['isis=%s' % self.env['ISISROOT']]

        includedir = P.join(self.env['NOINSTALL_DIR'], 'include')

        with file(P.join(self.workdir, 'config.options'), 'w') as config:
            for pkg in noinstall_pkgs:
                print('PKG_%s_LDFLAGS=-L%s' % (pkg.upper(), self.env['ISIS3RDPARTY']), file=config)
            print('PKG_FLAPACK_LDFLAGS="-L%s -L%s"' % (P.join(self.env['INSTALL_DIR'], 'lib'), self.env['ISIS3RDPARTY']), file=config)

            qt_pkgs = 'Core Gui Network Sql Xml XmlPatterns'

            print('QT_ARBITRARY_MODULES="%s"' % qt_pkgs, file=config)
            print('PKG_ARBITRARY_QT_CPPFLAGS="-I%s %s"' %  (includedir, ' '.join(['-I' + P.join(includedir, 'Qt%s' % pkg) for pkg in qt_pkgs.split()])), file=config)
            print('PKG_ARBITRARY_QT_LDFLAGS="-L%s"' % self.env['ISIS3RDPARTY'], file=config)
            print('PKG_ARBITRARY_QT_MORE_LIBS="-lreadline -lmysqlclient_r -lpq -lssl -lcrypto"', file=config)
            print('PKG_SUPERLU_LIBS=%s' % glob(P.join(self.env['ISIS3RDPARTY'], 'libsuperlu*.a'))[0], file=config)
            print('PKG_XERCESC_LDFLAGS="-L%s"' % self.env['ISIS3RDPARTY'], file=config)
            print('PKG_XERCESC_MORE_LIBS="-licuuc -licudata"', file=config)

        super(stereopipeline, self).configure(
            with_   = w,
            without = ['clapack', 'slapack'],
            disable = ['pkg_paths_default', 'static', 'qt-qmake']   + ['app-' + a for a in disable_apps.split()],
            enable  = ['debug=ignore', 'optimize=ignore'] + ['app-' + a for a in enable_apps.split()])

class visionworkbench(SVNPackage):
    src     = 'https://babelfish.arc.nasa.gov/svn/visionworkbench/trunk'

    def configure(self):
        self.helper('./autogen')

        w  = [i + '=%(INSTALL_DIR)s' % self.env for i in 'jpeg png gdal proj4 z ilmbase openexr boost flapack'.split()]

        with file(P.join(self.workdir, 'config.options'), 'w') as config:
            print('PKG_FLAPACK_LDFLAGS="-L%s -L%s"' % (P.join(self.env['INSTALL_DIR'], 'lib'), self.env['ISIS3RDPARTY']), file=config)

        super(visionworkbench, self).configure(with_ = w,
                                               without=('tiff gl qt hdf cairomm rabbitmq_c protobuf tcmalloc x11 clapack slapack'.split()),
                                               disable=('pkg_paths_default','static', 'qt-qmake'),
                                               enable=('debug=ignore', 'optimize=ignore'))

class lapack(Package):
    src     = 'http://www.netlib.org/lapack/lapack-3.1.0.tgz'
    chksum  = '6acf1483951cdcf16fc0e670ae1bc066ac1d185d'
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
        super(lapack, self).configure(with_='blas=-L%s -lblas' % self.env['ISIS3RDPARTY'])

class zlib(Package):
    src     = 'http://www.zlib.net/zlib-1.2.3.tar.gz'
    chksum  = '60faeaaf250642db5c0ea36cd6dcc9f99c8f3902'
    patches = 'patches/zlib'

    def configure(self):
        super(zlib,self).configure(other=('--shared',))

class bzip2(Package):
    src = 'http://www.bzip.org/1.0.5/bzip2-1.0.5.tar.gz'
    chksum = '8b02713ea0c8eb501cc8bdac4432d7f29700f767'
    patches = 'patches/bzip2'

    @stage
    def unpack(self):
        super(bzip2, self).unpack()
        self.helper('sed', '-i', '-e', 's:1\.0\.4:1.0.5:', 'Makefile-libbz2_so')

    @stage
    def configure(self):
        pass

    @stage
    def compile(self):
        cmd = ('make', )
        if 'MAKEOPTS' in self.env:
            cmd += (self.env['MAKEOPTS'],)
        cmd1 = cmd + ('-f', 'Makefile-libbz2_so', 'all')
        cmd2 = cmd + ('all',)
        self.helper(*cmd1)
        self.helper(*cmd2)

    @stage
    def install(self):
        self.helper('install', '-d', '%(INSTALL_DIR)s/include' % self.env)
        self.helper('install', '-d', '%(INSTALL_DIR)s/lib' % self.env)
        self.helper('install', '-m0644', 'bzlib.h', '%(INSTALL_DIR)s/include' % self.env)
        self.helper('install', '-m0755', 'libbz2.so.1.0.5', '%(INSTALL_DIR)s/lib' % self.env)
        self.helper('ln', '-sf', 'libbz2.so.1.0.5', '%(INSTALL_DIR)s/lib/libbz2.so.1.0' % self.env)
        self.helper('ln', '-sf', 'libbz2.so.1.0.5', '%(INSTALL_DIR)s/lib/libbz2.so.1' % self.env)
        self.helper('ln', '-sf', 'libbz2.so.1.0.5', '%(INSTALL_DIR)s/lib/libbz2.so' % self.env)


class boost(Package):
    src    = 'http://downloads.sourceforge.net/boost/boost_1_39_0.tar.gz'
    chksum = 'fc0f98aea163f2edd8d74e18eafc4704d7d93d07'
    patches = 'patches/boost'

    def __init__(self, env):
        super(boost, self).__init__(env)
        self.env['CFLAGS']   = self.env.get('CFLAGS', '')    + ' -I%(INSTALL_DIR)s/include' % self.env
        self.env['CXXFLAGS'] = self.env.get('CXXFLAGS', '')  + ' -I%(INSTALL_DIR)s/include' % self.env
        self.env['LDFLAGS']  = self.env.get('LDFLAGS', '')   + ' -L%(INSTALL_DIR)s/lib' % self.env

    @stage
    def configure(self):
        with file(P.join(self.workdir, 'user-config.jam'), 'w') as f:
            print('variant myrelease : release : <optimization>none <debug-symbols>none ;', file=f)
            print('variant mydebug : debug : <optimization>none ;', file=f)
            print('using gcc : : %s : <cxxflags>"%s" <linkflags>"%s -ldl" ;' %
                  tuple(self.env.get(i, ' ') for i in ('CC', 'CXXFLAGS', 'LDFLAGS')), file=f)

    # TODO: WRONG. There can be other things besides -j4 in MAKEOPTS
    @stage
    def compile(self):
        self.env['BOOST_ROOT'] = self.workdir

        self.helper('./bootstrap.sh')
        os.unlink(P.join(self.workdir, 'project-config.jam'))

        cmd = ['./bjam']
        if 'MAKEOPTS' in self.env:
            cmd += (self.env['MAKEOPTS'],)
        cmd += ['-q', 'variant=myrelease', '--user-config=%s/user-config.jam' % self.workdir,
                '--prefix=%(INSTALL_DIR)s' % self.env, '--layout=versioned',
                'threading=multi', 'link=shared', 'runtime-link=shared']
        self.helper(*cmd)

    # TODO: Might need some darwin path-munging with install_name_tool?
    @stage
    def install(self):
        self.env['BOOST_ROOT'] = self.workdir
        cmd = ['./bjam', '-q', 'variant=myrelease', '--user-config=%s/user-config.jam' % self.workdir,
               '--prefix=%(INSTALL_DIR)s' % self.env, '--layout=versioned',
               'threading=multi', 'link=shared', 'runtime-link=shared',
              'install']
        self.helper(*cmd)

class HeaderPackage(Package):
    @stage
    def configure(self, *args, **kw):
        kw['other'] = kw.get('other', []) + ['--prefix=%(NOINSTALL_DIR)s' % self.env,]
        super(HeaderPackage, self).configure(*args, **kw)

    def compile(self): pass

    @stage
    def install(self):
        self.helper('make', 'install-data')

class gsl_headers(HeaderPackage):
    src = 'http://mirrors.kernel.org/gnu/gsl/gsl-1.7.tar.gz',
    chksum = '0915f99c5eca63e6a4d4ed31b6a224789f918200',

class geos_headers(HeaderPackage):
    src = 'http://download.osgeo.org/geos/geos-3.0.0.tar.bz2',
    chksum = '71090220351c8ae7bb147d74145fa5daf83e3c26',
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
    src = 'http://archive.apache.org/dist/xml/xerces-c/Xerces-C_2_7_0/source/xerces-c-src_2_7_0.tar.gz',
    chksum = '56f9587f33fca0a573a45f07762e3262a255d73f',
    def configure(self):
        self.env['XERCESCROOT'] = self.workdir

        arch = get_platform(self)
        if arch  == 'linux64':
            arch = 'linux'
            bits = 64
        elif arch == 'linux32':
            arch = 'linux'
            bits = 32
        elif arch == 'osx32':
            arch = 'macosx'
            bits = 32
        else:
            raise PackageError(self, 'Unsupported arch: %s' % arch)

        cmd = ['./runConfigure', '-p%s' % arch, '-b%s' % bits, '-P%(NOINSTALL_DIR)s' % self.env]
        self.helper(*cmd, cwd=P.join(self.workdir, 'src', 'xercesc'))
    def compile(self):
        self.helper('make', 'Prepare', cwd=P.join(self.workdir, 'src', 'xercesc'))
    def install(self):
        d = P.join(self.env['NOINSTALL_DIR'], 'include')
        cmd = ['cp', '-vfR', P.join(self.workdir, 'include', 'xercesc'), d]
        self.helper(*cmd)

class qt_headers(HeaderPackage):
    src = 'http://get.qt.nokia.com/qt/source/qt-x11-opensource-src-4.4.1.tar.bz2',
    chksum = 'b0087fe51271f81d4dc35d4cb7518ef84a36f3c2',
    def configure(self):
        self.helper('./configure', '-confirm-license')

    def install(self):
        ext = ('.h', '.pro', '.pri')
        def docopy(files, dirname, fnames):
            accept = dirname.startswith('./include/')
            for f in fnames:
                if accept or P.splitext(f)[-1] in ext:
                    full = P.join(dirname, f)
                    if not P.isdir(full):
                        files.append(full)

        pwd = os.getcwd()
        os.chdir(self.workdir)

        files = []
        # This is amazingly ugly. All because OSX has a broken find(1). Sigh.
        try:
            P.walk('./', docopy, files)
            max_length = os.sysconf('SC_ARG_MAX') - len('cp --parent ') - len(self.env['NOINSTALL_DIR'])
            cmds = textwrap.wrap(' '.join(files), max_length)
            for f in cmds:
                run = ['cp', '--parent'] + f.split() + [self.env['NOINSTALL_DIR']]
                self.helper(*run)
        finally:
            os.chdir(pwd)

class qwt_headers(HeaderPackage):
    src = 'http://downloads.sourceforge.net/qwt/qwt-5.1.1.tar.bz2',
    chksum = 'fdb85ceafaf6778ca7bd507e08215f6e0bc39757',
    def configure(self): pass
    def install(self):
        cmd = ['cp', '-vf'] + glob(P.join(self.workdir, 'src', '*.h')) + [P.join('%(NOINSTALL_DIR)s' % self.env, 'include')]
        self.helper(*cmd)

class cspice_headers(HeaderPackage):
    # This will break when they release a new version BECAUSE THEY USE UNVERSIONED TARBALLS.
    PLATFORM = dict(
        linux64 = dict(
            src    = 'ftp://naif.jpl.nasa.gov/pub/naif/toolkit/C/PC_Linux_GCC_64bit/packages/cspice.tar.Z',
            chksum = '27643e4b7a872a9e663913f24807fbd9c9439710',
        ),
        linux32 = dict(
            src    = 'ftp://naif.jpl.nasa.gov/pub/naif/toolkit/C/PC_Linux_GCC_32bit/packages/cspice.tar.Z',
            chksum = 'b7d51a021f0edb2ffd9cbd6b3d1fc70cf2533b93',
        ),
        osx32   = dict(
            src    = 'ftp://naif.jpl.nasa.gov/pub/naif/toolkit/C/MacIntel_OSX_AppleC_32bit/packages/cspice.tar.Z',
            chksum = '6148ae487eb66e99df92d2b7cf00bfd187633c0c',
        ),
    )

    def __init__(self, env):
        super(cspice_headers, self).__init__(env)
        arch = get_platform(self)
        self.pkgname += '_' + arch
        self.src    = self.PLATFORM[arch]['src']
        self.chksum = self.PLATFORM[arch]['chksum']
    def configure(self, *args, **kw): pass
    def install(self):
        cmd = ['cp', '-vf'] + glob(P.join(self.workdir, 'include', '*.h')) + [P.join('%(NOINSTALL_DIR)s' % self.env, 'include')]
        self.helper(*cmd)

class isis(Package):

    ### Needs: superlu-3.0 gsl-1.7 qwt-5.1.1 geos-3.0.0 spice-0061 xerces-c 2.7.0 (+icu 3.4.0) qt-4.4.1

    PLATFORM = dict(
        linux64 = 'isisdist.wr.usgs.gov::isis3_x86-64_linux/isis/',
        linux32 = 'isisdist.wr.usgs.gov::isis3_x86_linux/isis/',
        osx32   = 'isisdist.wr.usgs.gov::isis3_intel_darwin/isis/',
    )

    def __init__(self, env):
        super(isis, self).__init__(env)
        arch = get_platform(self)

        self.pkgname += '_' + arch

        self.src = self.PLATFORM[arch]

        self.localcopy = P.join(env['DOWNLOAD_DIR'], 'rsync', self.pkgname)

    @stage
    def fetch(self):
        if not P.exists(P.dirname(self.localcopy)):
            os.mkdir(P.dirname(self.localcopy))
        if not P.exists(self.localcopy):
            os.mkdir(self.localcopy)
        self.helper('rsync', '-azv', '--delete', '--exclude', 'doc/*', '--exclude', '*/doc/*', self.src, self.localcopy)

    @stage
    def unpack(self):
        output_dir = P.join(self.env['BUILD_DIR'], self.pkgname)
        self.remove_build(output_dir)
        self.workdir = P.join(output_dir, self.pkgname + '-rsync')

        cmd = ('cp', '-lr', self.localcopy, self.workdir)
        self.helper(*cmd, cwd=output_dir)

        self._apply_patches()

    @stage
    def configure(self): pass

    @stage
    def compile(self): pass

    @stage
    def install(self):
        cmd = ('cp', '-lr', self.workdir, self.env['ISISROOT'])
        self.helper(*cmd)

        # Idiots...
        missing_links = (('libgeos-3*.so', 'libgeos.so'),  ('libblas.so.*', 'libblas.so'), 
                         ('libicuuc.so.*', 'libicuuc.so'), ('libicudata.so.*', 'libicudata.so'),
                         ('libreadline.so.5', 'libreadline.so'))

        for tgt, name in missing_links:
            self.helper('ln', '-sf', P.basename(glob(P.join(self.env['ISIS3RDPARTY'], tgt))[0]), P.join(self.env['ISIS3RDPARTY'], name))

class osg(Package):
    src = 'http://www.openscenegraph.org/downloads/stable_releases/OpenSceneGraph-2.8.2/source/OpenSceneGraph-2.8.2.zip'
    chksum = 'f2f0a3285a022640345a81f536459f37f3f38d01'
    patches = 'patches/osg'

    @stage
    def configure(self):
        self.builddir = P.join(self.workdir, 'build')

        def remove_danger(files, dirname, fnames):
            files.extend([P.join(dirname,f) for f in fnames if f == 'CMakeLists.txt'])

        files = []
        P.walk(self.workdir, remove_danger, files)
        cmd = ['sed',  '-i',
                    '-e', '/^[[:space:]]*[sS][eE][tT][[:space:]]*([[:space:]]*CMAKE_BUILD_TYPE.*)/{s/^/#IGNORE /g}',
                    '-e', '/^[[:space:]]*[sS][eE][tT][[:space:]]*([[:space:]]*CMAKE_INSTALL_PREFIX.*)/{s/^/#IGNORE /g}']

        cmd.extend(files)
        self.helper(*cmd)

        build_rules = P.join(os.environ.get('TMPDIR', '/tmp'), 'my_rules.cmake')
        with file(build_rules, 'w') as f:
            print('SET (CMAKE_C_COMPILER "%s" CACHE FILEPATH "C compiler" FORCE)' % (self.env['CC']), file=f)
            print('SET (CMAKE_C_COMPILE_OBJECT "<CMAKE_C_COMPILER> <DEFINES> %s <FLAGS> -o <OBJECT> -c <SOURCE>" CACHE STRING "C compile command" FORCE)' % (self.env.get('CPPFLAGS', '')), file=f)
            print('SET (CMAKE_CXX_COMPILER "%s" CACHE FILEPATH "C++ compiler" FORCE)' % (self.env['CXX']), file=f)
            print('SET (CMAKE_CXX_COMPILE_OBJECT "<CMAKE_CXX_COMPILER> <DEFINES> %s <FLAGS> -o <OBJECT> -c <SOURCE>" CACHE STRING "C++ compile command" FORCE)' % (self.env.get('CPPFLAGS', '')), file=f)

        cmd = ['cmake']
        args = [
            '-DCMAKE_INSTALL_PREFIX=%(INSTALL_DIR)s' % self.env,
            '-DCMAKE_BUILD_TYPE=MyBuild',
            '-DCMAKE_USER_MAKE_RULES_OVERRIDE=%s' % build_rules,
            '-DCMAKE_SKIP_RPATH=YES',
        ]

        for arg in 'XUL PDF XINE JPEG2K SVG FREETYPE CURL GIF TIFF XRANDR INVENTOR COLLADA OPENVRML PERFORMER ITK LIBVNCSERVER OURDCMTK GTK CAIRO'.split():
            args.append('-DENABLE_%s=OFF' % arg)
        for arg in ('JPEG', 'PNG', 'OPENEXR', 'ZLIB', 'GDAL'):
            args.append('-DENABLE_%s=ON' % arg)

        args.extend([
            '-DCMAKE_PREFIX_PATH=%(INSTALL_DIR)s' % self.env,
            '-DBUILD_OSG_APPLICATIONS=OFF',
            '-DLIB_POSTFIX=',
        ])


        os.mkdir(self.builddir)

        cmd = cmd + args + [self.workdir]

        self.helper(*cmd, cwd=self.builddir)

    @stage
    def compile(self):
        cmd = ('make', )
        if 'MAKEOPTS' in self.env:
            cmd += (self.env['MAKEOPTS'],)

        e = self.env.copy()
        if 'prefix' not in e:
            e['prefix'] = self.env['INSTALL_DIR']

        self.helper(*cmd, env=e, cwd=self.builddir)

    @stage
    def install(self):
        '''After install, the binaries should be on the live filesystem.'''

        e = self.env.copy()
        if 'prefix' not in e:
            e['prefix'] = self.env['INSTALL_DIR']

        cmd = ('make', 'install')
        self.helper(*cmd, env=e, cwd=self.builddir)
