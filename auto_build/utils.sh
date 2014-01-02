#!/bin/bash

function set_system_paths () {
    export PATH=/nasa/python/2.7.3/bin/:/nasa/sles11/git/1.7.7.4/bin/:~zmoratto/macports/bin:$HOME/projects/packages/bin/:$HOME/packages/local/bin/:$PATH

}

function status_file () {
    echo "status_"$1".txt"
}

function status_test_file () {
    echo "status_test_"$1".txt"
}

function status_build_file () {
    echo "status_build_"$1".txt"
}

function version_file (){
    echo "version_"$1".txt"
}

# To do: Make this consistent with the above, so
# remove the buildDir from here
function output_file () {
    buildDir=$1
    machine=$2
    echo "$buildDir/output_"$machine".txt"
}
function output_test_file () {
    buildDir=$1
    machine=$2
    echo "$buildDir/output_test_"$machine".txt"
}

function start_vrts {

    virtualMachines=$*

    for vrt in $virtualMachines; do 
        virsh start $vrt 2>/dev/null
    done

    while [ 1 ]; do
        allStarted=1
        for vrt in $virtualMachines; do
            ans=$(ssh $vrt "ls /" 2>/dev/null)
            if [ "$ans" = "" ]; then
                echo "Machine $vrt is not up yet"
                allStarted=0
            else
                echo "Machine $vrt is up"
            fi
        done
        if [ "$allStarted" -eq 1 ]; then
            break
        fi
        sec=30
        echo Sleeping for $sec seconds
        sleep $sec
    done
        
}

function get_test_machines {

    # Test the amos build on itself and andey.
    # Test the centos-64-5 build on itself and $masterMachine.
        
    buildMachine=$1
    masterMachine=$2

    if [ "$buildMachine" = "amos" ]; then
        testMachines="$buildMachine andey"
    elif [ "$buildMachine" = "centos-64-5" ]; then
        testMachines="$buildMachine $masterMachine"
    else
        testMachines=$buildMachine
    fi
    echo $testMachines
}

# Infrastructure needed for checking if any remote repositories changed.
# If nothing changed, there's no need to build/test.

# Global variables
done_hash_file="auto_build/done_hashes.txt"
curr_hash_file="auto_build/curr_hashes.txt"
remotes_changed=0

function check_if_remotes_changed() {

    remotes=('git@github.com:visionworkbench/visionworkbench.git' 'git@github.com:NeoGeographyToolkit/StereoPipeline.git' 'git@github.com:NeoGeographyToolkit/BinaryBuilder.git' 'git@github.com:NeoGeographyToolkit/StereoPipelineTest.git')
    
    mkdir -p auto_build
    rm -f $curr_hash_file
    for repo in "${remotes[@]}"; do
        remote_hash=$(git ls-remote $repo |grep HEAD | awk '{print $1}')
        local_hash=$(grep $repo $done_hash_file | awk '{print $1}')
        echo "Repository: $repo, remote hash: $remote_hash, local_hash: $local_hash"
        if [ "$local_hash" != "$remote_hash" ]; then
            echo Hashes differ
            remotes_changed=1
        else
            echo Hashes do not differ
        fi
        echo "$remote_hash $repo" >> $curr_hash_file
    done
    
}


