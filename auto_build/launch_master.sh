#!/bin/bash

# Launch and test all builds on all machines and notify the user of the status.
# In case of success, upload the builds to the GitHub release area. 

# The Linux build is built and tested locally. The macOS one is built
# and tested in the cloud.

# See auto_build/README.txt for more information.

buildDir=projects/BinaryBuilder     # must be relative to home dir
testDir=projects/StereoPipelineTest # must be relative to home dir

# Machines and paths
masterMachine="lunokhod1"
buildPlatforms="localLinux cloudMacX64 cloudMacArm64"

resumeRun=0 # Must be set to 0 in production. 1=Resume where it left off.
if [ "$(echo $* | grep resume)" != "" ]; then resumeRun=1; fi
sleepTime=30

# If to skip tests. Must be set to 0 in production.
skipTests=0
if [ "$(echo $* | grep skip_tests)" != "" ]; then skipTests=1; echo "Will skip tests."; fi

mailto="oleg.alexandrov@nasa.gov"

cd $HOME
mkdir -p $buildDir
cd $buildDir
echo "Work directory: $(pwd)"

# Set system paths and load utilities
source $HOME/$buildDir/auto_build/utils.sh

currMachine=$(machine_name)
if [ "$currMachine" != "$masterMachine" ]; then
    echo Error: Expecting the jobs to be launched from $masterMachine
    exit 1
fi

mkdir -p asp_tarballs

# Wipe the logs and status files of previous tests. We do it before the builds start,
# as we won't get to the tests if the builds fail.
if [ "$resumeRun" -eq 0 ]; then
    for buildPlatform in $buildPlatforms; do
        testMachine=$(get_test_machine $buildPlatform $masterMachine)
        echo Test machine for $buildPlatform is $testMachine
        outputTestFile=$(output_test_file $buildDir $testMachine)
        echo "" > $HOME/$outputTestFile
        # Copy to the build machine
        scp $HOME/$outputTestFile $testMachine:$outputTestFile 2> /dev/null
    done
fi

# Start the builds. The build script will copy back the built tarballs
# and status files. Note that we build on $masterMachine too,
# as that is where the doc gets built.
echo "Starting up the builds."
for buildPlatform in $buildPlatforms; do

    # The cloud macOS build is monitored on $masterMachine
    buildMachine=$(get_build_machine $buildPlatform $masterMachine)
    echo "Setting up and launching $buildPlatform on $buildMachine"

    statusFile=$(status_file $buildPlatform)
    outputFile=$(output_file $buildDir $buildPlatform)

    if [ "$resumeRun" -ne 0 ]; then
        # If resuming a run, $statusFile already has some data
        statusLine=$(cat $statusFile 2>/dev/null)
        tarBall=$(echo $statusLine | awk '{print $1}')
        progress=$(echo $statusLine | awk '{print $2}')
        status=$(echo $statusLine | awk '{print $3}')
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
               "$buildDir $statusFile $buildPlatform $masterMachine" $outputFile
    if [ $? -ne 0 ]; then
      echo Error: Unable to launch build on $buildMachine
      exit 1
    fi
    
done

# Whenever a build is done, launch tests for it. For the cloud builds, the test
# will be flagged as done by now. That happens in build.sh.
while [ 1 ]; do

    allTestsAreDone=1
    for buildPlatform in $buildPlatforms; do

        # Parse the current status for this build machine
        statusFile=$(status_file $buildPlatform)
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
        buildMachine=$(get_build_machine $buildPlatform $masterMachine)
        testMachine=$(get_test_machine $buildPlatform $masterMachine)
        echo Status file is $statusFile
        echo Tarball is $tarBall
        echo Progress is $progress
        echo Build machine for $buildPlatform is $buildMachine
        echo Test machine for $buildPlatform is $testMachine

        if [ "$progress" = "now_building" ]; then
            # Keep waiting
            echo "Status for $buildPlatform is $statusLine"
            allTestsAreDone=0
        elif [ "$progress" = "build_failed" ]; then
            # Nothing can be done for this machine
            echo "Status for $buildPlatform is $statusLine"
        elif [ "$progress" = "build_done" ]; then

            echo "Fetching the completed build"
            # Grab the build file from the build machine, unless on same machine
            if [ "$buildMachine" != "$masterMachine" ]; then
              echo "rsync -avz $buildMachine:$buildDir/$tarBall $buildDir/asp_tarballs/"
              rsync -avz  $buildMachine:$buildDir/$tarBall \
                          $HOME/$buildDir/asp_tarballs/ 2>/dev/null
            fi

            # Build for current machine is done, need to test it
            allTestsAreDone=0
            echo "$tarBall now_testing" > $statusFile
            outputTestFile=$(output_test_file $buildDir $testMachine)

            echo "Will launch tests on $testMachine"
            echo "$tarBall now_testing" > $statusFile

            # This logic is not needed when there's only one local machine
            # # Make sure all scripts are up-to-date on $testMachine
            # echo Test: Pushing code to $testMachine for $buildPlatform
            # ./auto_build/push_code.sh $testMachine $buildDir $filesList
            # if [ "$?" -ne 0 ]; then exit 1; fi
            # # Copy the tarball to the test machine
            # echo Copy $tarBall for $buildPlatform to $testMachine 
            # ssh $testMachine "mkdir -p $buildDir/asp_tarballs" 2>/dev/null
            # rsync -avz $tarBall $testMachine:$buildDir/asp_tarballs \
            #     2>/dev/null

            sleep 5; # Give the filesystem enough time to react
            if [ "$skipTests" -eq 0 ]; then
                # Start the tests
                echo will test $buildPlatform on $testMachine
                robust_ssh $testMachine $buildDir/auto_build/run_tests.sh    \
                    "$buildDir $tarBall $testDir $statusFile $masterMachine" \
                    $outputTestFile
            else
                # Fake it, so that we skip the testing
                echo "$tarBall test_done Success" > $statusFile
            fi

        elif [ "$progress" = "now_testing" ]; then

            # See if we finished testing the current build on all machines
            allDoneForCurrMachine=1
            statusForCurrMachine="Success"

            # Grab the test status file for this machine.
            echo Fetch $testMachine:$buildDir/$statusFile
            scp $testMachine:$buildDir/$statusFile . &> /dev/null

            # Parse the file
            statusLine=$(cat $statusFile)
            testProgress=$(echo $statusLine | awk '{print $2}')
            testStatus=$(echo $statusLine | awk '{print $3}')
            echo Test progress is $testProgress
            echo Test status is $testStatus

            echo "Status for $testMachine is $statusLine"
            if [ "$testProgress" != "test_done" ]; then
                allDoneForCurrMachine=0
            elif [ "$testStatus" != "Success" ]; then
                # This is case-sensitive
                statusForCurrMachine="Fail"
            fi

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
            echo "Status for $buildPlatform is $statusLine"
        fi

    done

    # Stop if we finished testing on all machines
    if [ "$allTestsAreDone" -eq 1 ]; then break; fi

    echo Will sleep for $sleepTime seconds
    sleep $sleepTime
    echo " "

done

overallStatus="Success"

# Check the status of all builds.
statusMasterFile="status_master.txt"
rm -f $statusMasterFile
echo "Machine and status" >> $statusMasterFile
count=0
timestamp=$(date -u +%Y-%m-%d) # UTC time, for consistency with GitHub Actions
for buildPlatform in $buildPlatforms; do
    # Check the status
    statusFile=$(status_file $buildPlatform)
    statusLine=$(cat $statusFile)
    tarBall=$( echo $statusLine | awk '{print $1}' )
    progress=$( echo $statusLine | awk '{print $2}' )
    statusAns=$( echo $statusLine | awk '{print $3}' )
    echo "$(date) Status for $buildPlatform is $tarBall $progress $statusAns"
    if [ "$statusAns" != "Success" ]; then statusAns="Fail"; fi
    if [ "$progress" != "test_done" ]; then
        echo "Error: Expecting the progress to be: test_done"
        statusAns="Fail"
    fi
    echo Status so far is $statusAns
    
    # Check the tarballs
    if [[ ! $tarBall =~ \.tar\.bz2$ ]]; then
        echo "Error: Expecting '$tarBall' to be with .tar.bz2 extension"
            statusAns="Fail"
    else
        if [ ! -f "$HOME/$buildDir/$tarBall" ]; then
            echo "Error: Could not find $HOME/$buildDir/$tarBall"
            statusAns="Fail"
        fi
    fi
    echo Status is $statusAns
    
    if [ "$statusAns" != "Success" ]; then overallStatus="Fail"; fi
    echo $buildPlatform $statusAns >> $statusMasterFile
    builds[$count]="$tarBall"
    ((count++))
done

# Cleanup the log dir
mkdir -p logs
rm -fv logs/*

# Copy the log files
for buildPlatform in $buildPlatforms; do
    # Copy the build logs
    outputFile=$(output_file $buildDir $buildPlatform)
    buildMachine=$(get_build_machine $buildPlatform $masterMachine)
    echo Copying log from $buildMachine:$outputFile
    rsync -avz $buildMachine:$outputFile logs 2>/dev/null
    
    # Append the test logs
    testMachine=$(get_test_machine $buildPlatform $masterMachine)
    outputTestFile=$(output_test_file $buildDir $testMachine)
    rsync -avz $testMachine:$outputTestFile logs 2>/dev/null
    echo "Logs for testing on $testMachine" >> logs/$(basename $outputFile)
    cat logs/$(basename $outputTestFile) >> logs/$(basename $outputFile)
done

# Copy the builds to GitHub
if [ "$overallStatus" = "Success" ]; then

    binaries=""
    len="${#builds[@]}"
    for ((count = 0; count < len; count++)); do
        tarBall=${builds[$count]}
        tarBall=$(realpath $tarBall)
        binaries="$binaries $tarBall"
    done
    
    upload_to_github "$binaries" $timestamp
    if [ $? -ne 0 ]; then
        echo Error: Failed to upload to GitHub
        overallStatus="Fail"
    fi
    url="https://github.com/NeoGeographyToolkit/StereoPipeline/releases"
    echo See the daily build at $url >> status_master.txt
fi

cat $statusMasterFile
echo Final status is $overallStatus

# Send mail to the user
subject="ASP build $timestamp status is $overallStatus"
# For some reason sending mail from lunokhod1 does not work.
#cat status_master.txt | mailx -s "$subject" $mailto
# But it works from lunokhod2, so do it that way.
# TODO(oalexan1): A better approach could be some Git action, perhaps.
rsync -avzP status_master.txt lunokhod2:$(pwd)
ssh lunokhod2 "cat $(pwd)/status_master.txt | mailx -s '$subject' $mailto"
