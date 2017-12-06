#!/bin/bash

# Launch and test all builds on all machines and notify the user of
# the status. In case of success, copy the resulting builds to byss
# and update the public link.

# IMPORTANT NOTE: This script assumes that that all VW, ASP,
# StereoPipelineTest, and BinaryBuilder code is up-to-date in github.

# If you have local modifications in the BinaryBuilder directory,
# update the list at auto_build/filesToCopy.txt (that list has all
# top-level files and directories in BinaryBuilder), and run this
# script as

# ./auto_build/launch_master.sh local_mode

# Once you are satisfied that everything works, check in your changes.
# Then run this script without any options. See auto_build/README.txt
# for more details.

buildDir=projects/BinaryBuilder     # must be relative to home dir
testDir=projects/StereoPipelineTest # must be relative to home dir

# Machines and paths
releaseMachine="byss"
releaseDir="/byss/docroot/stereopipeline/daily_build"
link="http://byss.arc.nasa.gov/stereopipeline/daily_build"
masterMachine="lunokhod1"
virtualMachines="centos-6"
buildMachines="$virtualMachines" # andey is out for an upgrade or forver
#buildMachines="andey $virtualMachines"

resumeRun=0 # Must be set to 0 in production. 1=Resume where it left off.
if [ "$(echo $* | grep resume)" != "" ]; then resumeRun=1; fi
sleepTime=30
localMode=0 # Run local copy of the code. Must not happen in production.
if [ "$(echo $* | grep local_mode)" != "" ]; then localMode=1; fi

# If to skip tests. Must be set to 0 in production.
skipTests=0
if [ "$(echo $* | grep skip_tests)" != "" ]; then skipTests=1; echo "Will skip tests."; fi

if [ "$USER" == "smcmich1" ]; then
    mailto="scott.t.mcmichael@nasa.gov"
    if [ "$localMode" -eq 0 ]; then
        mailto="$mailto oleg.alexandrov@nasa.gov"
    fi
else
    mailto="oleg.alexandrov@nasa.gov"
    if [ "$localMode" -eq 0 ]; then
        mailto="$mailto scott.t.mcmichael@nasa.gov"
    fi
fi

cd $HOME
mkdir -p $buildDir
cd $buildDir
echo "Work directory: $(pwd)"

# Set system paths and load utilities
source $HOME/$buildDir/auto_build/utils.sh

# Unless running in local mode for test purposes, fetch from github
# the latest version of BinaryBuilder, including this very script.
filesList=auto_build/filesToCopy.txt
if [ "$localMode" -eq 0 ]; then
    echo "Updating from github..."
    # Update itself from github
    failure=1
    for ((i = 0; i < 600; i++)); do
        # Bugfix: Sometimes the github server is down, so do multiple attempts.
        echo "Cloning BinaryBuilder in attempt $i"

        ./build.py binarybuilder
        failure="$?"
        if [ "$failure" -eq 0 ]; then break; fi
        sleep 60
    done
    currDir=$(pwd)
    cd build_asp/build/binarybuilder/binarybuilder-git
    files=$(ls -ad *)
    rsync -avz $files $currDir
    cd $currDir

    # Need the list of files so that we can mirror those later to the
    # build machines
    echo $files > $filesList
fi

currMachine=$(machine_name)
if [ "$currMachine" != "$masterMachine" ]; then
    echo Error: Expecting the jobs to be launched from $masterMachine
    exit 1
fi

echo "Making sure virtual machines are running..."
start_vrts $virtualMachines
mkdir -p asp_tarballs

# Wipe the doc before regenerating it
echo "Wiping the doc..."
if [ "$resumeRun" -eq 0 ]; then
    rm -fv dist-add/asp_book.pdf
fi

# Wipe the logs and status files of previous tests. We do it before the builds start,
# as we won't get to the tests if the builds fail.
if [ "$resumeRun" -eq 0 ]; then
    for buildMachine in $buildMachines; do
        testMachines=$(get_test_machines $buildMachine $masterMachine)
        for testMachine in $testMachines; do

            outputTestFile=$(output_test_file $buildDir $testMachine)
            echo "" > $HOME/$outputTestFile
            scp $HOME/$outputTestFile $testMachine:$outputTestFile  2> /dev/null

            statusTestFile=$(status_test_file $testMachine)
            rm -fv $statusTestFile
            
        done
    done
fi

# Start the builds. The build script will copy back the built tarballs
# and status files.
# The reason we build on $masterMachine here is to make the docs,
# which fails on other machines. When it comes to testing though,
# we'll test on $masterMachine the build from centos-6.
echo "Starting up the builds..."
for buildMachine in $buildMachines $masterMachine; do

    echo "Setting up and launching: $buildMachine"

    statusFile=$(status_file $buildMachine)
    outputFile=$(output_file $buildDir $buildMachine)

    # Set the ISIS env, needed for 'make check' in ASP.
    # We will push this to the build machine.
    configFile=$(release_conf_file $buildMachine)
    isis=$(isis_file)
    if [ ! -f "$HOME/$testDir/$configFile" ]; then
        echo Missing $HOME/$testDir/$configFile; exit 1;
    fi
    grep -i isis $HOME/$testDir/$configFile | grep export > $(isis_file)

    # Make sure all scripts are up-to-date on $buildMachine
    echo "Pushing code to: $buildMachine"
    ./auto_build/push_code.sh $buildMachine $buildDir $filesList
    if [ "$?" -ne 0 ]; then exit 1; fi

    if [ "$resumeRun" -ne 0 ]; then
        statusLine=$(cat $statusFile 2>/dev/null)
        tarBall=$(  echo $statusLine | awk '{print $1}' )
        progress=$( echo $statusLine | awk '{print $2}' )
        status=$(   echo $statusLine | awk '{print $3}' )
        # If we resume, rebuild only if the previous build failed
        # or previous testing failed.
        if [ "$progress" != "build_failed" ] && [ "$progress" != "" ] && \
            [ "$status" != "Fail" ]; then
            continue
        fi
    fi
    
    # Launch the build
    echo "NoTarballYet now_building" > $statusFile
    robust_ssh $buildMachine $buildDir/auto_build/build.sh \
        "$buildDir $statusFile $masterMachine" $outputFile
done

# Whenever a build is done, launch tests for it. For some
# builds, tests are launched on more than one machine.
while [ 1 ]; do

    allTestsAreDone=1

    for buildMachine in $buildMachines; do

        # Parse the current status for this build machine
        statusFile=$(status_file $buildMachine)
        statusLine=$(cat $statusFile)
        progress=$(echo $statusLine | awk '{print $2}')

        if [ "$progress" = "now_building" ]; then
            # Update status from the build machine to see if build finished
            # - It is important that we don't update this after the build is finished 
            #   because we modify this file locally and if overwrite it we won't
            #   make it to the correct if statement below!
            echo "Reading status from $statusFile"
            scp $buildMachine:$buildDir/$statusFile . &> /dev/null
        fi

        # Parse the file
        statusLine=$(cat $statusFile)
        tarBall=$(echo $statusLine | awk '{print $1}')
        progress=$(echo $statusLine | awk '{print $2}')
        testMachines=$(get_test_machines $buildMachine $masterMachine)

        if [ "$progress" = "now_building" ]; then
            # Keep waiting
            echo "Status for $buildMachine is $statusLine"
            allTestsAreDone=0
        elif [ "$progress" = "build_failed" ]; then
            # Nothing can be done for this machine
            echo "Status for $buildMachine is $statusLine"
        elif [ "$progress" = "build_done" ]; then

            echo "Fetching the completed build"
            # Grab the build file from the build machine
            echo "rsync -avz  $buildMachine:$buildDir/$tarBall $buildDir/asp_tarballs/"
            rsync -avz  $buildMachine:$buildDir/$tarBall \
                        $HOME/$buildDir/asp_tarballs/    2>/dev/null

            # Build for current machine is done, need to test it
            allTestsAreDone=0
            echo "$tarBall now_testing" > $statusFile
            for testMachine in $testMachines; do

                outputTestFile=$(output_test_file $buildDir $testMachine)

                echo "Will launch tests on $testMachine"
                statusTestFile=$(status_test_file $testMachine)
                echo "$tarBall now_testing" > $statusTestFile

                # Make sure all scripts are up-to-date on $testMachine
                ./auto_build/push_code.sh $testMachine $buildDir $filesList
                if [ "$?" -ne 0 ]; then exit 1; fi

                # Copy the tarball to the test machine
                ssh $testMachine "mkdir -p $buildDir/asp_tarballs" 2>/dev/null
                rsync -avz $tarBall $testMachine:$buildDir/asp_tarballs \
                    2>/dev/null

                sleep 5; # Give the filesystem enough time to react
                if [ "$skipTests" -eq 0 ]; then
                    # Start the tests
                    robust_ssh $testMachine $buildDir/auto_build/run_tests.sh        \
                        "$buildDir $tarBall $testDir $statusTestFile $masterMachine" \
                        $outputTestFile
                else
                    # Fake it, so that we skip the testing
                    echo "$tarBall test_done Success" > $statusFile
                fi
                    
            done

        elif [ "$progress" = "now_testing" ]; then

            # See if we finished testing the current build on all machines
            allDoneForCurrMachine=1
            statusForCurrMachine="Success"
            for testMachine in $testMachines; do

                # Grab the test status file for this machine.
                statusTestFile=$(status_test_file $testMachine)
                scp $testMachine:$buildDir/$statusTestFile . &> /dev/null

                # Parse the file
                statusTestLine=$(cat $statusTestFile)
                testProgress=$(echo $statusTestLine | awk '{print $2}')
                testStatus=$(echo $statusTestLine | awk '{print $3}')

                echo "Status for $testMachine is $statusTestLine"
                if [ "$testProgress" != "test_done" ]; then
                    allDoneForCurrMachine=0
                elif [ "$testStatus" != "Success" ]; then
                    statusForCurrMachine="Fail"
                fi
            done

            if [ "$allDoneForCurrMachine" -eq 0 ]; then
                allTestsAreDone=0
            else
                echo "$tarBall test_done $statusForCurrMachine" > $statusFile
            fi

        elif [ "$progress" != "test_done" ]; then
            # This can happen occasionally perhaps when the status file
            # we read is in the process of being written to and is empty.
            echo "Unknown progress value: '$progress'. Will wait."
            allTestsAreDone=0
        else
            echo "Status for $buildMachine is $statusLine"
        fi

    done

    # Stop if we finished testing on all machines
    if [ "$allTestsAreDone" -eq 1 ]; then break; fi

    echo Will sleep for $sleepTime seconds
    sleep $sleepTime
    echo " "

done

overallStatus="Success"

# Builds and tests finished. The documentation is now in
# dist-add/asp_book.pdf.
if [ ! -f "dist-add/asp_book.pdf" ]; then
    echo "Error: Could not find the documentation: dist-add/asp_book.pdf."
    echo "Error: Check if the build on $masterMachine which makes the doc succeded."
    overallStatus="Fail";
fi
echo Status after doc addition is $overallStatus

# Get the ASP version. Hopefully some machine has it.
version=""
for buildMachine in $buildMachines; do
    versionFile=$(version_file $buildMachine)
    localVersion=$(ssh $buildMachine \
        "cat $buildDir/$versionFile 2>/dev/null" 2>/dev/null)
    echo Version on $buildMachine is $localVersion
    if [ "$localVersion" != "" ]; then version=$localVersion; fi
done
if [ "$version" = "" ]; then
    version="None" # A non-empty string
    echo "Error: Could not determine the ASP version"
    overallStatus="Fail"
fi
echo Status after version check is $overallStatus

# Once we finished testing all builds, rename them for release, and
# record whether the tests passed.
statusMasterFile="status_master.txt"
rm -f $statusMasterFile
echo "Machine and status" >> $statusMasterFile
count=0
timestamp=$(date +%Y-%m-%d)
for buildMachine in $buildMachines; do

    # Check the status
    statusFile=$(status_file $buildMachine)
    statusLine=$(cat $statusFile)
    tarBall=$( echo $statusLine | awk '{print $1}' )
    progress=$( echo $statusLine | awk '{print $2}' )
    status=$( echo $statusLine | awk '{print $3}' )
    echo "$(date) Status for $buildMachine is $tarBall $progress $status"
    if [ "$status" != "Success" ]; then status="Fail"; fi
    if [ "$progress" != "test_done" ]; then
        echo "Error: Expecting the progress to be: test_done"
        status="Fail"
    fi

    # Check the tarballs
    if [[ ! $tarBall =~ \.tar\.bz2$ ]]; then
        echo "Error: Expecting '$tarBall' to be with .tar.bz2 extension"
            status="Fail"
    else
        if [ ! -f "$HOME/$buildDir/$tarBall" ]; then
            echo "Error: Could not find $HOME/$buildDir/$tarBall"
            status="Fail"
        fi
        echo "Renaming build $tarBall"
        tarBall=$(./auto_build/rename_build.sh $tarBall $version $timestamp)
        ans="$?"
        if [ "$ans" -ne 0 ]; then echo "Error: Renaming failed"; status="Fail"; fi
        if [ ! -f "$tarBall" ]; then echo "Error: Missing $tarBall $tarBall"; status="Fail"; fi
    fi
    if [ "$status" != "Success" ]; then overallStatus="Fail"; fi
    echo $buildMachine $status >> $statusMasterFile
    builds[$count]="$tarBall"
    ((count++))
done

# Cleanup the log dir
mkdir -p logs
rm -fv logs/*

# Copy the log files
for buildMachine in $buildMachines; do

    # Copy the build logs
    outputFile=$(output_file $buildDir $buildMachine)
    echo Copying log from $buildMachine:$outputFile
    rsync -avz $buildMachine:$outputFile logs 2>/dev/null

    # Append the test logs
    testMachines=$(get_test_machines $buildMachine $masterMachine)
    for testMachine in $testMachines; do
        outputTestFile=$(output_test_file $buildDir $testMachine)
        rsync -avz $testMachine:$outputTestFile logs 2>/dev/null
        echo "Logs for testing on $testMachine" >> logs/$(basename $outputFile)
        cat logs/$(basename $outputTestFile) >> logs/$(basename $outputFile)
    done
done

# Copy the builds to $releaseMachine and update the public link
ssh $releaseMachine "mkdir -p $releaseDir" 2>/dev/null
if [ "$overallStatus" = "Success" ]; then

    echo "" >> $statusMasterFile
    echo "Link: $link" >> $statusMasterFile
    echo "" >> $statusMasterFile
    echo "Paths on $releaseMachine" >> $statusMasterFile

    echo Wil copy doc and builds to $releaseMachine
    rsync -avz dist-add/asp_book.pdf $releaseMachine:$releaseDir 2>/dev/null
    len="${#builds[@]}"
    for ((count = 0; count < len; count++)); do
        tarBall=${builds[$count]}
        echo Copying $tarBall to $releaseMachine:$releaseDir
        rsync -avz $tarBall $releaseMachine:$releaseDir 2>/dev/null
        echo $releaseDir/$(basename $tarBall) >> $statusMasterFile
    done

    # Wipe older files on $releaseMachine and gen the index for today
    rsync -avz auto_build/rm_old.sh auto_build/gen_index.sh $releaseMachine:$releaseDir 2>/dev/null
    ssh $releaseMachine "$releaseDir/rm_old.sh $releaseDir 24 StereoPipeline-" 2>/dev/null
    ssh $releaseMachine "$releaseDir/gen_index.sh $releaseDir $version $timestamp" 2>/dev/null

fi

# Copy the logs to $releaseMachine
logDir="logs/$timestamp"
ssh $releaseMachine "mkdir -p $releaseDir/$logDir" 2>/dev/null
rsync -avz logs/* $releaseMachine:$releaseDir/$logDir  2>/dev/null
ssh $releaseMachine "$releaseDir/rm_old.sh $releaseDir/logs 24" 2>/dev/null

# List the logs in the report
echo "" >> $statusMasterFile
echo "Logs" >> $statusMasterFile
for log in $(ls logs |grep -v test); do
    echo "$link/$logDir/$log" >> $statusMasterFile
done

cat $statusMasterFile
echo Final status is $overallStatus

subject="ASP build $timestamp status is $overallStatus"
cat status_master.txt | mailx -s "$subject" $mailto
