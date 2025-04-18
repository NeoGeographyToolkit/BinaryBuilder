#!/bin/bash

# Build ASP. On any failure, ensure the "Fail" flag is set in
# $statusFile on the calling machine, otherwise the caller will wait
# forever.

# On success, copy back to the master machine the built tarball and
# set the status.

if [ "$#" -lt 4 ]; then
    echo Usage: $0 buildDir statusFile buildPlatform masterMachine
    exit 1
fi

buildDir=$1
statusFile=$2
buildPlatform=$3
masterMachine=$4

echo Running $(pwd)/build.sh

# Set path and load utilities
source $HOME/$buildDir/auto_build/utils.sh

# Current machine (must source auto_build/utils.sh first)
buildMachine=$(machine_name)

echo buildDir=$buildDir
echo statusFile=$statusFile
echo buildPlatform=$buildPlatform
echo buildMachine=$buildMachine
echo masterMachine=$masterMachine

cd $HOME
if [ ! -d "$buildDir" ]; then
    echo "Error: Directory: $buildDir does not exist"
    echo "Fail build_failed" > $buildDir/$statusFile
    exit 1
fi
cd $buildDir

# These are needed primarily for pfe
ulimit -s unlimited 2>/dev/null
ulimit -f unlimited 2>/dev/null
ulimit -v unlimited 2>/dev/null
ulimit -u unlimited 2>/dev/null

# rm -fv ./BaseSystem*bz2
# rm -fv ./StereoPipeline*bz2

# Set the ISIS env, needed for 'make check' in ASP. Do this only
# on the Mac, as on other platforms we lack
# all the needed ISIS data.
isMac=$(uname -s | grep Darwin)
if [ "$isMac" != "" ]; then
    isis=$(isis_file)
    if [ -f "$isis" ]; then
        . "$isis"
    else
        echo "Warning: Could not set up the ISIS environment."
    fi
fi

# Dump the environmental variables
env

# Init the status file
echo "NoTarballYet now_building" > $HOME/$buildDir/$statusFile

# The process is very different for cloudMacOS
# May need to move it to its own file
if [ "$buildPlatform" = "cloudMacOS" ]; then
  
    # The path to the gh tool
    gh=/home/oalexan1/miniconda3/envs/gh/bin/gh
    # check if $gh exists and is executable
    if [ ! -x "$gh" ]; then
        echo "Error: Cannot find the gh tool at $gh"
        exit 1
    fi

    repo=git@github.com:NeoGeographyToolkit/StereoPipeline.git
    
    # Start a new run
    echo "Starting a new run in the cloud"
    echo $gh workflow run build_test -R $repo
    $gh workflow run build_test -R $repo
    
    # Wait for 6 hours, by iterating 720 times with a pause of 30 seconds
    success=""
    for i in {0..720}; do
        echo "Will sleep for 30 seconds"
        sleep 30
     
        # For now just fetch the latest. Must launch and wait till it is done
        ans=$($gh run list -R $repo --workflow=build_test.yml | grep -v STATUS | head -n 1)
        echo Status of latest cloud build is $ans
        # Extract second value from ans with awk
        completed=$(echo $ans | awk '{print $1}')
        success=$(echo $ans | awk '{print $2}')
        id=$(echo $ans | awk '{print $7}')
        echo Completed is $completed
        echo Success is $success
        echo Id is $id
        
        if [ "$completed" != "completed" ]; then
            # It can be queued, in_progress, or completed
            echo Not completed, will loop and wait. Iteration: $i
        else
            echo Completed, will break the loop
            break
        fi
    done
    
    # The cloud directory where the build is stored. Wipe any prior local
    # version, or else the fetching can fail.
    cloudBuildDir=StereoPipeline-macOS
    /bin/rm -rf $cloudBuildDir

    # Fetch the build from the cloud. If it failed,
    # we will at least have the logs.
    echo Fetching the build with id $id from the cloud 
    echo $gh run download -R $repo $id
    $gh run download -R $repo $id
    
    if [ "$success" != "success" ]; then
        echo Cloud build failed with status $success
        echo "Fail build_failed" > $HOME/$buildDir/$statusFile
        exit 1
    else
        echo Cloud build succeeded
    fi

    asp_tarball=$(ls $cloudBuildDir/StereoPipeline-*.tar.bz2 | head -n 1)
    echo List the downloaded build directory
    ls -ld $cloudBuildDir/*
    # Check if empty, that means it failed
    if [ "$asp_tarball" = "" ]; then
        echo "Fail build_failed" > $HOME/$buildDir/$statusFile
        exit 1
    fi
    
    # Check the test status. This file is created by the cloud build.
    reportFile=$cloudBuildDir/output_test.txt
    test_ans=$(grep "test_status 0" $reportFile)
    
    # Move the build to where it is expected, then record the build name
    mkdir -p asp_tarballs
    mv $asp_tarball asp_tarballs
    asp_tarball=asp_tarballs/$(basename $asp_tarball)
    
    # Record build status. This must happen at the very end, otherwise the
    # parent script will take over before this script finished.
    if [ "$test_ans" != "" ]; then
        echo "$asp_tarball test_done Success" > $HOME/$buildDir/$statusFile
        # Wipe the fetched directory only on success, otherwise need to inspect it
        /bin/rm -rf $cloudBuildDir
        exit 0
    else
        echo "$asp_tarball test_done Fail" > $HOME/$buildDir/$statusFile
        exit 1
    fi
fi

# For the Mac build the script exits by now, so this is only for Linux.

# Build everything, including VW and ASP. Only the packages
# whose checksum changed will get built.
echo "Building changed packages"
opt=""
if [ "$isMac" != "" ]; then
    opt="--cc=$isisEnv/bin/clang --cxx=$isisEnv/bin/clang++ --gfortran=$isisEnv/bin/gfortran"
else
    opt="--cc=$isisEnv/bin/x86_64-conda_cos6-linux-gnu-gcc --cxx=$isisEnv/bin/x86_64-conda_cos6-linux-gnu-g++ --gfortran=$isisEnv/bin/x86_64-conda_cos6-linux-gnu-gfortran"
fi

# The path to the ASP dependencies 
opt="$opt --asp-deps-dir $isisEnv"

cmd="./build.py $opt --skip-tests"
echo $cmd
eval $cmd
exitStatus=$?

echo "Build status is $exitStatus"
if [ "$exitStatus" -ne 0 ]; then
    echo "Fail build_failed" > $HOME/$buildDir/$statusFile
    exit 1
fi

# Dump the ASP version. Will be used later.
versionFile=$(version_file $buildPlatform)
find_version $versionFile
echo "Saving the ASP version ($(cat $versionFile)) to file: $versionFile"

# Make sure all maintainers can access the files.
# Turn this off as there is only one maintainer,
# and they fail on some machines
#chown -R  :ar-gg-ti-asp-maintain $HOME/$buildDir
#chmod -R g+rw $HOME/$buildDir

echo "Packaging ASP."
./make-dist.py last-completed-run/install --asp-deps-dir $isisEnv --python-env $pythonEnv

if [ "$?" -ne 0 ]; then
    echo "Fail build_failed" > $HOME/$buildDir/$statusFile
    exit 1
fi

# Copy the build to asp_tarballs
echo "Moving packaged ASP to directory asp_tarballs"
asp_tarball=$(ls -trd StereoPipeline*bz2 | grep -i -v debug | tail -n 1)
if [ "$asp_tarball" = "" ]; then
    echo "Fail build_failed" > $HOME/$buildDir/$statusFile
    exit 1
fi
mkdir -p asp_tarballs
mv $asp_tarball asp_tarballs
asp_tarball=asp_tarballs/$asp_tarball

# Wipe old builds on the build machine
echo "Cleaning old builds..."
numKeep=8
if [ "$(echo $buildMachine | grep $masterMachine)" != "" ]; then
    numKeep=24 # keep more builds on master machine
fi
$HOME/$buildDir/auto_build/rm_old.sh $HOME/$buildDir/asp_tarballs $numKeep

# rm -f StereoPipeline*debug.tar.bz2

# Mark the build as finished. This must happen at the very end,
# otherwise the parent script will take over before this script finished.
echo "$asp_tarball build_done Success" > $HOME/$buildDir/$statusFile

# Last time make sure the permissions are right
# Turn this off as these fail on some machines
#chown -R  :ar-gg-ti-asp-maintain $HOME/$buildDir
#chmod -R g+rw $HOME/$buildDir

echo "Finished running build.sh locally!"

exit 0
