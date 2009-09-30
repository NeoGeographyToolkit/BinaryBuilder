#!/usr/bin/env python

from BinaryBuilder import Package, Environment

class png(Package):
    src    = 'http://downloads.sourceforge.net/libpng/libpng-1.2.40.tar.gz'
    chksum = '8ca6246930a57d5be7adc7c4e7fb5e00'

class gdal(Package):
    src    = 'http://download.osgeo.org/gdal/gdal-1.6.2.tar.gz'
    chksum = 'f2dcd6aa7222d021202984523adf3b55'

    def configure(self, env, *args):
        w = ('threads', 'libtiff=internal', 'png=%(INSTALL_DIR)s' % env, 'jpeg=%(INSTALL_DIR)s' % env)
        wo = ('cfitsio', 'curl', 'dods-root', 'dwgdirect', 'dwg-plt', 'ecw', 
              'expat', 'expat-inc', 'expat-lib', 'fme', 'geos', 'grass', 'hdf4', 
              'hdf5', 'idb', 'ingres', 'jasper', 'jp2mrsid', 'kakadu', 
              'libgrass', 'macosx-framework', 'mrsid', 'msg', 'mysql', 'netcdf',
              'oci', 'oci-include', 'oci-lib', 'odbc', 'ogdi', 'pcraster', 'perl',
              'pg', 'php', 'python', 'ruby', 'sde', 'sde-version', 'sqlite3', 'xerces',
              'xerces-inc', 'xerces-lib')
        args = ['--with-' + i for i in w] + ['--without-' + i for i in wo]
        super(gdal,self).configure(env, *args)


#===== /mnt/gentoo32/home/mike/BinaryStereo/builder/pkgs/ilmbase.pkg =====
#SRC=http://download.savannah.nongnu.org/releases/openexr/ilmbase-1.0.1.tar.gz
#MD5=f76f094e69a6079b0beb93d97e2a217e
#
#PATCHES="patches/ilmbase.pkg/ilmbase-1.0.0-asneeded.patch"
#===== /mnt/gentoo32/home/mike/BinaryStereo/builder/pkgs/isis-x86.pkg =====
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
#===== /mnt/gentoo32/home/mike/BinaryStereo/builder/pkgs/jpeg.pkg =====
#SRC=http://www.ijg.org/files/jpegsrc.v6b.tar.gz
#MD5=dbd5f3b47ed13132f04c685d608a7547
#
#CONFIGURE_OPTIONS="--enable-shared --disable-static"
#
## These patches are all taken from the gentoo jpeg patches
#
#PATCHES="patches/jpeg.pkg/05_all_jpeg-Makefile.patch \
#         patches/jpeg.pkg/06_all_jpeg-libtool.patch \
#         patches/jpeg.pkg/07_all_jpeg-LANG.patch \
#         patches/jpeg.pkg/30_all_jpeg-crop.patch \
#         patches/jpeg.pkg/50_all_jpeg-Debian-rdjpgcom_locale.patch \
#         patches/jpeg.pkg/51_all_jpeg-Debian-jpeglib.h_c++.patch \
#         patches/jpeg.pkg/52_all_jpeg-Debian-rdppm.patch \
#         patches/jpeg.pkg/60_all_jpeg-maxmem-sysconf.patch"
#
#pkg_install() {
#    mkdir -p "$INSTALL_DIR/man/man1"
#    default_pkg_install
#}
#===== /mnt/gentoo32/home/mike/BinaryStereo/builder/pkgs/openexr.pkg =====
#SRC=http://download.savannah.nongnu.org/releases/openexr/openexr-1.6.1.tar.gz
#MD5=11951f164f9c872b183df75e66de145a
#
#PATCHES="patches/openexr.pkg/openexr-1.6.1-gcc-4.3.patch"
#CONFIGURE_OPTIONS="--disable-ilmbasetest --disable-imfexamples"
#===== /mnt/gentoo32/home/mike/BinaryStereo/builder/pkgs/png.pkg =====
#SRC="http://prdownloads.sourceforge.net/libpng/libpng-1.2.35.tar.gz?download"
#MD5=8ca6246930a57d5be7adc7c4e7fb5e00
#===== /mnt/gentoo32/home/mike/BinaryStereo/builder/pkgs/proj.pkg =====
#SRC=http://download.osgeo.org/proj/proj-4.6.1.tar.gz
#MD5=7dbaab8431ad50c25669fd3fb28dc493
#===== /mnt/gentoo32/home/mike/BinaryStereo/builder/pkgs/stereo.pkg =====
#SRC=StereoPipeline-2.1.tar.gz
#MD5=334a43934769485ad5d1614a5c419e93
#
#PATCHES="patches/vw.pkg/0001-make-it-so-user-cflags-can-override-built-in-ones.patch"
#
#pkg_unpack() {
#    default_pkg_unpack
#    cd "$WORKDIR"
#    autoreconf --force --verbose --install
#
#    cat > "${WORKDIR}/config.options" << __EOF__
#ENABLE_DEBUG=ignore
#ENABLE_OPTIMIZE=ignore
#ENABLE_PROPER_LIBS=no
#ENABLE_PKG_PATHS_DEFAULT=no
#PKG_PATHS="$INSTALL_DIR $PWD/thirdparty/MBA-1.1"
#PREFIX=$INSTALL_DIR
#
##PKG_CLAPACK_LIBS=-Wl,-no-as-needed,-lclapack,-lblas,-lf2c,-lm,-as-needed
##PKG_SPICE_CPPFLAGS=-I/usr/include/cspice
#
#
#ENABLE_APP_STEREO=yes
#ENABLE_APP_POINT2MESH=yes
#ENABLE_APP_POINT2DEM=yes
#ENABLE_APP_DISPARITYDEBUG=yes
#
#ENABLE_APP_STEREOGUI=no
#ENABLE_APP_BUNDLEADJUST=no
#ENABLE_APP_ORBITVIZ=no
#ENABLE_APP_NURBS=no
#ENABLE_APP_CTXIMAGE=no
#ENABLE_APP_RMAX2CAHVOR=no
#ENABLE_APP_RMAXADJUST=no
#ENABLE_APP_BUNDLEVIS=no
#ENABLE_APP_ISISADJUST=no
#ENABLE_APP_CUDATEST=no
#ENABLE_APP_ORTHOPROJECT=no
#ENABLE_APP_POINT2MESH2=no
#ENABLE_APP_RESULTS=no
#
#
##checking for package OPENSCENEGRAPH... no (not found)
##checking for package MBA11... no (not found)
##checking for package MBA10... no (not found)
##checking for package MBA... no
##checking for package SPICE... no (not found)
##checking for qmake... /usr/bin/qmake
##checking for moc... /usr/bin/moc
##checking for uic... /usr/bin/uic
##checking for rcc... /usr/bin/rcc
##checking whether host operating system is Darwin... no
##checking whether we can build a simple Qt app... ko
##configure: WARNING: Cannot build a test Qt program
##checking for package QT_INCLUDE... no (missing QT)
##checking for package APPLE_QT... no
##checking for package QT_LIBS... yes
##checking for package QT_OPENGL... no (needs QT_INCLUDE)
##checking for package QT_GUI... no (needs QT_INCLUDE)
##checking for package QT_SQL... no (needs QT_INCLUDE)
##checking for package LINUX_QT... no (missing  QT_INCLUDE QT_GUI QT_OPENGL QT_SQL)
##checking for package QT... no
##checking for package APPLE_QWT... no
##checking for package PLAIN_QWT... no (needs QT_INCLUDE)
##checking for package SUFFX_QWT... no (needs QT_INCLUDE)
##checking for package QWT... no
##checking for package GSL_HASBLAS... no (not found)
##checking for package GSL_ASNEEDED... no (not found)
##checking for package GSL_NEEDBLAS... no (not found)
##checking for package GSL... no
##checking for package GEOS... no (not found)
##checking for package SUPERLU... no (not found)
##checking for package XERCESC... no (not found)
##checking for package ISIS3RDPARTY... no (needs SUPERLU)
##checking for package ISIS... no (needs QT)
##checking for package BOOST_COMMON... yes
##checking for package BOOST_ALL... yes
##checking for package VW_ALL... yes
#
#
#
#__EOF__
#}
#===== /mnt/gentoo32/home/mike/BinaryStereo/builder/pkgs/vw.pkg =====
#SRC=http://ti.arc.nasa.gov/m/project/nasa-vision-workbench/VisionWorkbench-2.0_beta3.tar.gz
#MD5=c3affabd6de9b2a6e0b62ab698c45461
#
#PATCHES="patches/vw.pkg/0001-make-it-so-user-cflags-can-override-built-in-ones.patch"
#
#pkg_unpack() {
#    default_pkg_unpack
#    cd "$WORKDIR"
#    autoreconf --force --verbose --install
#
#    cat > "${WORKDIR}/config.options" << __EOF__
#ENABLE_DEBUG=ignore
#ENABLE_OPTIMIZE=ignore
#ENABLE_PROPER_LIBS=no
#ENABLE_PKG_PATHS_DEFAULT=no
#PKG_PATHS=$INSTALL_DIR
#PREFIX=$INSTALL_DIR
#
#HAVE_PKG_TIFF=no
#HAVE_PKG_GL=no
#PKG_CLAPACK_LIBS=-Wl,-no-as-needed,-lclapack,-lblas,-lf2c,-lm,-as-needed
#__EOF__
#}
#===== /mnt/gentoo32/home/mike/BinaryStereo/builder/pkgs/zlib.pkg =====
#SRC=http://www.zlib.net/zlib-1.2.3.tar.gz
#MD5=debc62758716a169df9f62e6ab2bc634
#
#CONFIGURE_OPTIONS="--shared"
#
## These are all patches from gentoo
#PATCHES="\
#    patches/zlib.pkg/zlib-1.2.3-build.patch \
#    patches/zlib.pkg/zlib-1.2.3-visibility-support.patch \
#    patches/zlib.pkg/zlib-1.2.1-glibc.patch \
#    patches/zlib.pkg/zlib-1.2.1-build-fPIC.patch \
#    patches/zlib.pkg/zlib-1.2.1-configure.patch \
#    patches/zlib.pkg/zlib-1.2.1-fPIC.patch \
#    patches/zlib.pkg/zlib-1.2.3-r1-bsd-soname.patch \
#    patches/zlib.pkg/zlib-1.2.3-LDFLAGS.patch \
#"
#
class boost(Package):
    src    = 'http://downloads.sourceforge.net/boost/boost_1_39_0.tar.gz'
    chksum = 'fcc6df1160753d0b8c835d17fdeeb0a7'
#
#PATCHES="\
#    patches/boost.pkg/01_all_1.36.0-tools-build-fix.patch \
#    patches/boost.pkg/02_all_1.37.0-function-templates-compile-fix.patch \
#    patches/boost.pkg/03_all_1.36.0-compiler_status-trailing_slash.patch \
#    patches/boost.pkg/07_all_1.35.0-fix_mpi_installation.patch \
#    patches/boost.pkg/remove_toolset_from_targetname.patch \
#"
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
#===== /mnt/gentoo32/home/mike/BinaryStereo/builder/pkgs/clapack.pkg =====
#SRC=http://ti.arc.nasa.gov/m/project/nasa-vision-workbench/VisionWorkbench-LAPACK.tar.gz
#MD5=6795ab8af24bdd87476b4f2681bd3bee
#
#PATCHES="\
#    patches/clapack.pkg/0001-configure-changes.patch \
#    patches/clapack.pkg/0002-missing-libs-to-get-rid-of-undefined-symbols.patch \
#    patches/clapack.pkg/0003-make-sure-m4-exists.patch \
#"
#
#CONFIGURE_OPTIONS="--enable-debug=ignore --enable-optimize=ignore"
#
#pkg_unpack() {
#    default_pkg_unpack
#    cd "$WORKDIR"
#    autoreconf --force --verbose --install
#}

if __name__ == '__main__':
    e = Environment(CC='ccache gcc', CXX='ccache g++')
    gdal(e).all(e)
