#!/bin/bash

# Build the pdf doc


if [ "$#" -lt 2 ]; then
    echo Usage: $0 buildDir isisEnv
    exit 1
fi
buildDir=$1
isisEnv=$2

# Go to the doc directory
docDir=$HOME/$buildDir/build_asp/build/stereopipeline/stereopipeline-git/docs
if [ ! -d "$docDir" ]; then
    echo Missing doc directory: $docDir
    exit 1
fi
cd $docDir

condaFile=$HOME/miniconda3/etc/profile.d/conda.sh

if [ ! -f "$condaFile" ]; then
    echo Cannot find $condaFile
    exit 1
fi

# Activate conda to get the dependencies
# TODO(oalexan1): Move them to our own namespace.
source $condaFile
conda activate $(basename $isisEnv)

make latexpdf

if [ ! -f "_build/latex/asp_book.pdf" ]; then
    echo Failed to produce the pdf document
    exit 1
fi

exit 0
