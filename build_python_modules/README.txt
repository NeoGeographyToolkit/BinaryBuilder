To compile and install the Python modules needed by the Ames Stereo Pipeline
Python dependencies (such as sparse_disp), run the script:

./build_python_modules.sh <INSTALL DIRECTORY>

This install directory should be separate from the Stereo Pipeline install
directory, as to not overwrite its libraries. 

The script will print at the end the value of the environmental variable
ASP_PYTHON_MODULES_PATH which needs to be set before running the Stereo
Pipeline.

Required software:
 - gcc, g++, gfortran
 - cmake, version >= 2.8.7
 - Python, version >= 2.6
 - python-devel
 
Installed packages:
 - blas/lapack
 - numpy
 - scipy
 - geos
 - proj4
 - gdal
 - simplekml


Note that this script is an alternative to setting up your own Python
environment.  The Conda software (https://conda.io/docs/index.html)
provides an easy way to set up a python environment for ASP.  It has
been tested on Ubuntu 16.04 with the following additional packages
installed:

scipy=1.0.0
numpy=1.14.0
simplekml=1.3.0
pyfftw=0.10.4
proj4=4.9.3
gdal=2.2.2
geos=3.6.2
blas=1.0


Note that the simplekml and pyfftw packages needed the argument
"-c conda-forge" added to their "conda install" command.
