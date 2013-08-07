#!/bin/bash

# Launch and test all builds on all machines. Then notify the user of
# the status. In case of success, copy the resulting builds to byss.
# We assume all machines we need (byss, zula, amos, pfe25,
# centos-64-5, centos-32-5) are set up properly for login without
# password and their details are in .ssh/config.

# To do: See the .py to do list.
# Remove all but latest several builds on byss.
# To do: Fix the 32 bit build.
# To do: test rename_build.sh with 32 bit.
# To do: where to put max_err.pl and cmp_images.sh
# To do: How to ensure that the stereo from right dir is executed
# To do: Rm the temororary flags, and the git clone comment, in run_tests.sh
# To do: Need to upgrade StereoPipelineTest from git!
# To do: Create recipe for how to install sparse_disp and put that on amos and zula
# To do: Deal with the issues on the mac
# To do: test on zula runs at the same time!
# To do: Deal with docs
# To do: Cache cloning BinaryBuilder
# To do: Move build stuff to its own auto_build dir
# To do: Prepend errors with Error:. Search for exit 1.

tag=$(date +%Y-%m-%d)
sleepTime=30
buildDir=projects/BinaryBuilder     # must be relative to home dir
testDir=projects/StereoPipelineTest # must be relative to home dir
user=$(whoami)
#launchMachines="pfe25 amos zula" # temporary!!
#launchMachines="pfe25 zula amos" # temporary!!
launchMachines="pfe25 zula" # temporary!!
#launchMachines="amos" # temporary!!!
#launchMachines="zula amos" # temporary!!!
zulaSlaves="zula centos-64-5" # add centos-32-5
byss="byss"
byssPath="/byss/docroot/stereopipeline/daily_build"
#mailto="oleg.alexandrov@nasa.gov" # Mails sent to NASA don't always arrive!!!
mailto="oleg.alexandrov@gmail.com" # Just one user

cd $HOME
if [ ! -d "$buildDir" ]; then echo "Directory: $buildDir does not exist"; exit 1; fi;
if [ ! -d "$testDir" ];  then echo "Directory: $testDir does not exist"; exit 1; fi;
cd $buildDir

for launchMachine in $launchMachines; do


    if [ "$launchMachine" == "zula" ]; then
        buildMachines=$zulaSlaves
    else
        buildMachines=$launchMachine
    fi

    for buildMachine in $buildMachines; do
        statusFile="status_"$buildMachine".txt"
        # Make sure all scripts are up-to-date on the target machine
        rsync -avz *sh $user@$launchMachine:$buildDir >/dev/null 2>&1

#         # temporary!!!
#         # Set the status to now building
#         ssh $user@$launchMachine "echo NoTarballYet now_building > $buildDir/$statusFile 2>/dev/null" 2>/dev/null
#         sleep 5; # Give the filesystem enough time to react
#         ssh $user@$launchMachine "$buildDir/launch_slave.sh $buildMachine $buildDir $statusFile > $buildDir/output_$statusFile 2>&1&" 2>/dev/null
    done
done

# Wait until the builds are done and run the regressions.
# Note that on some machines more than one build happens,
# then do one regression run at a time.
while [ 1 ]; do
    allDone=1
    for launchMachine in $launchMachines; do

        if [ "$launchMachine" == "zula" ]; then
            buildMachines=$zulaSlaves
        else
            buildMachines=$launchMachine
        fi

        # See how many regressions are now running on the launch
        # machine and whether not all are done
        numRunning=0
        for buildMachine in $buildMachines; do
            statusFile="status_"$buildMachine".txt"
            statusLine=$(ssh $user@$launchMachine \
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
            statusFile="status_"$buildMachine".txt"
            statusLine=$(ssh $user@$launchMachine \
                "cat $buildDir/$statusFile 2>/dev/null" 2>/dev/null)
            tarBall=$( echo $statusLine | awk '{print $1}' )
            status=$( echo $statusLine | awk '{print $2}' )

            if [ "$status" = "build_done" ]; then
                # Build is done, no other builds are being tested,
                # so test the current build
                echo Will launch tests for $buildMachine
                ssh $user@$launchMachine "echo $tarBall now_testing > $buildDir/$statusFile 2>/dev/null" 2>/dev/null
                sleep 5; # Give the filesystem enough time to react
                ssh $user@$launchMachine "$buildDir/run_tests.sh $tarBall $testDir $buildDir $statusFile >> $buildDir/output_$statusFile 2>&1&" 2>/dev/null
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

# Once the regressions are finished, copy the builds to the master
# machine, rename them for release, and record whether the regressions
# passed.
masterStatus="masterStatus.txt"
overallStatus="Success"
rm -f $masterStatus
count=0
for launchMachine in $launchMachines; do

    if [ "$launchMachine" == "zula" ]; then
        buildMachines=$zulaSlaves
    else
        buildMachines=$launchMachine
    fi

    numRunning=0
    for buildMachine in $buildMachines; do
        statusFile="status_"$buildMachine".txt"
        statusLine=$(ssh $user@$launchMachine \
            "cat $buildDir/$statusFile 2>/dev/null" 2>/dev/null)
        tarBall=$( echo $statusLine | awk '{print $1}' )
        status=$( echo $statusLine | awk '{print $2}' )
        flag=$( echo $statusLine | awk '{print $3}' )
        echo $(date) Status for $buildMachine is $tarBall $status $flag
        if [ "$flag" != "Success" ]; then flag="Fail"; fi
        if [ "$status" != "test_done" ]; then
            echo "Expecting the status to be: test_done"
            flag="Fail"
        fi

        mkdir -p asp_tarballs
        rsync -avz $user@$launchMachine:$buildDir/$tarBall asp_tarballs 2>/dev/null
        if [ ! -f "$HOME/$buildDir/$tarBall" ]; then
            echo "Could not copy $HOME/$buildDir/$tarBall"
            flag="Fail"
        fi
        if [ "$flag" != "Success" ]; then overallStatus="Fail"; fi
        tarBall=$(./rename_build.sh $tarBall $tag)
        if [ ! -f "$tarBall" ]; then echo Missing $tarBall; flag="Fail"; fi
        echo $buildMachine $tarBall $flag >> $masterStatus
        builds[$count]="$tarBall"
        ((count++))
    done
done

# Copy the builds to byss
if [ "$overallStatus" = "Success" ]; then
    echo "" >> $masterStatus
    echo "Paths on byss" >> $masterStatus

    echo Wil copy builds to byss
    len="${#builds[@]}"
    echo len is $len
    for ((count = 0; count < len; count++)); do
        rsync -avz ${builds[$count]} $user@$byss:$byssPath 2>/dev/null
        rm -f "${builds[$count]}" # No need to keep this around
        build=${builds[$count]}
        build=${build/asp_tarballs\//}
        echo $byssPath/$build >> $masterStatus
    done
fi

subject="Build $tag status is $overallStatus"
mailx $mailto -s "$subject" < $masterStatus

# Wipe older builds
./rm_old.sh asp_tarballs 12
