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
virtualMachines="centos-32-5 centos-64-5 ubuntu-64-13"
buildMachines="amos $virtualMachines"

resumeRun=0 # Must be set to 0 in production. 1=Resume where it left off.
skipBuild=0 # Must be set to 0 in production. 1=Skip build, do testing.
skipRelease=0 # Must be set to 0 in production. 1=Don't make a public release.
timestamp=$(date +%Y-%m-%d)
sleepTime=30
local_mode=$1

mailto="oleg.alexandrov@nasa.gov oleg.alexandrov@gmail.com"
if [ "$resumeRun" -eq 0 ] && [ "$skipBuild" -eq 0 ] && \
    [ "$skipRelease" -eq 0 ] && [ "$local_mode" != "local_mode" ]; then
    mailto="$mailto z.m.moratto@nasa.gov SMcMichael@sgt-inc.com"
fi

currMachine=$(uname -n | perl -pi -e "s#\..*?\$##g")
if [ "$currMachine" != "$masterMachine" ]; then
    echo Error: Expecting the jobs to be launched from $masterMachine
    exit 1
fi

cd $HOME
mkdir -p $buildDir
cd $buildDir
echo "Work directory: $(pwd)"

# Unless running in local mode for test purposes, fetch from github
# the latest version of BinaryBuilder.
filesList=auto_build/filesToCopy.txt
if [ "$local_mode" != "local_mode" ]; then

    # Update from github
    dir="BinaryBuilder_newest"
    failure=1
    for ((i = 0; i < 600; i++)); do
        # Bugfix: Sometimes the github server is down, so do multiple attempts.
        echo "Cloning BinaryBuilder in attempt $i"
        rm -rf $dir
        git clone https://github.com/NeoGeographyToolkit/BinaryBuilder.git $dir
        failure="$?"
        if [ "$failure" -eq 0 ]; then break; fi
        sleep 60
    done
    if [ "$failure" -ne 0 ] || [ ! -d "$dir" ]; then
        echo "Failed to update from github"
        exit 1
    fi
    cd $dir
    files=$(\ls -ad * .git*)
    cp -rf $files ..
    cd ..
    rm -rf $dir

    # Need the list of files so that we can mirror those later to the
    # build machines
    echo $files > $filesList
fi

. $HOME/$buildDir/auto_build/utils.sh # load utilities
set_system_paths
start_vrts $virtualMachines
mkdir -p asp_tarballs

# Start the builds. The build script will copy back the built tarballs
# and status files.
for buildMachine in $buildMachines; do

    statusFile=$(status_file $buildMachine)
    
    if [ "$skipBuild" -ne 0 ] || [ "$resumeRun" -ne 0 ]; then
        statusLine=$(cat $statusFile)
        tarBall=$( echo $statusLine | awk '{print $1}' )
        progress=$( echo $statusLine | awk '{print $2}' )
    fi
    
    outputFile=$(output_file $buildDir $buildMachine)
    # Make sure all scripts are up-to-date on $buildMachine
    ./auto_build/push_code.sh $buildMachine $buildDir $filesList
    if [ "$?" -ne 0 ]; then exit 1; fi

    if [ "$skipBuild" -ne 0 ] && [ "$resumeRun" -eq 0 ]; then
        echo "$tarBall build_done" > $statusFile
        sleep 10
        continue
    fi
    if [ "$resumeRun" -eq 0 ] || [ "$progress" = "build_failed" ]; then
        # Set the status to now building
        echo "NoTarballYet now_building" > $statusFile
        for ((count = 0; count < 100; count++)); do
            # Several attempts to start the job
            ssh $buildMachine "nohup nice -19 $buildDir/auto_build/build.sh $buildDir $statusFile $masterMachine > $outputFile 2>&1&" 2>/dev/null
            sleep 10
            out=$(ssh $buildMachine "ps ux | grep build.sh | grep -v grep" \
                2>/dev/null)
            if [ "$out" != "" ]; then
                echo "Success starting on $buildMachine: $out";
                break
            fi
            echo "Trying to start build.sh at $(date) on $buildMachine in attempt $count"
        done
    fi
done

# Wipe all status test files before we start with testing.
if [ "$resumeRun" -eq 0 ] && [ "$skipBuild" -eq 0 ]; then
    for buildMachine in $buildMachines; do
        testMachines=$(get_test_machines $buildMachine $masterMachine)
        for testMachine in $testMachines; do
            statusTestFile=$(status_test_file $testMachine)
            rm -fv $statusTestFile
        done
    done
fi

# Whenever a build is done, launch tests for it. For some
# builds, tests are launched on more than one machine.
while [ 1 ]; do

    allTestsAreDone=1
    
    for buildMachine in $buildMachines; do

        statusFile=$(status_file $buildMachine)
        statusLine=$(cat $statusFile)
        tarBall=$(echo $statusLine | awk '{print $1}')
        progress=$(echo $statusLine | awk '{print $2}')
        testMachines=$(get_test_machines $buildMachine $masterMachine)
        
        if [ "$progress" = "now_building" ]; then
            echo "Build status for $buildMachine is $statusLine"
            allTestsAreDone=0
        elif [ "$progress" = "build_failed" ]; then
            # Nothing can be done for this machine
            echo "Build status for $buildMachine is $statusLine"
        elif [ "$progress" = "build_done" ]; then

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
                ssh $testMachine "nohup nice -19 $buildDir/auto_build/run_tests.sh $buildDir $tarBall $testDir $statusTestFile $masterMachine > $outputTestFile 2>&1&" 2>/dev/null
            done
            
        elif [ "$progress" = "now_testing" ]; then
            
            # See if we finished testing the current build on all machines
            allDoneForCurrMachine=1
            statusForCurrMachine="Success"
            for testMachine in $testMachines; do
                statusTestFile=$(status_test_file $testMachine)
                statusTestLine=$(cat $statusTestFile)
                testProgress=$(echo $statusTestLine | awk '{print $2}')
                testStatus=$(echo $statusTestLine | awk '{print $3}')
                echo "Test status for $testMachine is $statusTestLine"
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
        fi
        
    done

    # Stop if we finished testing on all machines
    if [ "$allTestsAreDone" -eq 1 ]; then break; fi
    
    echo Will sleep for $sleepTime seconds
    sleep $sleepTime
    echo " "
    
done

overallStatus="Success"

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
    overallStatus="Fail"
fi

# Once we finished testing all builds, rename them for release, and
# record whether the tests passed.
statusMasterFile="status_master.txt"
rm -f $statusMasterFile
echo "Machine and status" >> $statusMasterFile
count=0
for buildMachine in $buildMachines; do

    # Check the status
    statusFile=$(status_file $buildMachine)
    statusLine=$(cat $statusFile)
    tarBall=$( echo $statusLine | awk '{print $1}' )
    progress=$( echo $statusLine | awk '{print $2}' )
    status=$( echo $statusLine | awk '{print $3}' )
    echo $(date) Status for $buildMachine is $tarBall $progress $status
    if [ "$status" != "Success" ]; then status="Fail"; fi
    if [ "$progress" != "test_done" ]; then
        echo "Error: Expecting the progress to be: test_done"
        status="Fail"
    fi
    
    # Check the tarballs
    if [[ ! $tarBall =~ \.tar\.bz2$ ]]; then
        echo "Expecting '$tarBall' to be with .tar.bz2 extension"
            status="Fail"
    else
        if [ ! -f "$HOME/$buildDir/$tarBall" ]; then
            echo "Error: Could not find $HOME/$buildDir/$tarBall"
            status="Fail"
        fi
        echo "Renaming build $tarBall"
        tarBall=$(./auto_build/rename_build.sh $tarBall $version $timestamp)
        if [ "$?" -ne 0 ]; then "echo Renaming failed"; status="Fail"; fi
        if [ ! -f "$tarBall" ]; then echo Missing $tarBall; status="Fail"; fi
    fi
    if [ "$status" != "Success" ]; then overallStatus="Fail"; fi
    echo $buildMachine $status >> $statusMasterFile
    builds[$count]="$tarBall"
    ((count++))
done

# Copy the log files
mkdir -p logs
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
if [ "$overallStatus" = "Success" ] && [ "$skipRelease" = "0" ]; then

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

    if [ "$local_mode" != "local_mode" ]; then
        # Mark the fact that we've built/tested for the current state of remote repositories
        cp -fv $curr_hash_file $done_hash_file
    fi
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

subject="ASP build $timestamp status is $overallStatus"
cat status_master.txt | mailx -s "$subject" $mailto
