#!/bin/bash

# Must ensure reasonable versions of gcc, g++, gfortran, python, and
# git are somewhere in the paths below. Note: we put /usr/bin below
# to access the correct libtool on the Mac.
# - To clarify, this line contains the correct values for each different 
#   build machine all jammed together in one big line.  Same for LD_LIBRARY_PATH below.
# - Don't forget to include the paths for building the PDF with Latex

function prepend_to_path () {
    # Prepend to PATH unless alrady first in the path
    if ! echo "$PATH" | grep -Eq "(^)$1($|:)" ; then
        export PATH="$1:$PATH"
    fi
}

# Ensure this is changed when the environment changes.
# See docs/building_asp.rst for more details.
# Below is a a temporary fix for the latest experimental ISIS 
# being installed in a different environment.
if [ "$(uname -s)" = "Linux" ]; then
    isisEnv=$HOME/miniconda3/envs/isis_dev
    pythonEnv=$HOME/miniconda3/envs/python_isis_dev
else
    export isisEnv=$HOME/miniconda3/envs/asp_deps
    export pythonEnv=$HOME/miniconda3/envs/python_isis8 
fi

prepend_to_path $isisEnv/bin

# Get the machine name. Strip any domain name.
function machine_name() {
    machine=$(uname -n | perl -p -e "s#\..*?\$##g")
    echo $machine
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

function find_version () {
    versionFile=$1
    build_asp/install/bin/stereo -v 2>/dev/null | grep "NASA Ames Stereo Pipeline" | awk '{print $5}' >  $versionFile

}

function release_conf_file (){
    echo "release_"$1".conf"
}

function isis_file (){
    echo "auto_build/isis.sh"
}

function ncpus(){
    ncpu=$(cat /proc/cpuinfo 2>/dev/null |grep processor |wc | awk '{print $1}')
    if [ "$ncpu" = "0" ]; then ncpu=2; fi # For OSX
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
        else # All Linux machines
            # Start the process on the remote machine
            cmd="nohup nice -19 $prog $opts > $outfile 2>&1&"
            echo ssh $machine \"$cmd\"
            ssh $machine "$cmd" 2>/dev/null &
        fi

        # Wait a while and then look for the process name
        # This is very bad logic. Need to find a way to see if that
        # process is still running or exited. In the latter case
        # need to check for the exit code.
        sleep 5
        out=$(ssh $machine "ps ux | grep $name | grep -v grep" \
            2>/dev/null)
        if [ "$out" != "" ]; then
            echo "Success starting on $machine: $out";
            return 0
        fi
        echo "Trying to start $name at $(date) on $machine in attempt $count"
    done
    
    # Failed after many attempts
    return 1
}

# The Linux build is run on the master machine. The macOS build is run in the
# cloud, but monitored on the master machine. So the run machine is the master
# machine in both cases.
function get_build_machine {

    buildPlatform=$1
    masterMachine=$2
   
    if [ "$buildPlatform" == "localLinux" ]; then
        buildMachine=$masterMachine
    else
        buildMachine=$masterMachine
    fi

    # If this assumption ever changes, need to ensure the various machines
    # have the code and data in sync.    
    if [ "$buildMachine" != "$masterMachine" ]; then
        echo "Error: Expecting build machine to be $masterMachine"
        exit 1
    fi
    
    # Echo the result so it is captured by the caller
    echo $buildMachine
}

# The master machine is used for building and testing on Linux. On macOS, the
# build and test is in the cloud. Once that is done, we will copy the files
# locally, so in that case use the master machine as well.
function get_test_machine {

    buildPlatform=$1
    masterMachine=$2
   
    if [ "$buildPlatform" == "localLinux" ]; then
        testMachine=$masterMachine
    else
        testMachine=$masterMachine
    fi
    
    # If this assumption ever changes, need to ensure the various machines
    # have the code and data in sync.    
    if [ "$testMachine" != "$masterMachine" ]; then
        echo "Error: Expecting test machine to be $masterMachine"
        exit 1
    fi
    
    # Echo the result so it is captured by the caller
    echo $testMachine
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

# Wipe a given release from GitHub. This function must be invoked from
# a StereoPipeline directory where authentification with GitHub was
# done beforehand.
function wipe_release {
    gh=$1
    repo=$2
    release=$3
    
    # Wipe the old release
    echo $gh release -R $repo delete $release
    $gh release -R $repo delete $release
    
    # Wipe the old tag
    git fetch --all
    git push --delete god $release # delete the tag on the server
    git tag -d $release            # delete the tag locally
}
    
# Upload the builds to github
function upload_to_github {

    binaries=$1
    timestamp=$2

    echo The binaries to upload are $binaries
    echo Timestamp is $timestamp

    # The path to the gh tool
    gh=$HOME/miniconda3/envs/gh/bin/gh
    # check if $gh exists and is executable
    if [ ! -x "$gh" ]; then
        echo "Error: Cannot find the gh tool at $gh"
        exit 1
    fi
    
    repo=git@github.com:NeoGeographyToolkit/StereoPipeline.git
    daily_build="daily-build"

    # See the existing daily builds already published
    releases=$($gh release -R $repo list | awk '{print $1}' | grep $daily_build)
    
    # Today's release
    tag="${timestamp}-${daily_build}"

    # Add today's release, unless this is second time this tool runs today
    # so it is already present.
    exists=$(echo $releases | grep $tag)
    if [ "$exists" = "" ]; then
        releases="$tag $releases"
    fi

    # Have to cd to the local ASP directory, as that's where the GitHub credentials
    # are stored
    currDir=$(pwd)
    cd /home/oalexan1/projects/StereoPipeline
    
    # Note that the first time gh is used it will ask for authorization

    # Make gh not interactive
    $gh config set prompt disabled
   
    # Keep only the last two releases, so delete old ones
    numKeep=2
    count=0
    for release in $releases; do
        ((count = count + 1))
        if [ "$count" -gt "$numKeep" ]; then
            wipe_release $gh $repo "$release"
        fi
    done

    # List the releases
    echo Releases so far
    $gh release -R $repo list

    # If the current release already exists, wipe it
    exists=$($gh release -R $repo list | grep $tag)
    if [ "$exists" != "" ]; then
        echo Also wipe release $tag
        wipe_release $gh $repo $tag
    fi

    notes="Recent additions log: https://stereopipeline.readthedocs.io/en/latest/news.html"
    echo $gh release -R $repo create $tag $binaries --title $tag --notes "$notes"
    $gh release -R $repo create $tag $binaries --title $tag --notes "$notes"

    # Record the status
    status=$?
    echo Status is $status
    
    # Go back to the original directory
    cd $currDir

    return $status
}
