#!/bin/bash

# Remove all but several newest files in given directory

if [ "$#" -lt 2 ]; then echo Usage: $0 rmFromDir numLeft; exit; fi

dir=$1
numLeft=$2

if [ ! -d "$dir" ]; then echo Missing directory: $dir; exit 1; fi

num=$(ls -trd $dir/* |wc | awk '{print $1}')
echo num is $num

((stop=num-numLeft))

count=0
for f in $(ls -trd $dir/*); do
    ((count++))
    if [ $count -le $stop ]; then
        echo Wiping ./$f
        rm -rf ./$f
    fi
done
