#!/bin/bash

# Must ensure reasonable versions of gcc, g++, gfortran, python, and
# git are somewhere in the paths below. Note: we put /usr/bin below
# to access the correct libtool on the Mac.
# - To clarify, this line contains the correct values for each different 
#   build machine all jammed together in one big line.  Same for LD_LIBRARY_PATH below.
# - Don't forget to include the paths for building the PDF with Latex

function prepend_to_path () {
    # Prepend to PATH unless alrady first in the path
    if ! echo "$PATH" | /bin/grep -Eq "(^)$1($|:)" ; then
        export PATH="$1:$PATH"
        #echo New path $PATH
        #echo Already in the PATH=$PATH
    fi
}

export HOMEBREW_PREFIX=/Users/oalexan1/usr/local
prepend_to_path $HOME/../oalexan1/miniconda3/envs/isis/bin:$HOME/miniconda3/envs/isis/bin:/opt/rh/devtoolset-6/root/usr/bin:$HOMEBREW_PREFIX/bin:/home6/oalexan1/projects/data/gcc5/gcc-5.4.0/install/bin::/home/smcmich1/programs/latexmk/bin:/byss/smcmich1/programs/tkdiff-unix/:/Users/smcmich1/Library/Python/2.7/bin/:/home/pipeline/projects/gcc-4.9.3-install/bin:/home/oalexan1/projects/zack_packages/local/bin/:/home/pipeline/projects/packages/bin/:/Users/smcmich1/usr/local/bin:/home/oalexan1/.local/bin:/Users/oalexan1/.local/bin:/home/smcmich1/anaconda2/bin:/usr/local/bin:/usr/bin:/nasa/python/2.7.3/bin/:/nasa/sles11/git/1.7.7.4/bin/:/nasa/pkgsrc/2014Q3/gcc49/bin/:/nasa/svn/1.6.21/bin:/home/oalexan1/.local/bin/pip

# This is needed for new gcc
export LD_LIBRARY_PATH=/home/pipeline/projects/gcc5/lib:/home/pipeline/projects/gcc5/lib64:/opt/rh/devtoolset-6/root/usr/lib64:/opt/rh/devtoolset-6/root/usr/lib:/home6/oalexan1/projects/data/gcc5/gcc-5.4.0/install/lib:/home/pipeline/projects/gcc-4.9.3-install/lib:/home/pipeline/projects/gcc-4.9.3-install/lib64:/home/oalexan1/projects/zack_packages/local/lib:/home/oalexan1/projects/zack_packages/local/lib64

export DYLD_LIBRARY_PATH=/Users/oalexan1/usr/local/lib/gcc/4.9:$DYLD_LIBRARY_PATH

export PYTHONPATH=$PYTHONPATH:$HOME/.local

function machine_name() {
    machine=$(uname -n | perl -p -e "s#\..*?\$##g")
    echo $machine
}

# For centos7 tweak LD_LIBRARY_PATH
if [ "$(machine_name)" = "centos7" ]; then
    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$HOME/projects/BinaryBuilder/build_asp/install/lib
fi


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

function release_conf_file (){
    echo "release_"$1".conf"
}

function isis_file (){
    echo "auto_build/isis.sh"
}

function ncpus(){
    ncpu=$(cat /proc/cpuinfo 2>/dev/null |grep processor |wc | awk '{print $1}')
    if [ "$ncpu" = "0" ]; then ncpu=2; fi # For OSX # TODO update when we move to decoder!
    echo $ncpu
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

    if [ "$(whoami)" = "oalexan1" ]; then
	echo User oalexan1 cannot start the vrts
	return 0
    fi
    
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

function robust_ssh {

    # Do several attempts to launch a job on a machine.
    # This is primarily needed for OSX, sometimes
    # a nohup job on it fails.

    machine=$1
    prog=$2
    opts=$3
    outfile=$4
    name=$(basename $prog)

    for ((count = 0; count < 50; count++)); do

        if [ "$machine" = "decoder" ]; then
            # nohup does not work on Macs any more
            # Start an ssh process on the local machine in the background
            cmd="$prog $opts > $outfile 2>&1"
            echo ssh $machine \"$cmd\"
            ssh $machine "$cmd" 2>/dev/null &

        else # All linux machines
            # Start the process on the remote machine
            cmd="nohup nice -19 $prog $opts > $outfile 2>&1&"
            echo ssh $machine \"$cmd\"
            ssh $machine "$cmd" 2>/dev/null &
        fi

        # Wait a while and then look for the process name
        sleep 20
        out=$(ssh $machine "ps ux | grep $name | grep -v grep" \
            2>/dev/null)
        if [ "$out" != "" ]; then
            echo "Success starting on $machine: $out";
            return 0
        fi
        echo "Trying to start $name at $(date) on $machine in attempt $count"
    done
    return 1
}

function get_test_machines {

    # Test the centos7 build on $masterMachine.

    buildMachine=$1
    masterMachine=$2

    if [ "$buildMachine" = "centos7" ]; then
        testMachines="$masterMachine"
    elif [ "$buildMachine" = "lunokhod2" ]; then
        testMachines="$masterMachine"
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
