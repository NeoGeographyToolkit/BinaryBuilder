#!/bin/bash

# Launch the tests. We must not exit this script without updating the status file
# at $HOME/$buildDir/$statusFile, otherwise the caller will wait forever.

if [ "$#" -lt 5 ]; then echo Usage: $0 launchMachine tarBall testDir buildDir statusFile; exit 1; fi

launchMachine=$1
tarBall=$2
testDir=$3
buildDir=$4
statusFile=$5

. $HOME/$buildDir/auto_build/utils.sh # load utilities
set_system_paths

# If we are on zula, but we'd like to run tests for centos-32-5,
# connect to that machine and call this script there. The centos-32-5
# build does not run on zula, while the one from centos-64-5 has no
# such problem.
if [ "$(uname -n)" != "$launchMachine" ] && [ "$launchMachine" = "centos-32-5" ]; then
    user=build
    outputFile=$(output_file $buildDir $launchMachine)
    echo Will connect to $user@$launchMachine
    cd $HOME/$buildDir

    # Make sure all scripts are up-to-date on the machine above to run things on
    ./auto_build/push_code.sh $user $launchMachine $buildDir 2>/dev/null

    ssh $user@$launchMachine "echo $tarBall now_testing > $buildDir/$statusFile 2>/dev/null" 2>/dev/null
    sleep 5; # Give the filesystem enough time to react
    ssh $user@$launchMachine "nohup nice -19 $buildDir/auto_build/run_tests.sh $* > $outputFile 2>&1&" 2>/dev/null

    # Wait for the tests to finish
    while [ 1 ]; do
        statusLine=$(ssh $user@$launchMachine \
            "cat $buildDir/$statusFile 2>/dev/null" 2>/dev/null)
        tarBall=$( echo $statusLine | awk '{print $1}' )
        state=$( echo $statusLine | awk '{print $2}' )
        status=$( echo $statusLine | awk '{print $3}' )
        echo $(date) Status for $launchMachine is $tarBall $state $status
        if [ "$state" = "test_done" ]; then
            break;
        fi
        echo Status is $statusLine
        sleep 30
    done

    echo $statusLine > $HOME/$buildDir/$statusFile
    ssh $user@$launchMachine "cat $outputFile" 2>/dev/null # append to curr logfile
    exit
fi

status="Fail"
reportFile="report.txt"
rm -f $HOME/$testDir/$reportFile

# if [ "$(uname -n)" = "centos-32-5" ]; then
#     cd $HOME/$buildDir
#     base=$(ls -trd BaseSysem*bz2 | grep -i -v debug | tail -n 1)
#     if [ "$base" = "" ]; then
#         echo "Error: Missing BaseSystem"
#         echo "$tarBall test_done $status" > $HOME/$buildDir/$statusFile
#         exit 1
#     fi
#     ./deploy-base.py $base $HOME/projects/base_system
# fi

# Unpack the tarball
if [ ! -e "$HOME/$buildDir/$tarBall" ]; then
    echo "Error: File: $HOME/$buildDir/$tarBall does not exist"
    echo "$tarBall test_done $status" > $HOME/$buildDir/$statusFile
    exit 1
fi
tarBallDir=$(dirname $HOME/$buildDir/$tarBall)
cd $tarBallDir
tar xjfv $HOME/$buildDir/$tarBall
binDir=$HOME/$buildDir/$tarBall
binDir=${binDir/.tar.bz2/}
if [ ! -e "$binDir" ]; then
    echo "Error: Directory: $binDir does not exist"
    echo "$tarBall test_done $status" > $HOME/$buildDir/$statusFile
    exit 1
fi

cd $HOME
if [ ! -d "$testDir" ];  then
    echo "Error: Directory: $testDir does not exist"
    echo "$tarBall test_done $status" > $HOME/$buildDir/$statusFile
    exit 1
fi
cd $testDir

# Ensure we have an up-to-date version of the test suite
# To do: Cloning can be sped up by local caching.
newDir=StereoPipelineTest_new
failure=1
for ((i = 0; i < 600; i++)); do
    # Bugfix: Sometimes the github server is down, so do multiple attempts.
    echo "Cloning StereoPipelineTest in attempt $i"
    rm -rf $newDir
    git clone https://github.com/NeoGeographyToolkit/StereoPipelineTest.git $newDir
    failure="$?"
    if [ "$failure" -eq 0 ]; then break; fi
    sleep 60
done
if [ "$failure" -ne 0 ]; then
    echo "$tarBall test_done $status" > $HOME/$buildDir/$statusFile
    exit 1
fi
cp -rf $newDir/.git* .; cp -rf $newDir/* .; rm -rf $newDir

# Set up the config file and run
machine=$(uname -n)
configFile="release_"$machine".conf"
configFileLocal="release_"$machine"_local.conf"
if [ ! -e $configFile ]; then
    echo "Error: File $configFile does not exist"
    echo "$tarBall test_done $status" > $HOME/$buildDir/$statusFile
    exit 1
fi
cp -fv $configFile $configFileLocal
perl -pi -e "s#(export ASP=).*?\n#\$1$binDir\n#g" $configFileLocal

bin/run_tests.pl $configFileLocal
if [ "$?" -ne 0 ]; then
    echo "$tarBall test_done $status" > $HOME/$buildDir/$statusFile
    exit 1
fi
if [ ! -f $reportFile ]; then
    echo "Error: Final report file does not exist"
    echo "$tarBall test_done $status" > $HOME/$buildDir/$statusFile
    exit 1
fi

# Mark run as done
failures=$(grep -i fail $reportFile)
if [ "$failures" = "" ]; then
    status="Success"
fi

echo "$tarBall test_done $status" > $HOME/$buildDir/$statusFile
