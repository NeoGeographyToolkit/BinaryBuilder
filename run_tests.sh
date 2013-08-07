#!/bin/bash

if [ "$#" -lt 4 ]; then echo Usage: $0 tarBall testDir buildDir statusFile; exit; fi

tarBall=$1
testDir=$2
buildDir=$3
statusFile=$4

status="Fail"

# Unpack the tarball
if [ ! -e "$HOME/$buildDir/$tarball" ]; then
    echo File: $HOME/$buildDir/$tarball does not exist
    echo $tarBall test_done $status > $HOME/$buildDir/$statusFile
    exit 1
fi
tarBallDir=$(dirname $HOME/$buildDir/$tarBall)
cd $tarBallDir
bzip2 -dc $HOME/$buildDir/$tarBall | tar xfv -
binDir=$HOME/$buildDir/$tarBall
binDir=${binDir/.tar.bz2/}
if [ ! -e "$binDir" ]; then
    echo Directory: $binDir does not exist
    echo $tarBall test_done $status > $HOME/$buildDir/$statusFile
    exit 1
fi

# Set up the config file and run
cd $HOME
if [ ! -d "$testDir" ];  then echo "Directory: $testDir does not exist"
    echo $tarBall test_done $status > $HOME/$buildDir/$statusFile
    exit 1
fi
cd $testDir
machine=$(uname -n)
configFile="release_"$machine".conf"
configFileLocal="release_"$machine"_local.conf"
if [ ! -e $configFile ]; then
    echo File $configFile does not exist
    echo $tarBall test_done $status > $HOME/$buildDir/$statusFile
    exit 1
fi
cp -fv $configFile $configFileLocal
perl -pi -e "s#(export ASP=).*?\n#\$1$binDir\n#g" $configFileLocal
rm -f report.txt
bin/run_tests.pl $configFileLocal
if [ "$?" -ne 0 ]; then
    echo $tarBall test_done $status > $HOME/$buildDir/$statusFile
    exit 1
fi
if [ ! -f report.txt ]; then
    echo Final report file does not exist
    echo $tarBall test_done $status > $HOME/$buildDir/$statusFile
    exit 1
fi

# Mark run as done
failures=$(grep -i fail report.txt)
if [ "$failures" = "" ]; then
    status="Success"
fi

echo $tarBall test_done $status > $HOME/$buildDir/$statusFile

# Ensure the directory is wiped when done
rm -rf $binDir
