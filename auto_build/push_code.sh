#!/bin/bash

# Before we launch any job on a given machine, ensure that that
# machine has the code in BinaryBuilder up-to-date.

if [ "$#" -lt 3 ]; then echo Usage: $0 user machine buildDir; exit; fi
user=$1
machine=$2
buildDir=$3

cd $HOME/$buildDir

# The list of files is generated earlier, in start.sh
files=$(cat auto_build/filesToCopy.txt)

echo "rsync -avz $files $user@$machine:$buildDir"
rsync -avz $files $user@$machine:$buildDir 2>/dev/null

sleep 5 # just in case, to ensure the files finished copying
