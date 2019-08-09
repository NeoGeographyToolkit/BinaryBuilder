#!/bin/bash

# Unzip a tarball, rename it to remove the time stamp,
# and zip it back. Thus transform
# StereoPipeline-2.3.0-2013-11-13-x86_64-Linux-GLIBC-2.5.tar.bz2
# into
# StereoPipeline-2.3.0-x86_64-Linux-GLIBC-2.5.tar.bz2

if [ "$#" -lt 1 ]; then echo Usage: $0 tarball; exit; fi

tarball=$1

if [[ ! $tarball =~ \.tar\.bz2$ ]]; then
    echo Expecting $tarball to be a .tar.bz2 archive
    exit 1
fi

tarballDir=$(dirname $tarball)
tarballNameIn=$(basename $tarball)
cd $tarballDir

tarballNameOut=$(echo $tarballNameIn | perl -p -e "s#\d\d\d\d-\d+-\d+-##g")

# Names without the .tar.bz2 extension
in=${tarballNameIn/.tar.bz2/}
out=${tarballNameOut/.tar.bz2/}
rm -rf $in $out

bzip2 -dc $tarballNameIn | tar xfv - > /dev/null 2>&1
if [ "$?" -ne 0 ]; then echo "Unpacking failed"; exit 1; fi

mv $in $out

tar cf $tarballNameOut --use-compress-prog=pbzip2 $out
if [ "$?" -ne 0 ]; then echo "Packing back failed"; exit 1; fi

rm -rf $in $out

echo Renamed $tarballDir/$tarballNameIn to $tarballDir/$tarballNameOut


