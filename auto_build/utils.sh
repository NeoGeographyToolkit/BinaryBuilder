#!/bin/bash

function set_system_paths () {
    export PATH=/nasa/python/2.7.3/bin/:/nasa/sles11/git/1.7.7.4/bin/:~zmoratto/macports/bin:$HOME/projects/packages/bin/:$HOME/packages/local/bin/:$PATH

}

function status_file () {
    echo "status_"$1".txt"
}

function status_build_file () {
    echo "status_build_"$1".txt"
}

# To do: Make this consistent with the above, so
# remove the buildDir from here
function output_file () {
    buildDir=$1
    machine=$2
    echo "$buildDir/output_"$machine".txt"
}
