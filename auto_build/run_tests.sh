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
userName=$6

# Set system paths and load utilities
source $HOME/$buildDir/auto_build/utils.sh

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
machine=$(machine_name)
configFile=$(release_conf_file $machine)

if [ ! -e $configFile ]; then
    echo "Error: File $configFile does not exist"
    ssh $masterMachine "echo '$tarBall test_done $status' > $buildDir/$statusFile"\
        2>/dev/null
    exit 1
fi
perl -pi -e "s#(export ASP=).*?\n#\$1$binDir\n#g" $configFile

# Run the tests. Let the verbose output go to a file.
#outputFile=output_test_"$machine".txt
echo "Launching the tests. Output goes to: $(pwd)/$reportFile"
num_cpus=$(ncpus)
if [ "$num_cpus" -gt 4 ]; then num_cpus=4; fi # Don't overload machines
#bin/run_tests.pl $configFile > $outputFile 2>&1
py.test -n $num_cpus -q -s -r a --tb=no --config $configFile > $reportFile

# Tests are finished running, make sure all maintainers can access the files.
chown -R  :ar-gg-ti-asp-maintain $HOME/$testDir
chmod -R g+rw $HOME/$testDir

if [ "$?" -ne 0 ]; then
    echo "Last command failed, sending status and early quit."
    ssh $userName@$masterMachine "echo '$tarBall test_done $status' > $buildDir/$statusFile"\
        2>/dev/null
    exit 1
fi
if [ ! -f "$reportFile" ]; then
    echo "Error: Final report file does not exist"
    ssh $userName@$masterMachine "echo '$tarBall test_done $status' > $buildDir/$statusFile"\
        2>/dev/null
    exit 1
fi

# Wipe old builds on the test machine
echo "Wiping old builds..."
numKeep=8
if [ "$(echo $machine | grep $masterMachine)" != "" ]; then
    numKeep=24 # keep more builds on master machine
fi
$HOME/$buildDir/auto_build/rm_old.sh $HOME/$buildDir/asp_tarballs $numKeep

# Append the result of tests to the logfile
cat $reportFile

# Display the allowed error (actual error with extra tolerance) for each run
bin/print_allowed_error.pl $reportFile

# Mark tests as done
echo "Reporting test results..."
failures=$(grep -i fail $reportFile)
if [ "$failures" = "" ]; then
    status="Success"
fi
ssh $userName@$masterMachine "echo '$tarBall test_done $status' > $buildDir/$statusFile"\
    2>/dev/null
echo "Finished running tests locally!"
