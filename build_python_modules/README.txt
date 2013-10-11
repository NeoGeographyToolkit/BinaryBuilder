To compile and install the Python modules needed by the Ames Stereo
Pipeline Python dependencies (such as sparse_disp), run the script:

./build_python_modules.sh <INSTALL DIRECTORY>

This install directory should be separate from the Stereo Pipeline
install directory, as to not overwrite its libraries. 

The script will print at the end the value of the environmental
variable ASP_PYTHON_MODULES_PATH which needs to be set before running
the Stereo Pipeline.
