#!/usr/bin/env python

from BinaryBuilder import SVNPackage, Package, Environment, icall, PackageError

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
        super(gdal,self).configure(env, with_=w, without=wo)

class ilmbase(Package):
    src     = 'http://download.savannah.nongnu.org/releases/openexr/ilmbase-1.0.1.tar.gz'
    chksum  = 'f76f094e69a6079b0beb93d97e2a217e'
    patches = ('patches/ilmbase.pkg/ilmbase-1.0.0-asneeded.patch',)

class jpeg(Package):
    src     = 'http://www.ijg.org/files/jpegsrc.v6b.tar.gz'
    chksum  = 'dbd5f3b47ed13132f04c685d608a7547'
    patches = (\
        'patches/jpeg.pkg/05_all_jpeg-Makefile.patch',
        'patches/jpeg.pkg/06_all_jpeg-libtool.patch',
        'patches/jpeg.pkg/07_all_jpeg-LANG.patch',
        'patches/jpeg.pkg/30_all_jpeg-crop.patch',
        'patches/jpeg.pkg/50_all_jpeg-Debian-rdjpgcom_locale.patch',
        'patches/jpeg.pkg/51_all_jpeg-Debian-jpeglib.h_c++.patch',
        'patches/jpeg.pkg/52_all_jpeg-Debian-rdppm.patch',
        'patches/jpeg.pkg/60_all_jpeg-maxmem-sysconf.patch',
    )

    def configure(self, env):
        super(jpeg, self).configure(env, enable=('shared',), disable=('static',))

    def install(self, env):
        icall('mkdir', '-p', '%(INSTALL_DIR)s/man/man1' % env)
        super(jpeg,self).install(env)

class openexr(Package):
    src     = 'http://download.savannah.nongnu.org/releases/openexr/openexr-1.6.1.tar.gz'
    chksum  = '11951f164f9c872b183df75e66de145a'
    patches = ('patches/openexr.pkg/openexr-1.6.1-gcc-4.3.patch',)

    def configure(self, env):
        super(openexr,self).configure(env, with_=('ilmbase-prefix=%(INSTALL_DIR)s' % env,
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

        enable = ['debug=ignore', 'optimize=ignore', 'pkg_paths_default=no'] \
               + ['--enable-app-'  + a for a in enable_apps.split()] \
               + ['--disable-app-' + a for a in disable_apps.split()]

        with_ = ('pkg_paths="%(INSTALL_DIR)s"' % env)
        super(stereopipeline, self).configure(env, enable=enable, with_=with_)

class visionworkbench(SVNPackage):
    src     = 'https://babelfish.arc.nasa.gov/svn/visionworkbench/trunk'

    def configure(self, env):
        enable = ('debug=ignore', 'optimize=ignore', 'pkg_paths_default=no')
        args = ('pkg_paths="%(INSTALL_DIR)s"' % env, '--without-tiff', '--without-gl')

        super(stereopipeline, self).configure(env, other=args, enable=enable)

class zlib(Package):
    src     = 'http://www.zlib.net/zlib-1.2.3.tar.gz'
    chksum  = 'debc62758716a169df9f62e6ab2bc634'

    patches = (\
        'patches/zlib.pkg/zlib-1.2.3-build.patch',
        'patches/zlib.pkg/zlib-1.2.3-visibility-support.patch',
        'patches/zlib.pkg/zlib-1.2.1-glibc.patch',
        'patches/zlib.pkg/zlib-1.2.1-build-fPIC.patch',
        'patches/zlib.pkg/zlib-1.2.1-configure.patch',
        'patches/zlib.pkg/zlib-1.2.1-fPIC.patch',
        'patches/zlib.pkg/zlib-1.2.3-r1-bsd-soname.patch',
        'patches/zlib.pkg/zlib-1.2.3-LDFLAGS.patch',
    )

    def configure(self, env):
        super(zlib,self).configure(env, other=('--shared',))

class boost(Package): pass
#    src    = 'http://downloads.sourceforge.net/boost/boost_1_39_0.tar.gz'
#    chksum = 'fcc6df1160753d0b8c835d17fdeeb0a7'
#    patches = (\
#        'patches/boost.pkg/01_all_1.36.0-tools-build-fix.patch',
#        'patches/boost.pkg/02_all_1.37.0-function-templates-compile-fix.patch',
#        'patches/boost.pkg/03_all_1.36.0-compiler_status-trailing_slash.patch',
#        'patches/boost.pkg/07_all_1.35.0-fix_mpi_installation.patch',
#        'patches/boost.pkg/remove_toolset_from_targetname.patch',
#    )
#
#local OPTIONS="\
#    --includedir="$INSTALL_DIR/include" \
#    --layout=system \
#    --prefix="$INSTALL_DIR" \
#    --with-program_options --with-filesystem --with-system --with-thread \
#    threading=multi link=shared runtime-link=shared \
#"
#
##threading=single,multi link=shared,static runtime-link=shared,static \
#
#pkg_configure() {
#
#    bconf --with-libraries=program_options,filesystem,system,thread \
#          --without-icu \
#        || die "Could not configure boost"
#
#    eval "$(head -n1 Makefile)"
#    test -z "$BJAM" && die "Could not find bjam?"
#    export BJAM
#
#    local compiler=gcc
#    local compilerExecutable="$CC"
#    LDFLAGS="$LDFLAGS -ldl"
#
#    cat > "${WORKDIR}/user-config.jam" << __EOF__
#variant vwrelease : release : <optimization>off <debug-symbols>off ;
#using ${compiler} : : ${compilerExecutable} : <cxxflags>"${CXXFLAGS}" <linkflags>"${LDFLAGS}" ;
#__EOF__
#
#}
#
#pkg_build() {
#
#    export BOOST_ROOT="${WORKDIR}"
#
#    ${BJAM} -q \
#        ${OPTIONS} \
#        --user-config=${WORKDIR}/user-config.jam \
#        || die "boost build failed"
#}
#
#pkg_install() {
#
#    export BOOST_ROOT="${WORKDIR}"
#
#    ${BJAM} -q \
#        ${OPTIONS} \
#        --user-config=${WORKDIR}/user-config.jam \
#        install || die "boost install failed"
#}

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
        print >>sys.stderr, e
