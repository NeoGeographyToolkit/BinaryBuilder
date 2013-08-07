#!/bin/bash

# Build ASP. On any faiulre, ensure the "Fail" flag is set in $doneFile.

if [ "$#" -lt 2 ]; then echo Usage: $0 buildDir doneFile; exit 1; fi

if [ -x /usr/bin/zsh ] && [ "$MY_BUILD_SHELL" = "" ]; then
    # Use zsh if available, that helps with compiling on pfe,
    # more specifically with ulmit.
    export MY_BUILD_SHELL=zsh
    exec /usr/bin/zsh $0 $*
fi

buildDir=$1
doneFile=$2
DEPS_BUILD=deps_build
ASP_BUILD=asp_build

cd $HOME
msg="Error: Directory: $buildDir does not exist"
if [ ! -d "$buildDir" ]; then echo $msg; echo Fail > $doneFile; exit 1; fi
cd $buildDir

# Paths to newest python and to git
export PATH=/nasa/python/2.7.3/bin/:/nasa/sles11/git/1.7.7.4/bin/:$HOME/projects/packages/bin/:$PATH

# These are needed primarily for pfe
ulimit -s unlimited 2>/dev/null
ulimit -f unlimited 2>/dev/null
ulimit -v unlimited 2>/dev/null
ulimit -u unlimited 2>/dev/null

# These are needed for centos-32-5 and 64-5
if [ -f /usr/bin/gcc44 ] && [ -f /usr/bin/g++44 ]; then
    rm -f gcc; ln -s /usr/bin/gcc44 gcc
    rm -f g++; ln -s /usr/bin/g++44 g++
    export PATH=$(pwd):$PATH
fi
which gcc; which git; gcc --version; python --version

# Get a fresh BinaryBuilder first
rm -rf tmp
#git clone https://github.com/NeoGeographyToolkit/BinaryBuilder.git tmp
if [ "$?" -ne 0 ]; then exit 1; fi
cp -rf tmp/.git* .; cp -rf tmp/* .; rm -rf tmp

# Rebuild the dependencies first (only the ones whose chksum changed
# will get rebuilt)
echo "Will build dependencies"
./build.py --download-dir $(pwd)/tarballs --dev-env --resume --build-root $(pwd)/$DEPS_BUILD
if [ "$?" -ne 0 ]; then; echo Fail > $doneFile; exit 1; fi
rm -f BaseSystem* StereoPipeline*
./make-dist.py --include all --set-name BaseSystem last-completed-run/install
if [ "$?" -ne 0 ]; then echo Fail > $doneFile; exit 1; fi

echo "Will build ASP"
rm -rf $(pwd)/$ASP_BUILD
base_system=$(ls -trd BaseSystem* |tail -n 1)
./build.py --download-dir $(pwd)/tarballs --base $base_system \
    visionworkbench stereopipeline --build-root $(pwd)/$ASP_BUILD
if [ "$?" -ne 0 ]; then echo Fail > $doneFile; exit 1; fi
./make-dist.py last-completed-run/install
if [ "$?" -ne 0 ]; then echo Fail > $doneFile; exit 1; fi

# Mark the build as finished
build=$(ls -trd StereoPipeline*bz2 | grep -i -v debug | tail -n 1)
if [ "$build" = "" ]; then echo Fail > $doneFile; exit 1; fi
echo $build > $doneFile
