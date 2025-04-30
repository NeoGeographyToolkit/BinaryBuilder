Nightly regressions
===================

The Ames Stereo Pipeline automatic build/test/release framework launches every
day builds for all supported platforms, tests them, and notifies the maintainers
of the status. In case of success, it publishes the obtained builds to GitHub,
at:

    https://github.com/NeoGeographyToolkit/StereoPipeline/releases

Machines:
--------

lunokhod1:            Ubuntu 18 Linux
GitHub cloud machine: Mac OS X with Intel CPU
GitHub cloud machine: Mac OS X with Arm CPU

ssh on local machines must be configured so that it works without user name or
password. For the moment, just one local machine exists.

The main script is auto_build/launch_master.sh in BinaryBuilder. It gets started
on lunokhod1.

The Linux build is done on lunokhod1. The OSX builds are created and tested on
GitHub via Actions. Then they are downloaded and integrated into the release.

Each time the automated builds are started, a fresh copy is fetched not only of
VisionWorkbench and StereoPipeline, but also of StereoPipelineTest. As such, all
these repositories must be up-to-date before the builds happen. 

A local copy of BinaryBuilder is used on lunokhod1, and the GitHub copy is used
in the cloud. These are better kept in sync.

The build process for ASP and dependencies is described in::

https://stereopipeline.readthedocs.io/en/latest/building_asp.html

Some env variables are set in::

  auto_build/utils.sh
