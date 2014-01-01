#!/bin/bash

function compute_python_path () {
    installDir=$1
    dir1=$(ls -d $installDir/lib/python*/site-packages 2>/dev/null | head -n 1)
    dir2=$(ls -d $installDir/lib64/python*/site-packages 2>/dev/null | head -n 1)
    dir3=$(ls -d $installDir/swig/python 2>/dev/null | head -n 1)
    dir4=$(dirname $(find $installDir -name _gdal.so | grep -v archive | head -n 1))
    echo "$dir1:$dir2:$dir3:$dir4:$installDir/lib" | perl -pi -e "s#^:*##g" | \
        perl -pi -e "s#:*\$##g" | perl -pi -e "s#:+#:#g"
}


# Find the absolute path of installDir
if [ "$#" -lt 1 ]; then echo Usage: $0 '<installation directory>'; exit; fi
installDir=$1
mkdir -p $installDir
if [ "$?" -ne 0 ]; then exit 1; fi
currDir=$(pwd)
cd $installDir
installDir=$(pwd)
cd $currDir

n_cpu=$(grep -c ^processor /proc/cpuinfo 2>/dev/null)
if [ "$n_cpu" = "" ]; then n_cpu=2; fi
echo Will use $n_cpu processes

buildDir=$(pwd)/build_python
mkdir -p $buildDir
if [ "$?" -ne 0 ]; then exit 1; fi

# Find gfortran
gfortran=$(which gfortran)
if [ "$gfortran" = "" ]; then 
    dirs=$(echo $PATH | perl -pi -e "s#:# #g")
    for dir in $dirs; do
        val=$(ls $dir/gfortran* 2>/dev/null | head -n 1)
        if [ "$val" != "" ]; then
            gfortran=$val
            break
        fi
    done
fi
if [ "$gfortran" = "" ]; then 
    echo "ERROR: Cannot find gfortran"
    exit 1
fi

# If gfortran is named gfortran-mp-4.8 or so, create a symlink to gfortran,
# otherwise the numpy build gets confused later
gfortran2=$(dirname $gfortran)/gfortran
if [ "$gfortran2" != "$gfortran" ]; then
    gfortran2=$buildDir/gfortran
    ln -s $gfortran $gfortran2
    gfortran=$gfortran2
    export PATH=$buildDir:$PATH
fi

# install blas/lapack
cd $buildDir
file=lapack-3.4.2.tgz
if [ ! -f "$file" ]; then
    wget http://www.netlib.org/lapack/$file
fi
tar xzfv $file
cd lapack-3.4.2
rm -rf build
mkdir -p build
cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$installDir -DCMAKE_Fortran_FLAGS:STRING="-fPIC" -DBUILD_SHARED_LIBS:BOOL=ON -DCMAKE_Fortran_COMPILER=$gfortran
if [ "$?" -ne 0 ]; then exit 1; fi
make -j $n_cpu
if [ "$?" -ne 0 ]; then exit 1; fi
make install
if [ "$?" -ne 0 ]; then exit 1; fi

# Install numpy
cd $buildDir
rm -rf numpy-1.7.0
file=numpy-1.7.0.tar.gz
if [ ! -f "$file" ]; then
    wget http://downloads.sourceforge.net/project/numpy/NumPy/1.7.0/$file
fi
tar xzfv $file
if [ "$?" -ne 0 ]; then exit 1; fi
cd numpy-1.7.0
python setup.py build --fcompiler=gnu95
if [ "$?" -ne 0 ]; then exit 1; fi
python setup.py install --prefix=$installDir
if [ "$?" -ne 0 ]; then exit 1; fi

# Install scipy
p=$(compute_python_path $installDir);
export PYTHONPATH=$p # refresh the python path
cd $buildDir
export BLAS_SRC=$buildDir/lapack-3.4.2/BLAS/SRC
export BLAS=$installDir
export LAPACK_SRC=$buildDir/lapack-3.4.2
export LAPACK=$installDir
rm -rf scipy-0.12.0
file=scipy-0.12.0.tar.gz
if [ ! -f "$file" ]; then
    wget --no-check-certificate https://pypi.python.org/packages/source/s/scipy/$file
fi
tar xzfv $file
cd scipy-0.12.0
python setup.py build --fcompiler=gnu95
if [ "$?" -ne 0 ]; then exit 1; fi
python setup.py install --prefix=$installDir
if [ "$?" -ne 0 ]; then exit 1; fi

# install geos
cd $buildDir
p=$(compute_python_path $installDir)
export PYTHONPATH=$p # refresh the python path
rm -rf geos-3.4.2
file=geos-3.4.2.tar.bz2
if [ ! -f "$file" ]; then
    wget http://download.osgeo.org/geos/$file
fi
tar jxf $file
cd geos-3.4.2
./configure --enable-static --prefix=$installDir
if [ "$?" -ne 0 ]; then exit 1; fi
make -j $n_cpu
if [ "$?" -ne 0 ]; then exit 1; fi
make install
if [ "$?" -ne 0 ]; then exit 1; fi

# Install proj4
cd $buildDir
p=$(compute_python_path $installDir)
export PYTHONPATH=$p # refresh the python path
rm -rf proj-4.8.0
file=proj-4.8.0.tar.gz
if [ ! -f "$file" ]; then
    wget http://download.osgeo.org/proj/$file
fi
tar xzfv $file
cd proj-4.8.0
./configure --enable-static --without-jni --prefix=$installDir
if [ "$?" -ne 0 ]; then exit 1; fi
make -j $n_cpu
if [ "$?" -ne 0 ]; then exit 1; fi
make install
if [ "$?" -ne 0 ]; then exit 1; fi

# Install gdal
cd $buildDir
p=$(compute_python_path $installDir)
export PYTHONPATH=$p # refresh the python path
rm -rf gdal-1.10.0
file=gdal-1.10.0.tar.gz
if [ ! -f "$file" ]; then
    wget http://download.osgeo.org/gdal/1.10.0/$file
fi
tar xzfv $file
cd gdal-1.10.0
./configure --enable-static --with-threads --with-libtiff --with-geotiff=internal --with-jpeg --with-png --with-zlib --with-pam --with-geos=$installDir/bin/geos-config --without-bsb --without-cfitsio --without-curl --without-dods-root --without-dwg-plt --without-dwgdirect --without-ecw --without-epsilon --without-expat --without-expat-inc --without-expat-lib --without-fme --without-gif --without-grass --without-hdf4 --without-hdf5 --without-idb --without-ingres --without-jasper --without-jp2mrsid --without-kakadu --without-libgrass --without-macosx-framework --without-mrsid --without-msg --without-mysql --without-netcdf --without-oci --without-oci-include --without-oci-lib --without-odbc --without-ogdi --without-pcidsk --without-pcraster --without-perl --without-pg --without-php --without-ruby --without-sde --without-sde-version --without-spatialite --without-sqlite3 --without-xerces --without-xerces-inc --without-xerces-lib --without-libiconv-prefix --without-libiconv --without-xml2 --without-pcre --without-freexl --with-python=yes --prefix=$installDir
if [ "$?" -ne 0 ]; then exit 1; fi
make -j $n_cpu
if [ "$?" -ne 0 ]; then exit 1; fi
make install # this will fail but we'll go on
cd swig/python
python setup.py install --prefix=$installDir
if [ "$?" -ne 0 ]; then exit 1; fi

p=$(compute_python_path $installDir);
export PYTHONPATH=$p # refresh the python path

echo ""
echo ""
echo "***********************************************"
echo ""
echo "Done! Please be sure to set the following environmental variable before running Stereo Pipeline:"
echo ""
echo export ASP_PYTHON_MODULES_PATH=$PYTHONPATH
echo ""
echo "***********************************************"
echo ""
echo ""

exit 0
