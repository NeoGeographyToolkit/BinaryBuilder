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

# Set system paths and load utilities
source $HOME/$buildDir/auto_build/utils.sh

status="Fail"

# Init the status file
echo "$tarBall now_testing" > $HOME/$buildDir/$statusFile

# Unpack the tarball
if [ ! -e "$HOME/$buildDir/$tarBall" ]; then
    echo "Error: File: $HOME/$buildDir/$tarBall does not exist"
    echo "$tarBall test_done $status" > $HOME/$buildDir/$statusFile
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
    echo "$tarBall test_done $status" > $HOME/$buildDir/$statusFile
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
    echo "$tarBall test_done $status" > $HOME/$buildDir/$statusFile
    exit 1
fi

cp -rf $newDir/* .; rm -rf $newDir

# Set up the config file
machine=$(machine_name)
configFile=$(release_conf_file $machine)

if [ ! -e $configFile ]; then
    echo "Error: File $configFile does not exist"
    echo "$tarBall test_done $status" > $HOME/$buildDir/$statusFile
    exit 1
fi
perl -pi -e "s#(export ASP=).*?\n#\$1$binDir\n#g" $configFile

# Run the tests. Let the verbose output go to a file.
#outputFile=output_test_"$machine".txt
echo "Launching the tests. Output goes to: $(pwd)/$reportFile"
num_cpus=$(ncpus)
#if [ "$num_cpus" -gt 8 ]; then num_cpus=8; fi # Don't overload machines

# This is a bugfix for a known issue with pytest.
export LANG=en_US.UTF-8

echo The environment
env

# Run the tests with timeout. See StereoPipelineTest/README.txt for usage.
cmd="/usr/bin/time $HOME/miniconda3/envs/pytest/bin/python $HOME/miniconda3/envs/pytest/bin/pytest --timeout=14400 -n $num_cpus -q -s -r a --tb=no --config $configFile"
echo Running: $cmd
echo Current directory: $(pwd)
$cmd > $reportFile 2>&1
test_status="$?"

if [ "$test_status" -ne 0 ]; then
    echo "pytest command failed. See StereoPipelineTest/README.txt for how to install and use pytest."
    echo "$tarBall test_done $status" > $HOME/$buildDir/$statusFile
    exit 1
fi

# Turn this off. Some groups no longer exists on all machines.
# To be revisited when more developers maintain this.
# # Tests are finished running, make sure all maintainers can access the files.
# chown -R :ar-gg-ti-asp-maintain $HOME/$testDir
# chmod -R g+rw $HOME/$testDir
# chown -R  :ar-gg-ti-asp-maintain $HOME/$buildDir
# chmod -R g+rw $HOME/$buildDir
# # Trying these again, for some reason the above does not work, but
# # this apparently does.  I think it is because $HOME/$testDir is a
# # symlink and now we are modifying the internals of the actual dir.
# for d in . *; do 
#     chown -R :ar-gg-ti-asp-maintain $d
#     chmod -R g+rw $d
# done

if [ ! -f "$reportFile" ]; then
    echo "Error: Final report file does not exist."
    echo "$tarBall test_done $status" > $HOME/$buildDir/$statusFile
    exit 1
fi

# Append the result of tests to the logfile
echo "###### Contents of the report file ######"
cat $reportFile
echo "###### End of the report file ######"

# Wipe old builds on the test machine
echo "Wiping old builds..."
numKeep=8
if [ "$(echo $machine | grep $masterMachine)" != "" ]; then
    numKeep=24 # keep more builds on master machine
fi
$HOME/$buildDir/auto_build/rm_old.sh $HOME/$buildDir/asp_tarballs $numKeep

# Display the allowed error (actual error with extra tolerance) for each run
bin/print_allowed_error.pl $reportFile

# Mark tests as done
echo "Reporting test results..."
failures=$(grep -i fail $reportFile)
if [ "$failures" = "" ]; then
        status="Success"
fi
echo "$tarBall test_done $status" > $HOME/$buildDir/$statusFile
echo "Finished running tests locally!"


