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

function start_vrts {

    host=$1
    vrt1=$2
    vrt2=$3

    # Connect to $host and start virtual machines $vrt1 and $vrt2
    ssh $host virsh start $vrt1 2>/dev/null
    ssh $host virsh start $vrt2 2>/dev/null

    while [ 1 ]; do
        ans1=$(ssh $vrt1 "ls /" 2>/dev/null)
        ans2=$(ssh $vrt2 "ls /" 2>/dev/null)
        if [ "$ans1" != "" ] && [ "$ans2" != "" ]; then break; fi
        echo $(date) "Sleping while waiting for virtual machines" \
            "$vrt1 $vrt2 to start"
        sleep 60
    done
        
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


