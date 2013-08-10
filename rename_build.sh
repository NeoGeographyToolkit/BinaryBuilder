#!/bin/bash

# Rename a build to follow ASP conventions.
# This code must print to STDOUT just one statement,
# the final build name.

if [ "$#" -lt 3 ]; then echo Usage: $0 build version timestamp; exit; fi

in_z=$1 # expecting a tar.bz2 file here
version=$2
timestamp=$3

# Go to asp_tarballs and make things relative to that directory
if [ ! -d "asp_tarballs" ]; then
    echo directory asp_tarballs does not exist; exit 1;
fi
cd asp_tarballs
in_z=${in_z/asp_tarballs\//}

out_z=$in_z
if [ "$(echo $in_z | grep -i Darwin)" != "" ]; then
    out_z=StereoPipeline-$version-$timestamp-x86_64-OSX.tar.bz2
fi
if [ "$(echo $in_z | grep -i x86_64-redhat)" != "" ]; then
    out_z=StereoPipeline-$version-$timestamp-x86_64-Linux-GLIBC-2.5.tar.bz2
fi
if [ "$(echo $in_z | grep -i x86_32-redhat)" != "" ]; then # test this!
    out_z=StereoPipeline-$version-$timestamp-i686-Linux-GLIBC-2.5.tar.bz2
fi
if [ "$(echo $in_z | grep -i Ubuntu13)" != "" ]; then
    out_z=StereoPipeline-$version-$timestamp-x86_64-Linux-GLIBC-2.17.tar.bz2
fi
if [ "$(echo $in_z | grep -i SuSE11)" != "" ]; then
    out_z=StereoPipeline-$version-$timestamp-x86_64-Linux-SuSE.tar.bz2
fi

in=${in_z/.tar.bz2/}
out=${out_z/.tar.bz2/}

rm -rf $in $out
bzip2 -dc $in_z | tar xfv - > /dev/null 2>&1
mv $in $out
cp -f ../dist-add/asp_book.pdf $out # Copy the ASP book
tar cf $out_z --use-compress-prog=pbzip2 $out
rm -rf $in

echo asp_tarballs/$out_z
