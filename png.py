#!/usr/bin/env python

from __future__ import print_function

from BinaryBuilder import SVNPackage, Package, Environment, icall, PackageError
import os.path as P

# pychecker objects to the stage decorator "changing the signature"
__pychecker__ = 'no-override'

class png(Package):
    src    = 'http://downloads.sourceforge.net/libpng/libpng-1.2.40.tar.gz'
    chksum = 'a2f6808735bf404967f81519a967fb2a'

class gdal(Package):
    src    = 'http://download.osgeo.org/gdal/gdal-1.6.2.tar.gz'
    chksum = 'f2dcd6aa7222d021202984523adf3b55'

    def configure(self, env):
        w = ('threads', 'libtiff=internal', 'png=%(INSTALL_DIR)s' % env, 'jpeg=%(INSTALL_DIR)s' % env)
        wo = ('cfitsio', 'curl', 'dods-root', 'dwgdirect', 'dwg-plt', 'ecw',
              'expat', 'expat-inc', 'expat-lib', 'fme', 'geos', 'grass', 'hdf4',
              'hdf5', 'idb', 'ingres', 'jasper', 'jp2mrsid', 'kakadu',
              'libgrass', 'macosx-framework', 'mrsid', 'msg', 'mysql', 'netcdf',
              'oci', 'oci-include', 'oci-lib', 'odbc', 'ogdi', 'pcraster', 'perl',
              'pg', 'php', 'python', 'ruby', 'sde', 'sde-version', 'sqlite3', 'xerces',
              'xerces-inc', 'xerces-lib')
        super(gdal,self).configure(env, with_=w, without=wo, disable='static')

class ilmbase(Package):
    src     = 'http://download.savannah.nongnu.org/releases/openexr/ilmbase-1.0.1.tar.gz'
    chksum  = 'f76f094e69a6079b0beb93d97e2a217e'
    patches = 'patches/ilmbase'

class jpeg(Package):
    src     = 'http://www.ijg.org/files/jpegsrc.v6b.tar.gz'
    chksum  = 'dbd5f3b47ed13132f04c685d608a7547'
    patches = 'patches/jpeg'

    def configure(self, env):
        super(jpeg, self).configure(env, enable=('shared',), disable=('static',))

    def install(self, env):
        icall('mkdir', '-p', '%(INSTALL_DIR)s/man/man1' % env)
        super(jpeg,self).install(env)

class openexr(Package):
    src     = 'http://download.savannah.nongnu.org/releases/openexr/openexr-1.6.1.tar.gz'
    chksum  = '11951f164f9c872b183df75e66de145a'
    patches = 'patches/openexr'

    def configure(self, env):
        super(openexr,self).configure(env, with_=('ilmbase-prefix=%(INSTALL_DIR)s' % env),
                                           disable=('ilmbasetest', 'imfexamples'))

class proj(Package):
    src     = 'http://download.osgeo.org/proj/proj-4.6.1.tar.gz'
    chksum  = '7dbaab8431ad50c25669fd3fb28dc493'

class stereopipeline(SVNPackage):
    src     = 'https://babelfish.arc.nasa.gov/svn/stereopipeline/trunk'
    def configure(self, env):
        enable_apps  = 'stereo point2mesh point2dem disparitydebug'
        disable_apps = 'stereogui bundleadjust orbitviz nurbs ctximage \
                        rmax2cahvor rmaxadjust bundlevis isisadjust cudatest \
                        orthoproject point2mesh2 results'

        super(stereopipeline, self).configure(env,
                                               with_ = 'pkg_paths=%(INSTALL_DIR)s' % env,
                                               disable=['pkg_paths_default'] + ['app-' + a for a in disable_apps.split()],
                                               enable=['debug=ignore', 'optimize=ignore'] + ['app-'  + a for a in enable_apps.split()])

class visionworkbench(SVNPackage):
    src     = 'https://babelfish.arc.nasa.gov/svn/visionworkbench/trunk'

    def configure(self, env):
        icall('./autogen', cwd=self.workdir, env=env)

        super(visionworkbench, self).configure(env,
                                               with_ = 'pkg_paths=%(INSTALL_DIR)s' % env,
                                               without=('tiff', 'gl', 'qt', 'hdf', 'cairomm', 'rabbitmq_c', 'protobuf', 'tcmalloc'),
                                               disable=('pkg_paths_default','static'),
                                               enable=('debug=ignore', 'optimize=ignore'))

class zlib(Package):
    src     = 'http://www.zlib.net/zlib-1.2.3.tar.gz'
    chksum  = 'debc62758716a169df9f62e6ab2bc634'
    patches = 'patches/zlib'

    def configure(self, env):
        super(zlib,self).configure(env, other=('--shared',))

class boost(Package):
    src    = 'http://downloads.sourceforge.net/boost/boost_1_39_0.tar.gz'
    chksum = 'fcc6df1160753d0b8c835d17fdeeb0a7'
    patches = 'patches/boost'

    def configure(self, env):
        with file(P.join(self.workdir, 'user-config.jam'), 'w') as f:
            print('variant myrelease : release : <optimization>none <debug-symbols>none ;', file=f)
            print('variant mydebug : debug : <optimization>none ;', file=f)
            print('using gcc : : %s : <cxxflags>"%s" <linkflags>"%s -ldl" ;' %
                  tuple(env.get(i, ' ') for i in ('CC', 'CXXFLAGS', 'LDFLAGS')), file=f)

    # TODO: WRONG. There can be other things besides -j4 in MAKEOPTS
    def compile(self, env):
        env['BOOST_ROOT'] = self.workdir

        icall('./bootstrap.sh', cwd=self.workdir)
        os.unlink(P.join(self.workdir, 'project-config.jam'))

        cmd = ['./bjam']
        if 'MAKEOPTS' in env:
            cmd += (env['MAKEOPTS'],)
        cmd += ['-q', 'variant=myrelease', '--user-config=%s/user-config.jam' % self.workdir,
                '--prefix=%(INSTALL_DIR)s' % env, '--layout=versioned',
                'threading=multi', 'link=shared', 'runtime-link=shared']
        icall(*cmd, cwd=self.workdir, env=env)

    # TODO: Might need some darwin path-munging with install_name_tool?
    def install(self, env):
        env['BOOST_ROOT'] = self.workdir
        cmd = ['./bjam', '-q', 'variant=myrelease', '--user-config=%s/user-config.jam' % self.workdir,
               '--prefix=%(INSTALL_DIR)s' % env, '--layout=versioned',
               'threading=multi', 'link=shared', 'runtime-link=shared',
              'install']
        icall(*cmd, cwd=self.workdir, env=env)

class isis(Package):
    def __init__(self, env, arch):
        if arch not in ('x86_linux', 'x86_64_linux', 'darwin'):
            raise Exception('Unsupported isis architecture')

        super(isis, self).__init__(env)

#pkg_download() {
#    local dd="${DOWNLOAD_DIR}/${PKGNAME}"
#    mkdir "$dd"
#    cd $dd
#    rsync -azv --delete isisdist.wr.usgs.gov::isis3_x86_linux/isis .
#}
#
#pkg_unpack() {
#    export WORKDIR="${DOWNLOAD_DIR}/${PKGNAME}/isis"
#}
#
#pkg_configure() {
#    true
#}
#
#pkg_build() {
#    true
#}
#
#pkg_install() {
#    ISIS_INCLUDEDIR="$INSTALL_DIR/include/isis"
#    ISIS_LIBDIR="$INSTALL_DIR/lib/isis"
#
#    install -v -m0755 -d $ISIS_INCLUDEDIR $ISIS_LIBDIR
#
#    install -v -m0644 -t $ISIS_INCLUDEDIR inc/*.h
#    install -v -m0755 -t $ISIS_LIBDIR lib/*.so lib/*.plugin lib/*.a
#
#    cp -vr 3rdParty/lib/* 3rdParty/plugins "$ISIS_LIBDIR"
#}

if __name__ == '__main__':
    import os
    import sys

    e = Environment(CC='ccache gcc', CFLAGS='', CXX='ccache g++', CXXFLAGS='', MAKEOPTS='-j4', PATH=os.environ['PATH'])

    if len(sys.argv) == 1:
        build = (zlib, png, jpeg, proj, gdal, ilmbase, openexr, boost, visionworkbench, isis, stereopipeline)
    else:
        build = (globals()[pkg] for pkg in sys.argv[1:])

    try:
        for pkg in build:
            Package.build(pkg, e)
    except PackageError, e:
        print('ERROR: ', e)
