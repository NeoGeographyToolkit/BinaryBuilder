#!/bin/bash

# Before we launch any job on a given machine, ensure that that
# machine has the code in BinaryBuilder up-to-date.

if [ "$#" -lt 3 ]; then echo Usage: $0 machine buildDir filesList; exit; fi

machine=$1
buildDir=$2
filesList=$3

cd $HOME/$buildDir

if [ ! -f "$filesList" ]; then
    echo Error: Cannot find $filesList
    exit 1
fi

# The list of files to push
files=$(cat $filesList | tr '\n' ' ')

ssh $machine "mkdir -p $buildDir" 2>/dev/null

echo "rsync -avz --delete $files $machine:$buildDir"
rsync -avz --delete $files $machine:$buildDir 2>/dev/null

if [ $? -eq 0 ]; then
    sleep 5 # just in case, to ensure the files finished copying
    exit 0
else
    exit 1
fi
