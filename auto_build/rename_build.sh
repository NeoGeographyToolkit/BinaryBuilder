#!/bin/bash

# Rename a build to follow ASP conventions.
# This code must print to STDOUT just one statement,
# the final build name.

# TODO(oalexan1): This should not be necessary. Must ensure that
# BinaryBuilder always produces builds with the right name.

if [ "$#" -lt 3 ]; then echo Usage: $0 build version timestamp; exit; fi

in_z=$1
version=$2
timestamp=$3

if [[ ! $in_z =~ \.tar\.bz2$ ]]; then
    echo Expecting $in_z to be a .tar.bz2 archive
    exit 1
fi

# Go to asp_tarballs and make things relative to that directory
if [ ! -d "asp_tarballs" ]; then
    echo directory asp_tarballs does not exist; exit 1;
fi
cd asp_tarballs
in_z=${in_z/asp_tarballs\//}

out_z=$in_z
if [ "$(echo $in_z | grep -i -E 'OSX|Darwin')" != "" ]; then
    out_z=StereoPipeline-$version-$timestamp-x86_64-OSX.tar.bz2
else
    if [ "$(echo $in_z | grep -i x86_64)" != "" ]; then
	out_z=StereoPipeline-$version-$timestamp-x86_64-Linux.tar.bz2
    fi
fi

in=${in_z/.tar.bz2/}
out=${out_z/.tar.bz2/}

# Unpack
rm -rf $in $out
if [ -d "$in" ] || [ -d "$out" ]; then exit 1; fi # could not wipe
bzip2 -dc $in_z | tar xfv - > /dev/null 2>&1
if [ "$?" -ne 0 ]; then echo "Unpacking failed"; exit 1; fi
if [ "$in" != "$out" ]; then 
    cp -rf $in $out # make a copy, keep the original
fi

# Pack back
tar cjf $out_z $out
if [ "$?" -ne 0 ]; then echo "Packing back failed"; exit 1; fi

# Remove the extracted version of the output build, but keep the
# extracted version of the input build, for forensic analysis.
# Old builds will be removed later.
rm -rf $out

# The last line printed by this shell script must be the name of the output build
echo asp_tarballs/$out_z

