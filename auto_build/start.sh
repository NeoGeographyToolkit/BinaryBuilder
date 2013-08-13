#!/bin/bash

# Initiate the build/test/release famework. See README.txt for more details.

# IMPORTANT: The first thing this script does is update itself (and
# other codes) from github. Updating a script while it is running does
# not always work nicely. The user must ensure that each time this
# script is modified, it is first called interactively with the option
# "no_self_update", be satisfied that everything works properly, then
# check in all desired changes.

# This procedure must be followed only when this script is modified.
# It can handle safely the process of updating other modified code.

# IMPORTANT: The list in auto_build/filesToCopy.txt must be modified
# each time a new file/directory is added to the top level of
# BinaryBuilder. This list is auto-generated below, but based on the
# list of files already on github, so it won't reflect local changes.

no_self_update=$1

buildDir=projects/BinaryBuilder # must be relative to home dir
cd $HOME/$buildDir

if [ "$no_self_update" != "no_self_update" ]; then

    # Update from github
    dir="BinaryBuilder_newest"
    rm -rf $dir
    git clone https://github.com/NeoGeographyToolkit/BinaryBuilder.git $dir
    cd $dir
    files=$(\ls -ad *)
    cp -rf $files ..
    cd ..
    rm -rf $dir

    # Need the list of files so that we can copy those later to the slave machines
    echo $files > auto_build/filesToCopy.txt

fi

./auto_build/launch_master.sh $buildDir
