#!/bin/bash

# Build ASP. On any failure, ensure the "Fail" flag is set in
# $statusFile on the calling machine, otherwise the caller will wait
# forever.

# On success, copy back to the master machine the built tarball and
# set the status.

if [ "$#" -lt 4 ]; then
    echo Usage: $0 buildDir statusFile masterMachine userName
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
userName=$4

cd $HOME
if [ ! -d "$buildDir" ]; then
    echo "Error: Directory: $buildDir does not exist"
    ssh $masterMachine "echo 'Fail build_failed' > $buildDir/$statusFile" \
        2>/dev/null
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

# Build everything, including VW and ASP. Only the packages
# whose checksum changed will get built.
echo "Building changed packages"
./build.py
status="$?"
echo "Build status is $status"
if [ "$status" -ne 0 ]; then
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

echo "Making the distribution..."
./make-dist.py last-completed-run/install
if [ "$?" -ne 0 ]; then
    ssh $masterMachine "echo 'Fail build_failed' > $buildDir/$statusFile" \
        2>/dev/null
    exit 1
fi

# Copy the build to asp_tarballs
echo "Moving to asp_tarballs..."
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
echo "Cleaning old builds..."
numKeep=8
if [ "$(echo $buildMachine | grep $masterMachine)" != "" ]; then
    numKeep=24 # keep more builds on master machine
fi
$HOME/$buildDir/auto_build/rm_old.sh $HOME/$buildDir/asp_tarballs $numKeep

rm -f StereoPipeline*debug.tar.bz2

# Copy the build to the master machine
echo "Copying back to lunokhod1..."
rsync -avz $asp_tarball $masterMachine:$buildDir/asp_tarballs \
        2>/dev/null

# Mark the build as finished. This must happen at the very end,
# otherwise the parent script will take over before this script finished.
# - We need to make sure we SSH back as the correct user!
echo "Sending status to lunokhod1..."
ssh -v $userName@$masterMachine \
    "echo '$asp_tarball build_done Success' > $buildDir/$statusFile" # \
#    2>/dev/null
echo "ssh $userName@$masterMachine echo '$asp_tarball build_done Success' > $buildDir/$statusFile 2>/dev/null"


echo "Finished running build.sh locally!"
