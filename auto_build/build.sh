#!/bin/bash

# Build ASP. On any faiulre, ensure the "Fail" flag is set in $statusBuildFile,
# otherwise the caller will wait forever.

if [ "$#" -lt 2 ]; then echo Usage: $0 buildDir statusBuildFile; exit 1; fi

if [ -x /usr/bin/zsh ] && [ "$MY_BUILD_SHELL" = "" ]; then
    # Use zsh if available, that helps with compiling on pfe,
    # more specifically with ulmit.
    export MY_BUILD_SHELL=zsh
    exec /usr/bin/zsh $0 $*
fi

buildDir=$1
statusBuildFile=$2

cd $HOME
if [ ! -d "$buildDir" ]; then
    echo "Error: Directory: $buildDir does not exist"
    echo "Fail build_failed" > $statusBuildFile
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
if [ -f /usr/bin/gcc44 ] && [ -f /usr/bin/g++44 ]; then
    rm -f gcc; ln -s /usr/bin/gcc44 gcc
    rm -f g++; ln -s /usr/bin/g++44 g++
    export PATH=$(pwd):$PATH
fi
which gcc; which git; gcc --version; python --version

# Rebuild the dependencies first (only the ones whose chksum changed
# will get rebuilt)
echo "Will build dependencies"
rm -f ./BaseSystem*bz2 ./StereoPipeline*bz2
./build.py --download-dir $(pwd)/tarballs --dev-env --resume \
    --build-root $(pwd)/build_deps
if [ "$?" -ne 0 ]; then echo "Fail build_failed" > $statusBuildFile; exit 1; fi
./make-dist.py --include all --set-name BaseSystem last-completed-run/install
if [ "$?" -ne 0 ]; then echo "Fail build_failed" > $statusBuildFile; exit 1; fi

echo "Will build ASP"
rm -rf $(pwd)/build_asp
base_system=$(ls -trd BaseSystem* |tail -n 1)
./build.py --download-dir $(pwd)/tarballs --base $base_system \
    visionworkbench stereopipeline --build-root $(pwd)/build_asp
if [ "$?" -ne 0 ]; then echo "Fail build_failed" > $statusBuildFile; exit 1; fi

if [ "$(uname -n)" = "zula" ]; then
    echo "Will build the documentation"
    rm -fv dist-add/asp_book.pdf
    cd build_asp/build/stereopipeline/stereopipeline-git/docs/book
    make
    gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/ebook -dNOPAUSE -dQUIET -dBATCH -sOutputFile=output.pdf asp_book.pdf
    mv -f output.pdf $HOME/$buildDir/dist-add/asp_book.pdf
    cd $HOME/$buildDir
fi

./make-dist.py last-completed-run/install
if [ "$?" -ne 0 ]; then echo "Fail build_failed" > $statusBuildFile; exit 1; fi

# Copy the build to asp_tarballs
asp_tarball=$(ls -trd StereoPipeline*bz2 | grep -i -v debug | tail -n 1)
if [ "$asp_tarball" = "" ]; then echo "Fail build_failed" > $statusBuildFile; exit 1; fi
mkdir -p asp_tarballs
mv $asp_tarball asp_tarballs
asp_tarball=asp_tarballs/$asp_tarball

# Wipe old builds
numKeep=12
if [ "$(uname -n | grep centos)" != "" ]; then
    numKeep=4 # these machines have little storage
fi
./auto_build/rm_old.sh asp_tarballs $numKeep

# Mark the build as finished. This must happen at the very end,
# otherwise the parent script will take over before this script finished.
echo "$asp_tarball build_done Success" > $statusBuildFile
