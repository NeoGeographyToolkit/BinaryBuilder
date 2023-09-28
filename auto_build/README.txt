Nightly regressions
===================

The Ames Stereo Pipeline automatic build/test/release framework
launches every day builds for all supported platforms, tests them, and
notifies the maintainers of the status. In case of success, it
publishes the obtained builds to GitHub, at:

    https://github.com/NeoGeographyToolkit/StereoPipeline/releases

Machines:
--------

lunokhod1:        Ubuntu 18 Linux
decoder:          Mac OS X

ssh must be configured so that ssh connections from each machine to
lunokhod1 and back, and to itself (both using its name and using
'localhost') work without specifying a user name or password (user
names, ports, etc., can be specified in .ssh/config). 

The main script is auto_build/launch_master.sh in BinaryBuilder. It gets started
on lunokhod1.

The Linux build is done on lunokhod1. The OSX build is created and tested on
GitHub via Actions. It is then further tested on decoder, but this machine will
soon be decommissioned, and then the cloud solution will be the only one left.

The obtained builds include the latest pdf documentation, generated on
lunokhod1 (as other machines lack LaTeX), and later copied to each
build. The builds are renamed according to the release convention
before being published.

Each time the automated builds are started, a fresh copy is fetched
not only of VisionWorkbench and StereoPipeline, but also of
BinaryBuilder and StereoPipelineTest. As such, all these repositories
must be up-to-date before the builds happen.

We assume that all machines have the needed supporting executables,
such as compilers, Python, git, etc. The complete list of needed
software is in StereoPipeline/INSTALLGUIDE. Recently most of them
are installed via conda. The paths to these tools
is set via:

 source auto_build/utils.sh
