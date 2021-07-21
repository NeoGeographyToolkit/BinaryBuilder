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
        #echo New path $PATH
        #echo Already in the PATH=$PATH
    fi
}

# Ensure this is changed when the environment changes
export isisEnv=$HOME/miniconda3/envs/isis5.0.1

# TODO(oalexan1): Sort this out. 
prepend_to_path $isisEnv/bin:$HOME/../oalexan1/miniconda3/envs/sparse_disp/bin:/home/smcmich1/programs/latexmk/bin:/byss/smcmich1/programs/tkdiff-unix/:/Users/smcmich1/Library/Python/2.7/bin/:/Users/smcmich1/usr/local/bin:/home/oalexan1/.local/bin:/Users/oalexan1/.local/bin:/usr/local/bin:/home/oalexan1/.local/bin/pip

# These are needed for the development build and will
# be set properly for the packaged build.
# TODO(oalexan1): Are these necessary?
export ISISROOT_DEV=$isisEnv
export GDAL_DATA=$isisEnv/share/gdal
export QT_PLUGIN_PATH=$isisEnv/plugins

export PYTHONPATH=$PYTHONPATH:$HOME/.local

function machine_name() {
    machine=$(uname -n | perl -p -e "s#\..*?\$##g")
    echo $machine
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

    # The same machine is used for building and testing. In the future
    # that may change.

    buildMachine=$1
    masterMachine=$2

    testMachines=$buildMachine

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
    gh=/home/oalexan1/projects/packages/gh_1.11.0_linux_amd64/bin/gh
    repo=git@github.com:NeoGeographyToolkit/StereoPipeline.git
    
    # First record all the releases we already did
    releaseFile="GitHubReleases.txt"

    count=0
    declare -a releases=() # make an empty initial array
    for f in $(cat $releaseFile); do
        if [ "$f" = "" ]; then
            continue;
        fi
        releases[$count]=$f
        ((count++))
    done

    # Add today's release. If this is second time this tool runs today,
    # ensure we don't add this timestamp twice
    tag=$timestamp"-daily-build"
    exists=$(cat $releaseFile |grep $tag)
    if [ "$exists" = "" ]; then
        releases[$count]=$tag
    fi
    
    numReleases="${#releases[@]}"
    for ((count = 0; count < numReleases; count++)); do
      echo "Release timestamp: ${releases[$count]}"
    done

    # Have to cd to the local ASP directory, as that's where the GitHub credentials
    # are stored
    currDir=$(pwd)
    cd /home/oalexan1/projects/StereoPipeline
    
    # Make gh not interactive
    $gh config set prompt disabled

    # Keep only the last two releases, so delete old ones
    numKeep=2
    for ((count = 0; count < numReleases - numKeep; count++)); do
        wipe_release $gh $repo "${releases[$count]}"
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

    echo $gh release -R $repo create $tag $binaries --title $tag --notes "$tag"
    $gh release -R $repo create $tag $binaries --title $tag --notes "$tag"

    # Record the status
    status=$?
    echo Status is $status
    
    # Go back to the original directory
    cd $currDir

    # Record the releases that are kept. Keep only the last two
    # releases, so delete old ones.
    /bin/rm -f $releaseFile
    for ((count = numReleases - numKeep; count < numReleases; count++)); do
        if [ "$count" -lt 0 ]; then continue; fi
        echo "${releases[$count]}" >> $releaseFile
    done

    return $status
}
