#!/bin/bash

# Build the pdf doc. Note how we use the sphinx package installed
# at $SPHINX_PATH. 

if [ "$#" -lt 1 ]; then
    echo Usage: $0 buildDir
    exit 1
fi
buildDir=$1

SPHINX_PATH=/home/oalexan1/miniconda3/envs/sphinx/bin

# Go to the doc directory
docDir=$HOME/$buildDir/build_asp/build/stereopipeline/stereopipeline-git/docs
if [ ! -d "$docDir" ]; then
    echo Missing doc directory: $docDir
    exit 1
fi
cd $docDir

PATH=$SPHINX_PATH:$PATH make latexpdf

if [ ! -f "_build/latex/asp_book.pdf" ]; then
    echo Failed to produce the pdf document
    exit 1
fi

exit 0
