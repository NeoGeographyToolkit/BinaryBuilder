#!/bin/bash

# Launch a build on the current machine or on one of its virtual submachines

if [ "$#" -lt 3 ]; then echo Usage: $0 machine buildDir statusFile; exit; fi

# Note: buildDir must be relative to $HOME
machine=$1; buildDir=$2; statusFile=$3;
doneFile="buildDone.txt" # Put here the build name when it is done

cd $HOME
if [ ! -d "$buildDir" ]; then echo "Error: Directory: $buildDir does not exist"; exit 1; fi;
cd $buildDir

user=$(whoami)
if [ "$(echo $machine | grep centos)" != "" ]; then
    # The case of virtual machines
    user=build
    # If the machine is not running, start it
    isRunning=$(virsh list --all 2>/dev/null |grep running | grep $machine)
    if [ "$isRunning" == "" ]; then
        virsh start $machine
    fi
    # Wait until the machine is fully running
    while [ 1 ]; do
        ans=$(ssh "$user@$machine" ls $buildDir 2>/dev/null)
        if [ "$ans" != "" ]; then break; fi
        echo $(date) "Sleping while waiting for $machine to start"
        sleep 60
    done
fi

# Make sure all scripts are up-to-date on the target machine
rsync -avz patches *sh *py $user@$machine:$buildDir

# Ensure we first wipe $doneFile, then launch the build
ssh $user@$machine "rm -f $buildDir/$doneFile"
# Bug fix for Mac: It does not ssh to itself or nohup
if [ "$(uname -n)" = "$machine" ]; then
    ./build.sh $buildDir $doneFile > output_build.txt 2>&1&
else
    ssh $user@$machine "nohup nice -19 $buildDir/build.sh $buildDir $doneFile > $buildDir/output_build.txt 2>&1&"
fi

# Wait until the build finished
while [ 1 ]; do
  asp_tarball=$(ssh "$user@$machine" "cat $buildDir/$doneFile 2>/dev/null" 2>/dev/null)
  if [ "$asp_tarball" != "" ]; then break; fi
  echo $(date) "Sleping while waiting for the build on $machine to finish"
  sleep 60
done

# Copy back the obtained tarball and mark it as built
mkdir -p asp_tarballs
echo Copying $user@$machine:$buildDir/$asp_tarball to asp_tarballs
rsync -avz $user@$machine:$buildDir/$asp_tarball asp_tarballs
echo $asp_tarball build_done > $statusFile
