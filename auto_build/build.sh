#!/bin/bash

# Build ASP. On any failure, ensure the "Fail" flag is set in
# $statusFile on the calling machine, otherwise the caller will wait
# forever.

# On success, copy back to the master machine the built tarball and
# set the status.

if [ "$#" -lt 3 ]; then
    echo Usage: $0 buildDir statusFile masterMachine
    exit 1
fi

if [ -x /usr/bin/zsh ] && [ "$MY_BUILD_SHELL" = "" ]; then
    # Use zsh if available, that helps with compiling on pfe,
    # more specifically with ulmit.
    export MY_BUILD_SHELL=zsh
    exec /usr/bin/zsh $0 $*
fi

buildDir=$1
statusFile=$2
masterMachine=$3

cd $HOME
if [ ! -d "$buildDir" ]; then
    echo "Error: Directory: $buildDir does not exist"
    echo "Fail build_failed" > $buildDir/$statusFile
    exit 1
fi
cd $buildDir

# Set path and load utilities
source $HOME/$buildDir/auto_build/utils.sh

# These are needed primarily for pfe
ulimit -s unlimited 2>/dev/null
ulimit -f unlimited 2>/dev/null
ulimit -v unlimited 2>/dev/null
ulimit -u unlimited 2>/dev/null

rm -fv ./BaseSystem*bz2
rm -fv ./StereoPipeline*bz2

# Set the ISIS env, needed for 'make check' in ASP. Do this only
# on the Mac, as on other platforms we lack
# all the needed ISIS data.
isMac=$(uname -a|grep Darwin)
if [ "$isMac" != "" ]; then
    isis=$(isis_file)
    if [ -f "$isis" ]; then
        . "$isis"
    else
        echo "Warning: Could not set up the ISIS environment."
    fi
fi

# Dump the environmental variables
env

# Init the status file
echo "NoTarballYet now_building" > $HOME/$buildDir/$statusFile

# Build everything, including VW and ASP. Only the packages
# whose checksum changed will get built.
echo "Building changed packages"
opt=""
if [ "$(uname -n | grep centos7)" != "" ]; then
    # Use gcc 5 on centos7
    opt="--cxx=/home/pipeline/projects/gcc5/bin/g++ --cc=/home/pipeline/projects/gcc5/bin/gcc --gfortran=/home/pipeline/projects/gcc5/bin/gfortran --threads 2"
fi
cmd="./build.py $opt --skip-tests"
echo $cmd
eval $cmd
exitStatus=$?

echo "Build status is $exitStatus"
if [ "$exitStatus" -ne 0 ]; then
    echo "Fail build_failed" > $HOME/$buildDir/$statusFile
    exit 1
fi

buildMachine=$(machine_name)
if [ "$(uname -n | grep centos7)" != "" ]; then
    # Build the documentation on the machine which has LaTeX
    echo "Will build the documentation"
    rm -fv dist-add/asp_book.pdf
    cd build_asp/build/stereopipeline/stereopipeline-git/build_binarybuilder
    rm -fv ../docs/book/asp_book.pdf

    # Must temporarily set LD_LIBRARY_PATH so cmake does not complain.
    # It likely will cause issues if this is set globally.
    orig_path=$LD_LIBRARY_PATH
    export LD_LIBRARY_PATH=$HOME/projects/BinaryBuilder/build_asp/install/lib:$LD_LIBRARY_PATH
    make workbook
    export LD_LIBRARY_PATH=$orig_path
    
    # Copy the documentation to the master machine
    echo Copying the documentation to $masterMachine
    rsync -avz ../docs/book/asp_book.pdf \
          $masterMachine:$buildDir/dist-add/ 2>/dev/null

    cd $HOME/$buildDir
fi

# Dump the ASP version
versionFile=$(version_file $buildMachine)
echo "Dumping the version to file: $versionFile"
build_asp/install/bin/stereo -v 2>/dev/null | grep "NASA Ames Stereo Pipeline" | awk '{print $5}' >  $versionFile

# Make sure all maintainers can access the files.
# - These commands fail on the VM but that is OK because we don't need them to work on that machine.
chown -R  :ar-gg-ti-asp-maintain $HOME/$buildDir
chmod -R g+rw $HOME/$buildDir

echo "Making the distribution..."
./make-dist.py last-completed-run/install
if [ "$?" -ne 0 ]; then
    echo "Fail build_failed" > $HOME/$buildDir/$statusFile
    exit 1
fi

# Copy the build to asp_tarballs
echo "Moving to asp_tarballs..."
asp_tarball=$(ls -trd StereoPipeline*bz2 | grep -i -v debug | tail -n 1)
if [ "$asp_tarball" = "" ]; then
    echo "Fail build_failed" > $HOME/$buildDir/$statusFile
    exit 1
fi
mkdir -p asp_tarballs
mv $asp_tarball asp_tarballs
asp_tarball=asp_tarballs/$asp_tarball

# Wipe old builds on the build machine
echo "Cleaning old builds..."
numKeep=8
if [ "$(echo $buildMachine | grep $masterMachine)" != "" ]; then
    numKeep=24 # keep more builds on master machine
fi
$HOME/$buildDir/auto_build/rm_old.sh $HOME/$buildDir/asp_tarballs $numKeep

rm -f StereoPipeline*debug.tar.bz2

# Mark the build as finished. This must happen at the very end,
# otherwise the parent script will take over before this script finished.
echo "$asp_tarball build_done Success" > $HOME/$buildDir/$statusFile

# Last time make sure the permissions are right
chown -R  :ar-gg-ti-asp-maintain $HOME/$buildDir
chmod -R g+rw $HOME/$buildDir

echo "Finished running build.sh locally!"
