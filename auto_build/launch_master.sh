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

# See auto_build/README.txt for more details.

# To do: Must push the tests to other machines when new tests are added.
# To do: When ISIS gets updated, need to update the base_system
# on each machine presumambly as that one is used in regressions.

version="2.2.2_post" # Must change the version in the future
buildDir=projects/BinaryBuilder     # must be relative to home dir
testDir=projects/StereoPipelineTest # must be relative to home dir

# Machines and paths
releaseHost="byss"
releaseDir="/byss/docroot/stereopipeline/daily_build"
link="http://byss.arc.nasa.gov/stereopipeline/daily_build"
launchMachines="pfe25 zula amos andey"
zulaSlaves="zula centos-64-5 centos-32-5"

resumeRun=0 # Must be set to 0 in production. 1=Resume where it left off.
skipBuild=0 # Must be set to 0 in production. 1=Skip build, do testing.
skipRelease=0 # Must be set to 0 in production. 1=Don't make a public release.
timestamp=$(date +%Y-%m-%d)
user=$(whoami)
sleepTime=30
local_mode=$1

mailto="oleg.alexandrov@nasa.gov oleg.alexandrov@gmail.com"
if [ "$resumeRun" -eq 0 ] && [ "$skipBuild" -eq 0 ] && \
    [ "$skipRelease" -eq 0 ] && [ "$local_mode" != "local_mode" ]; then
    mailto="$mailto z.m.moratto@nasa.gov SMcMichael@sgt-inc.com"
fi

cd $HOME
if [ ! -d "$buildDir" ]; then echo "Error: Directory: $buildDir does not exist"; exit 1; fi;
if [ ! -d "$testDir" ];  then echo "Error: Directory: $testDir does not exist"; exit 1; fi;
cd $buildDir
echo "Work directory: $(pwd)"

. $HOME/$buildDir/auto_build/utils.sh # load utilities
set_system_paths

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
    # slave machines
    echo $files > auto_build/filesToCopy.txt
fi

for launchMachine in $launchMachines; do

    if [ "$launchMachine" = "zula" ]; then
        buildMachines=$zulaSlaves
    else
        buildMachines=$launchMachine
    fi

    for buildMachine in $buildMachines; do
        statusFile=$(status_file $buildMachine)
        statusLine=$(ssh $user@$launchMachine \
            "cat $buildDir/$statusFile 2>/dev/null" 2>/dev/null)
        tarBall=$( echo $statusLine | awk '{print $1}' )
        state=$( echo $statusLine | awk '{print $2}' )
        status=$( echo $statusLine | awk '{print $3}' )

        outputFile=$(output_file $buildDir $buildMachine)
        # Make sure all scripts are up-to-date on the target machine
        ./auto_build/push_code.sh $user $launchMachine $buildDir 2>/dev/null
        if [ "$skipBuild" -ne 0 ] && [ "$resumeRun" -eq 0 ]; then
            ssh $user@$launchMachine "echo $tarBall build_done Success > $buildDir/$statusFile" 2>/dev/null
            sleep 10
            continue
        fi
        if [ "$resumeRun" -eq 0 ] || [ "$state" = "build_failed" ]; then
            # Set the status to now building
            ssh $user@$launchMachine "echo NoTarballYet now_building > $buildDir/$statusFile" 2>/dev/null
            sleep 10
            for ((count = 0; count < 100; count++)); do
                # Several attempts to start the job
                sleep 10
                ssh $user@$launchMachine "nohup nice -19 $buildDir/auto_build/launch_slave.sh $buildMachine $buildDir $statusFile < /dev/null > $outputFile 2>&1&" 2>/dev/null
                out=$(ssh $user@$launchMachine "ps ux | grep launch_slave.sh | grep -v grep" \
                    2>/dev/null)
                if [ "$out" != "" ]; then echo "Success starting on $launchMachine: $out"; break; fi
                echo "Trying to start launch_slave.sh at $(date) on $launchMachine in attempt $count"
            done
        fi
    done
done

# Wait until the builds are done and run the regressions.
# Note that on some machines more than one build happens,
# then do one regression run at a time.
while [ 1 ]; do
    allDone=1
    for launchMachine in $launchMachines; do

        if [ "$launchMachine" = "zula" ]; then
            buildMachines=$zulaSlaves
        else
            buildMachines=$launchMachine
        fi

        # See how many regressions are now running on the launch
        # machine and whether not all are done
        numRunning=0
        for buildMachine in $buildMachines; do
            statusFile=$(status_file $buildMachine)
            statusLine=$(ssh $user@$launchMachine \
                "cat $buildDir/$statusFile 2>/dev/null" 2>/dev/null)
            tarBall=$( echo $statusLine | awk '{print $1}' )
            state=$( echo $statusLine | awk '{print $2}' )
            status=$( echo $statusLine | awk '{print $3}' )
            echo $(date) Status for $buildMachine is $tarBall $state $status
            if [ "$state" != "test_done" ]; then
                allDone=0
            fi
            if [ "$state" = "now_testing" ]; then
                ((numRunning++));
            fi
        done
        if [ "$numRunning" -ne 0 ]; then continue; fi

        # No regressions are running, see if to start one
        for buildMachine in $buildMachines; do
            statusFile=$(status_file $buildMachine)
            outputFile=$(output_file $buildDir $buildMachine)
            statusLine=$(ssh $user@$launchMachine \
                "cat $buildDir/$statusFile 2>/dev/null" 2>/dev/null)
            tarBall=$( echo $statusLine | awk '{print $1}' )
            state=$( echo $statusLine | awk '{print $2}' )

            if [ "$state" = "build_done" ]; then
                # Build is done, no other builds are being tested,
                # so test the current build
                echo Will launch tests for $buildMachine
                ssh $user@$launchMachine "echo $tarBall now_testing > $buildDir/$statusFile 2>/dev/null" 2>/dev/null
                sleep 5; # Give the filesystem enough time to react
                ssh $user@$launchMachine "nohup nice -19 $buildDir/auto_build/run_tests.sh $buildMachine $tarBall $testDir $buildDir $statusFile >> $outputFile 2>&1&" 2>/dev/null
                allDone=0
                break # launch just one testing session at a time
            fi
        done

    done

    if [ $allDone -eq 1 ]; then
        break;
    fi
    echo Will sleep for $sleepTime seconds
    sleep $sleepTime
    echo " "

done

# Copy back the documentation processed on zula which has LaTeX.
# This must happen after all builds finished, as otherwise git
# will fetch an outdated version during build.
overallStatus="Success"
for launchMachine in $launchMachines; do
    if [ "$launchMachine" = "zula" ]; then
        if [ "$(uname -n)" != "zula" ]; then
            rm -fv dist-add/asp_book.pdf
        fi
        echo Copying the documentation from $user@$launchMachine
        rsync -avz $user@$launchMachine:$buildDir/dist-add/asp_book.pdf \
            dist-add
        if [ ! -f "dist-add/asp_book.pdf" ]; then
            echo "Error: Missing dist-add/asp_book.pdf"
            overallStatus="Fail"
        fi
    fi
done

# Once the regressions are finished, copy the builds to the master
# machine, rename them for release, and record whether the regressions
# passed. Copy the logfiles as well.
statusMasterFile="status_master.txt"
rm -f $statusMasterFile
echo "Machine and status" >> $statusMasterFile
count=0
for launchMachine in $launchMachines; do

    if [ "$launchMachine" = "zula" ]; then
        buildMachines=$zulaSlaves
    else
        buildMachines=$launchMachine
    fi

    for buildMachine in $buildMachines; do

        # Check the status
        statusFile=$(status_file $buildMachine)
        outputFile=$(output_file $buildDir $buildMachine)
        statusLine=$(ssh $user@$launchMachine \
            "cat $buildDir/$statusFile 2>/dev/null" 2>/dev/null)
        tarBall=$( echo $statusLine | awk '{print $1}' )
        state=$( echo $statusLine | awk '{print $2}' )
        status=$( echo $statusLine | awk '{print $3}' )
        echo $(date) Status for $buildMachine is $tarBall $state $status
        if [ "$status" != "Success" ]; then status="Fail"; fi
        if [ "$state" != "test_done" ]; then
            echo "Error: Expecting the state to be: test_done"
            status="Fail"
        fi

        # Copy the tarballs
        mkdir -p asp_tarballs
        if [ "$tarBall" = "Fail" ]; then
            status="Fail"
        else
            echo Copying $user@$launchMachine:$buildDir/$tarBall to asp_tarballs
            rsync -avz $user@$launchMachine:$buildDir/$tarBall asp_tarballs 2>/dev/null
            if [ ! -f "$HOME/$buildDir/$tarBall" ]; then
                echo "Error: Could not copy $HOME/$buildDir/$tarBall"
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

        # Copy the log files
        mkdir -p logs
        echo Copying log from $user@$launchMachine:$outputFile
        rsync -avz $user@$launchMachine:$outputFile logs 2>/dev/null

    done
done

ssh $user@$releaseHost "mkdir -p $releaseDir"

# Copy the builds to $releaseHost and update the public link
if [ "$overallStatus" = "Success" ] && [ "$skipRelease" = "0" ]; then

    echo "" >> $statusMasterFile
    echo "Link: $link" >> $statusMasterFile
    echo "" >> $statusMasterFile
    echo "Paths on $releaseHost" >> $statusMasterFile

    echo Wil copy doc and builds to $releaseHost
    rsync -avz dist-add/asp_book.pdf $user@$releaseHost:$releaseDir 2>/dev/null
    len="${#builds[@]}"
    for ((count = 0; count < len; count++)); do
        tarBall=${builds[$count]}
        echo Copying $tarBall to $user@$releaseHost:$releaseDir
        rsync -avz $tarBall $user@$releaseHost:$releaseDir 2>/dev/null
        rm -f $tarBall # No need to keep this around
        echo $releaseDir/$(basename $tarBall) >> $statusMasterFile
    done

    # Wipe older files on $releaseHost and gen the index for today
    rsync -avz auto_build/rm_old.sh auto_build/gen_index.sh $user@$releaseHost:$releaseDir 2>/dev/null
    ssh $user@$releaseHost "$releaseDir/rm_old.sh $releaseDir 12 StereoPipeline-" 2>/dev/null
    ssh $user@$releaseHost "$releaseDir/gen_index.sh $releaseDir $version $timestamp" 2>/dev/null
fi

# Copy the logs
logDir="logs/$timestamp"
ssh $user@$releaseHost "mkdir -p $releaseDir/$logDir" 2>/dev/null
rsync -avz logs/* $user@$releaseHost:$releaseDir/$logDir 2>/dev/null
ssh $user@$releaseHost "$releaseDir/rm_old.sh $releaseDir/logs 12" 2>/dev/null

# List the logs in the report
echo "" >> $statusMasterFile
echo "Logs" >> $statusMasterFile
for log in $(ls logs); do
    echo "$link/$logDir/$log" >> $statusMasterFile
done

cat $statusMasterFile

subject="ASP build $timestamp status is $overallStatus"
mailx $mailto -s "$subject" < $statusMasterFile
