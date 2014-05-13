#!/bin/bash

# Remove all but several newest directories/files in given directory.
# WARNING: This script can remove ENTIRE DIRECTORIES! Use with care!

if [ "$#" -lt 2 ]; then echo Usage: $0 rmFromDir numLeft; exit; fi

dir=$1
numLeft=$2
prefix=$3  # rm file starting with this prefix

if [ ! -d "$dir" ]; then echo Missing directory: $dir; exit 1; fi

# A precaution, don't remove current dir
if [ "${dir:0:1}" = "." ] || [ "$dir" = "$(pwd)" ];
    then echo Error: Cannot remove $dir
    exit 1
fi

num=$(ls -trd $dir/* |wc | awk '{print $1}')
((stop=num-numLeft))

# A precaution, don't remove all files
if [ "$stop" -eq "$num" ]; then
    echo Error: Cannot remove all files
    exit 1
fi

count=0
for f in $(ls -trd $dir/$prefix*); do
    ((count++))
    if [ $count -le $stop ]; then
        echo Removing $f
        rm -rf $f
    fi
done

