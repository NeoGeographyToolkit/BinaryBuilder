#!/usr/bin/env python

from __future__ import print_function

from BinaryBuilder import SVNPackage, Package, stage
import os.path as P
import os

# pychecker objects to the stage decorator "changing the signature"
__pychecker__ = 'no-override'

class png(Package):
    src    = 'http://downloads.sourceforge.net/libpng/libpng-1.2.40.tar.gz'
    chksum = 'a2f6808735bf404967f81519a967fb2a'
    def __init__(self, env):
        super(png, self).__init__(env)
        self.env['CFLAGS'] = self.env.get('CFLAGS', '') + ' -I%(INSTALL_DIR)s/include' % self.env
        self.env['LDFLAGS'] = self.env.get('LDFLAGS', '') + ' -L%(INSTALL_DIR)s/lib' % self.env

class gdal(Package):
    src    = 'http://download.osgeo.org/gdal/gdal-1.6.2.tar.gz'
    chksum = 'f2dcd6aa7222d021202984523adf3b55'

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
    chksum  = 'f76f094e69a6079b0beb93d97e2a217e'
    patches = 'patches/ilmbase'

class jpeg(Package):
    #src     = 'http://www.ijg.org/files/jpegsrc.v6b.tar.gz'
    #chksum  = 'dbd5f3b47ed13132f04c685d608a7547'
    #patches = 'patches/jpeg6'

    src     = 'http://www.ijg.org/files/jpegsrc.v7.tar.gz'
    chksum  = '382ef33b339c299b56baf1296cda9785'
    patches = 'patches/jpeg7'

    def configure(self):
        super(jpeg, self).configure(enable=('shared',), disable=('static',))

    #def install(self):
    #    #self.helper('mkdir', '-p', '%(INSTALL_DIR)s/man/man1' % self.env)
    #    super(jpeg,self).install()

class openexr(Package):
    src     = 'http://download.savannah.nongnu.org/releases/openexr/openexr-1.6.1.tar.gz'
    chksum  = '11951f164f9c872b183df75e66de145a'
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
    chksum  = '7dbaab8431ad50c25669fd3fb28dc493'

class stereopipeline(SVNPackage):
    src     = 'https://babelfish.arc.nasa.gov/svn/stereopipeline/trunk'
    def configure(self):
        self.helper('./autogen')

        enable_apps  = 'stereo point2mesh point2dem disparitydebug'
        disable_apps = 'stereogui bundleadjust orbitviz nurbs ctximage \
                        rmax2cahvor rmaxadjust bundlevis isisadjust cudatest \
                        orthoproject point2mesh2 results'

        super(stereopipeline, self).configure(with_ = ['pkg_paths=%(INSTALL_DIR)s' % self.env],
                                              disable=['pkg_paths_default'] + ['app-' + a for a in disable_apps.split()],
                                              enable=['debug=ignore', 'optimize=ignore'] + ['app-'  + a for a in enable_apps.split()])

class visionworkbench(SVNPackage):
    src     = 'https://babelfish.arc.nasa.gov/svn/visionworkbench/trunk'

    def configure(self):
        self.helper('./autogen')

        w = [i + '=%(INSTALL_DIR)s' % self.env for i in ('jpeg', 'png', 'gdal', 'proj4', 'z', 'ilmbase', 'openexr', 'boost')]
        super(visionworkbench, self).configure(with_ = w,
                                               without=('tiff', 'gl', 'qt', 'hdf', 'cairomm', 'rabbitmq_c', 'protobuf', 'tcmalloc', 'x11'),
                                               disable=('pkg_paths_default','static'),
                                               enable=('debug=ignore', 'optimize=ignore'))

class zlib(Package):
    src     = 'http://www.zlib.net/zlib-1.2.3.tar.gz'
    chksum  = 'debc62758716a169df9f62e6ab2bc634'
    patches = 'patches/zlib'

    def configure(self):
        super(zlib,self).configure(other=('--shared',))

class bzip2(Package):
    src = 'http://www.bzip.org/1.0.5/bzip2-1.0.5.tar.gz'
    chksum = '3c15a0c8d1d3ee1c46a1634d00617b1a'
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
    chksum = 'fcc6df1160753d0b8c835d17fdeeb0a7'
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

#class isis_linux64(Package):
#
#    @stage
#    def unpack(self, 
#    rsync -azv --delete isisdist.wr.usgs.gov::isis3_x86-64_linux/isis .
