#!/bin/bash

# Launch a build on the current machine or on one of its virtual
# submachines.

# This script must not exit without updating the status in $statusFile
# otherwise the caller will wait forever.

if [ "$#" -lt 3 ]; then echo Usage: $0 buildMachine buildDir statusFile; exit; fi

# Note: buildDir must be relative to $HOME
buildMachine=$1; buildDir=$2; statusFile=$3;

cd $HOME
if [ ! -d "$buildDir" ]; then echo "Error: Directory: $buildDir does not exist"; exit 1; fi;
cd $buildDir

echo "Launching build/test sequence on machine $(uname -n) at $(date)"

user=$(whoami)
if [ "$(echo $buildMachine | grep centos)" != "" ]; then
    # The case of virtual machines
    user=build
    # If the machine is not running, start it
    isRunning=$(virsh list --all 2>/dev/null |grep running | grep $buildMachine)
    if [ "$isRunning" == "" ]; then
        virsh start $buildMachine
    fi
    # Wait until the machine is fully running
    while [ 1 ]; do
        ans=$(ssh $user@$buildMachine "ls /" 2>/dev/null)
        if [ "$ans" != "" ]; then break; fi
        echo $(date) "Sleping while waiting for $buildMachine to start"
        sleep 60
    done
fi

# Make sure all scripts are up-to-date on the build machine
./auto_build/push_code.sh $user $buildMachine $buildDir 2>/dev/null

# Initiate the status file on the build machine (which may not be this machine)
outputBuildFile="$buildDir/output_build_"$buildMachine".txt"
ssh $user@$buildMachine "echo NoTarballYet now_building > $buildDir/$statusFile" 2>/dev/null
sleep 5; # Give the filesystem enugh time to react
ssh $user@$buildMachine "nohup nice -19 $buildDir/auto_build/build.sh $buildDir $statusFile > $outputBuildFile 2>&1&"

# Wait until the build finished
while [ 1 ]; do
    statusLine=$(ssh $user@$buildMachine \
        "cat $buildDir/$statusFile 2>/dev/null" 2>/dev/null)
    asp_tarball=$( echo $statusLine | awk '{print $1}' )
    state=$( echo $statusLine | awk '{print $2}' )

    if [ "$asp_tarball" = "Fail" ] || [ "$state" = "build_done" ]; then
        break
    fi
    echo $(date) "Sleping while waiting for the build on $buildMachine to finish"
    sleep 60
done

# Copy back the obtained tarball and mark it as built
if [ "$asp_tarball" != "Fail" ]; then
    mkdir -p asp_tarballs
    echo Copying $user@$buildMachine:$buildDir/$asp_tarball to asp_tarballs
    rsync -avz $user@$buildMachine:$buildDir/$asp_tarball asp_tarballs
fi
echo "$asp_tarball build_done" > $statusFile

echo ssh $user@$buildMachine "cat $outputBuildFile" 2>/dev/null

ssh $user@$buildMachine "cat $outputBuildFile" 2>/dev/null # append to curr logfile
