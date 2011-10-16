Common subdirectories: lapack-3.2.1/BLAS and lapack-3.2.1.new/BLAS
diff -u lapack-3.2.1/configure.ac lapack-3.2.1.new/configure.ac
--- lapack-3.2.1/configure.ac	2011-10-16 11:31:28.000000000 -0700
+++ lapack-3.2.1.new/configure.ac	2011-10-16 11:34:41.000000000 -0700
@@ -2,6 +2,8 @@
 AC_INIT([lapack], [3.2.1], [lapack@cs.utk.edu])
 AM_INIT_AUTOMAKE([foreign])
 
+AC_CONFIG_MACRO_DIR([m4])
+
 dnl AC_LANG(Fortran 77)
 AC_PROG_F77
 AC_PROG_LIBTOOL
Common subdirectories: lapack-3.2.1/INSTALL and lapack-3.2.1.new/INSTALL
Only in lapack-3.2.1.new: m4
diff -u lapack-3.2.1/Makefile.am lapack-3.2.1.new/Makefile.am
--- lapack-3.2.1/Makefile.am	2011-10-16 11:31:28.000000000 -0700
+++ lapack-3.2.1.new/Makefile.am	2011-10-16 11:33:38.000000000 -0700
@@ -1,5 +1,7 @@
 SUBDIRS = INSTALL SRC
 
+ACLOCAL_AMFLAGS = -I m4
+
 pkgconfigdir = $(libdir)
 pkgconfig_DATA = lapack.pc
 
Common subdirectories: lapack-3.2.1/SRC and lapack-3.2.1.new/SRC
Common subdirectories: lapack-3.2.1/TESTING and lapack-3.2.1.new/TESTING
