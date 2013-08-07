#!/bin/bash

# Launch a build on the current machine or on one of its virtual submachines

if [ "$#" -lt 3 ]; then echo Usage: $0 machine buildDir statusFile; exit; fi

# Note: buildDir must be relative to $HOME
machine=$1; buildDir=$2; statusFile=$3;
doneFile="done.txt" # Put here the build name when it is done

cd $HOME
if [ ! -d "$buildDir" ]; then echo "Directory: $buildDir does not exist"; exit 1; fi;
cd $buildDir

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
        sleep 60
    done
else
    user=$(whoami)
fi

# Make sure all scripts are up-to-date on the target machine
rsync -avz *sh $user@$machine:$buildDir

# Ensure we first wipe $doneFile, then launch the build
ssh $user@$machine "rm -f $buildDir/$doneFile"
ssh $user@$machine "$buildDir/build.sh $buildDir $doneFile > $buildDir/output.txt 2>&1&"

# Wait until the build finished
while [ 1 ]; do
  asp_tarball=$(ssh "$user@$machine" "cat $buildDir/$doneFile 2>/dev/null" 2>/dev/null)
  if [ "$asp_tarball" != "" ]; then break; fi
  echo "Sleping while waiting for the build on $machine to finish"
  sleep 60
done

# Copy back the obtained tarball and mark it as built
mkdir -p asp_tarballs
rsync -avz $user@$machine:$buildDir/$asp_tarball asp_tarballs
echo $buildDir/asp_tarballs/$asp_tarball build_done > $statusFile
