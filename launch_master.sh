#!/bin/bash

# This is the master script, launching and testing all builds on all
# machines. Copy the resulting tested builds to the release directory.

# To do: Find a way to remove old tarballs from asp_tarballs
# To do: where to put max_err.pl and cmp_images.sh
# To do: How to ensure that the stereo from right dir is executed
# To do: Rm the temororary flags, and the git clone comment, in run_tests.sh
# To do: Now we will wait forever if build.sh fails
# To do: Need to upgrade StereoPipelineTest from git!
# To do: Create recipe for how to install sparse_disp and put that on amos and zula
# To do: Deal with the issues on the mac
# To do: Put the nohup back on mac!
# To do: Fix and test the ssh commands!
# To do: Put zula in ssh config
# To do: test on zula runs at the same time!
# To do: Deal with clang!
# To do: Give proper name to release
# To do: Deal with docs
# To do: Cache cloning BinaryBuilder
# To do: Keep just several recent builds

tag=$(date +%Y-%m-%d)
sleepTime=30
buildDir=projects/BinaryBuilder     # must be relative to home dir
testDir=projects/StereoPipelineTest # must be relative to home dir
user=$(whoami)
zula="50.131.219.181"
#launchMachines="pfe25 amos $zula" # temporary!!
launchMachines="pfe25 $zula amos" # temporary!!
#launchMachines="pfe25" # temporary!!
#launchMachines="amos" # temporary!!!
#launchMachines="$zula amos" # temporary!!!
zulaSlaves="$zula centos-64-5" # add centos-32-5

cd $HOME
if [ ! -d "$buildDir" ]; then echo "Directory: $buildDir does not exist"; exit 1; fi;
if [ ! -d "$testDir" ];  then echo "Directory: $testDir does not exist"; exit 1; fi;
cd $buildDir

for launchMachine in $launchMachines; do


    if [ "$launchMachine" == "$zula" ]; then
        buildMachines=$zulaSlaves
        port=9229
    else
        buildMachines=$launchMachine
        port=22
    fi

    for buildMachine in $buildMachines; do
        statusFile="status_"$buildMachine"_"$tag".txt"
        # Make sure all scripts are up-to-date on the target machine
        rsync -avz -e "ssh -p $port" *sh $user@$launchMachine:$buildDir >/dev/null 2>&1

#         # temporary!!!
#         # Set the status to now building
#         echo ssh $user@$launchMachine -p $port "echo NoTarballYet now_building > $buildDir/$statusFile 2>/dev/null" 2>/dev/null # temporary!!!
#         ssh $user@$launchMachine -p $port "echo NoTarballYet now_building > $buildDir/$statusFile 2>/dev/null" 2>/dev/null
#         sleep 5; # Give the filesystem enough time to react
#         echo ssh $user@$launchMachine -p $port "$buildDir/launch_slave.sh $buildMachine $buildDir $statusFile > $buildDir/output_$statusFile 2>&1&" 2>/dev/null # temporary!!!
#         ssh $user@$launchMachine -p $port "$buildDir/launch_slave.sh $buildMachine $buildDir $statusFile > $buildDir/output_$statusFile 2>&1&" 2>/dev/null
    done
done

# On the machines on which the builds are done, and no regressions are running, start one.
while [ 1 ]; do

    allDone=1
    for launchMachine in $launchMachines; do

        if [ "$launchMachine" == "$zula" ]; then
            buildMachines=$zulaSlaves
            port=9229
        else
            buildMachines=$launchMachine
            port=22
        fi

        # See how many regressions are now running on the launch machine and whether not all are done
        numRunning=0
        for buildMachine in $buildMachines; do
            statusFile="status_"$buildMachine"_"$tag".txt"
            statusLine=$(ssh $user@$launchMachine -p $port \
                "cat $buildDir/$statusFile 2>/dev/null" 2>/dev/null)
            tarBall=$( echo $statusLine | awk '{print $1}' )
            status=$( echo $statusLine | awk '{print $2}' )
            echo $(date) Status for $buildMachine is $tarball $status
            if [ "$status" != "test_done" ]; then
                allDone=0
            fi
            if [ "$status" = "now_testing" ]; then
                ((numRunning++));
            fi
        done
        if [ "$numRunning" -ne 0 ]; then continue; fi

        # No regressions are running, see if to start one
        for buildMachine in $buildMachines; do
            statusFile="status_"$buildMachine"_"$tag".txt"
            statusLine=$(ssh $user@$launchMachine -p $port \
                "cat $buildDir/$statusFile 2>/dev/null" 2>/dev/null)
            tarBall=$( echo $statusLine | awk '{print $1}' )
            status=$( echo $statusLine | awk '{print $2}' )

            if [ "$status" = "build_done" ]; then
                # Build is done, no other builds are being tested, so test the current build
                echo Will launch tests for $buildMachine
                ssh $user@$launchMachine -p $port "echo $tarBall now_testing > $buildDir/$statusFile 2>/dev/null" 2>/dev/null
                sleep 5; # Give the filesystem enough time to react
                ssh $user@$launchMachine -p $port "$buildDir/run_tests.sh $tarBall $testDir $buildDir $statusFile >> $buildDir/output_$statusFile 2>&1&" 2>/dev/null
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

masterStatus="masterStatus.txt"
rm -f $masterStatus
for launchMachine in $launchMachines; do

    if [ "$launchMachine" == "$zula" ]; then
        buildMachines=$zulaSlaves
        port=9229
    else
        buildMachines=$launchMachine
        port=22
    fi

    numRunning=0
    for buildMachine in $buildMachines; do
        statusFile="status_"$buildMachine"_"$tag".txt"
        statusLine=$(ssh $user@$launchMachine -p $port \
            "cat $buildDir/$statusFile 2>/dev/null" 2>/dev/null)
        tarBall=$( echo $statusLine | awk '{print $1}' )
        status=$( echo $statusLine | awk '{print $2}' )
        fail=$( echo $statusLine | awk '{print $3}' )
        echo $(date) Status for $buildMachine is $tarBall $status $fail
        if [ "$fail" != "0" ]; then fail=1; fi
        if [ "$status" != "test_done" ]; then
            echo "Expecting the status to be: test_done"
            exit 1;
        fi

        mkdir -p asp_tarballs
        rsync -avz -e "ssh -p $port" $user@$launchMachine:$tarBall asp_tarballs 2>/dev/null
        if [ ! -f "$HOME/$tarBall" ]; then
            echo "Could not copy $HOME/$tarBall"
            fail=1
        fi
        echo $tarBall $fail >> $masterStatus
    done
done