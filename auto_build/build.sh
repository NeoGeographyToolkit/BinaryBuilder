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
    ssh $masterMachine "echo 'Fail build_failed' > $buildDir/$statusFile" \
        2>/dev/null
    exit 1
fi
cd $buildDir

. $HOME/$buildDir/auto_build/utils.sh # load utilities
set_system_paths

# These are needed primarily for pfe
ulimit -s unlimited 2>/dev/null
ulimit -f unlimited 2>/dev/null
ulimit -v unlimited 2>/dev/null
ulimit -u unlimited 2>/dev/null

# These are needed for centos-32-5 and 64-5
if [ -f /usr/bin/gcc44 ] && [ -f /usr/bin/g++44 ] && \
    [ -f /usr/bin/gfortran44 ]; then
    rm -f gcc; ln -s /usr/bin/gcc44 gcc
    rm -f g++; ln -s /usr/bin/g++44 g++
    rm -f gfortran; ln -s /usr/bin/gfortran44 gfortran
    export PATH=$(pwd):$PATH
fi

rm -fv ./BaseSystem*bz2
rm -fv ./StereoPipeline*bz2

# Set the ISIS env, needed for 'make check' in ASP
isis=$(isis_file)
if [ -f "$isis" ]; then
    . "$isis"
    env
else
    echo "Error: Cannot find $isis"
    ssh $masterMachine "echo 'Fail build_failed' > $buildDir/$statusFile" \
        2>/dev/null
    exit 1
fi

# Build everything, including VW and ASP. Only the packages
# whose checksum changed will get built.
echo "Building changed packages"
./build.py
if [ "$?" -ne 0 ]; then
    ssh $masterMachine "echo 'Fail build_failed' > $buildDir/$statusFile" \
        2>/dev/null
    exit 1
fi

buildMachine=$(machine_name)
if [ "$buildMachine" = "lunokhod1" ]; then
    # Build the documentation on the machine which has LaTeX
    echo "Will build the documentation"
    rm -fv dist-add/asp_book.pdf
    cd build_asp/build/stereopipeline/stereopipeline-git/docs/book
    rm -fv asp_book.pdf
    make

    # Copy the documentation to the master machine
    echo Copying the documentation to $masterMachine
    rsync -avz asp_book.pdf $masterMachine:$buildDir/dist-add/ \
        2>/dev/null

    cd $HOME/$buildDir
fi

# Dump the ASP version
versionFile=$(version_file $buildMachine)
build_asp/install/bin/stereo -v 2>/dev/null | grep "NASA Ames Stereo Pipeline" | awk '{print $5}' >  $versionFile

./make-dist.py last-completed-run/install
if [ "$?" -ne 0 ]; then
    ssh $masterMachine "echo 'Fail build_failed' > $buildDir/$statusFile" \
        2>/dev/null
    exit 1
fi

# Copy the build to asp_tarballs
asp_tarball=$(ls -trd StereoPipeline*bz2 | grep -i -v debug | tail -n 1)
if [ "$asp_tarball" = "" ]; then
    ssh $masterMachine "echo 'Fail build_failed' > $buildDir/$statusFile" \
        2>/dev/null
    exit 1
fi
mkdir -p asp_tarballs
mv $asp_tarball asp_tarballs
asp_tarball=asp_tarballs/$asp_tarball

# Wipe old builds on the build machine
numKeep=8
if [ "$(echo $buildMachine | grep $masterMachine)" != "" ]; then
    numKeep=24 # keep more builds on master machine
fi
$HOME/$buildDir/auto_build/rm_old.sh $HOME/$buildDir/asp_tarballs $numKeep

rm -f StereoPipeline*debug.tar.bz2

# Copy the build to the master machine
rsync -avz $asp_tarball $masterMachine:$buildDir/asp_tarballs \
        2>/dev/null

# Mark the build as finished. This must happen at the very end,
# otherwise the parent script will take over before this script
# finished.
ssh $masterMachine \
    "echo '$asp_tarball build_done Success' > $buildDir/$statusFile" \
    2>/dev/null
