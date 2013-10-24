#!/bin/bash

# Launch a build on the current machine or on one of its virtual
# submachines.

# This script must not exit without updating the status in $statusFile
# otherwise the caller will wait forever.

if [ "$#" -lt 4 ]; then echo Usage: $0 buildMachine buildDir statusFile statusBuildFile; exit 1; fi

# Note: buildDir must be relative to $HOME
buildMachine=$1; buildDir=$2; statusFile=$3; statusBuildFile=$4

cd $HOME
if [ ! -d "$buildDir" ]; then echo "Error: Directory: $buildDir does not exist"; exit 1; fi;
cd $buildDir

echo "Launching build/test sequence on machine $(uname -n) at $(date)"

. $HOME/$buildDir/auto_build/utils.sh # load utilities

user=$(whoami)
if [ "$(echo $buildMachine | grep centos)" != "" ]; then
    # The case of virtual machines
    user=build
    # If the machine is not running, start it
    isRunning=$(virsh list --all 2>/dev/null | grep running | grep $buildMachine)
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
ssh $user@$buildMachine "echo NoTarballYet now_building > $buildDir/$statusBuildFile" 2>/dev/null
sleep 5 # Give the filesystem enough time to react

# We cannot build on andey, there we will just copy the build from amos
if [ "$buildMachine" = "andey" ]; then
    exit 0
fi

# Start the build
buildOutputFile="$buildDir/output_build_"$buildMachine".txt"
ssh $user@$buildMachine "nohup nice -19 $buildDir/auto_build/build.sh $buildDir $statusBuildFile > $buildOutputFile 2>&1&" 2>/dev/null

# Wait until the build finished
while [ 1 ]; do
    statusLine=$(ssh $user@$buildMachine \
        "cat $buildDir/$statusBuildFile 2>/dev/null" 2>/dev/null)
    asp_tarball=$( echo $statusLine | awk '{print $1}' )
    state=$( echo $statusLine | awk '{print $2}' )

    if [ "$asp_tarball" = "Fail" ] || [ "$state" != "now_building" ]; then
        break
    fi
    echo $(date) "Sleping while waiting for the build on $buildMachine to finish"
    sleep 60
done

# Copy back the obtained tarball
if [ "$asp_tarball" != "Fail" ]; then
    mkdir -p asp_tarballs
    echo Copying $user@$buildMachine:$buildDir/$asp_tarball to asp_tarballs
    rsync -avz $user@$buildMachine:$buildDir/$asp_tarball asp_tarballs 2>/dev/null
fi

# Append the build log file to current logfile.
# Wipe weird characters which can create funny artifacts in the log file.
echo Will append $buildOutputFile
echo ssh $user@$buildMachine "cat $buildOutputFile" 2>/dev/null
#ssh $user@$buildMachine "cat $buildOutputFile" | perl -pi -e "s/[^\s[:print:]]//g" 2>/dev/null 
echo Done appending $buildOutputFile

# Copy the build from amos to andey
echo Machine is "'$buildMachine'"
if [ "$buildMachine" = "amos" ]; then 

    if [ "$asp_tarball" != "Fail" ] && [ -f "$asp_tarball" ]; then
        res=""
        while [ "$res" = "" ]; do
            echo Will attempt to copy to andey: 
            ssh $user@andey "mkdir -p $buildDir/asp_tarballs" 2>/dev/null
            rsync -avz $asp_tarball $user@andey:$buildDir/asp_tarballs 2>/dev/null
            res=$(ssh $user@andey "ls $buildDir/$asp_tarball" 2>/dev/null)
            echo Result is $res
            sleep 10
        done
    fi

    statusFile2=$(status_file andey)
    echo "$asp_tarball build_done" > $statusFile2
    echo "File contents is"
    cat $statusFile2
    rsync -avz $statusFile2 $user@andey:$buildDir 2>/dev/null

fi

# Mark the build as done. This must happen at the very end,
# as otherwise the parent script will spring into action
# before this child script exits.
echo "$asp_tarball build_done" > $statusFile

