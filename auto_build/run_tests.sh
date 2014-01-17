#!/bin/bash

# Launch the tests. We must not exit this script without updating the status file
# at $HOME/$buildDir/$statusFile, otherwise the caller will wait forever.

if [ "$#" -lt 5 ]; then
    echo Usage: $0 buildDir tarBall testDir statusFile masterMachine
    exit 1
fi

buildDir=$1
tarBall=$2
testDir=$3
statusFile=$4
masterMachine=$5

. $HOME/$buildDir/auto_build/utils.sh # load utilities
set_system_paths

status="Fail"

# Unpack the tarball
if [ ! -e "$HOME/$buildDir/$tarBall" ]; then
    echo "Error: File: $HOME/$buildDir/$tarBall does not exist"
    ssh $masterMachine "echo '$tarBall test_done $status' > $buildDir/$statusFile"\
        2>/dev/null
    exit 1
fi
tarBallDir=$(dirname $HOME/$buildDir/$tarBall)
cd $tarBallDir
echo "Unpacking $HOME/$buildDir/$tarBall"
tar xjfv $HOME/$buildDir/$tarBall
binDir=$HOME/$buildDir/$tarBall
binDir=${binDir/.tar.bz2/}
if [ ! -e "$binDir" ]; then
    echo "Error: Directory: $binDir does not exist"
    ssh $masterMachine "echo '$tarBall test_done $status' > $buildDir/$statusFile"\
        2>/dev/null
    exit 1
fi

cd $HOME
mkdir -p $testDir
cd $testDir
reportFile="report.txt"
rm -f $reportFile

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
    ssh $masterMachine "echo '$tarBall test_done $status' > $buildDir/$statusFile"\
        2>/dev/null
    exit 1
fi
cp -rf $newDir/.git* .; cp -rf $newDir/* .; rm -rf $newDir

# Set up the config file
machine=$(uname -n | perl -pi -e "s#\..*?\$##g")
configFile="release_"$machine".conf"
if [ ! -e $configFile ]; then
    echo "Error: File $configFile does not exist"
    ssh $masterMachine "echo '$tarBall test_done $status' > $buildDir/$statusFile"\
        2>/dev/null
    exit 1
fi
perl -pi -e "s#(export ASP=).*?\n#\$1$binDir\n#g" $configFile

# Run the tests. Let the verbose output go to a file.
outputFile=output_test_"$machine".txt
echo "Launching the tests. Output goes to: $(pwd)/$outputFile"
bin/run_tests.pl $configFile > $outputFile 2>&1

if [ "$?" -ne 0 ]; then
    ssh $masterMachine "echo '$tarBall test_done $status' > $buildDir/$statusFile"\
        2>/dev/null
    exit 1
fi
if [ ! -f "$reportFile" ]; then
    echo "Error: Final report file does not exist"
    ssh $masterMachine "echo '$tarBall test_done $status' > $buildDir/$statusFile"\
        2>/dev/null
    exit 1
fi

# Append the result of tests to the logfile
cat $reportFile

# Display the allowed error (actual error with extra tolerance) for each run
bin/print_allowed_error.pl $reportFile

# Mark tests as done
failures=$(grep -i fail $reportFile)
if [ "$failures" = "" ]; then
    status="Success"
fi
ssh $masterMachine "echo '$tarBall test_done $status' > $buildDir/$statusFile"\
    2>/dev/null

