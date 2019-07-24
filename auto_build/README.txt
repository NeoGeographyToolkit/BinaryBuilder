The Ames Stereo Pipeline automatic build/test/release framework
launches every day builds for all supported platforms, tests them, and
notifies the maintainers of the status. In case of success, it copies
the obtained builds to the release area and updates the link at:

https://byss.arc.nasa.gov/stereopipeline/daily_build

Machines:
lunokhod1:        Master machine on which the framework starts
ubuntu16:         Ubuntu 16, Linux, 64 bit
decoder:          Mac OS X 10.12
byss:             The machine storing the obtained builds

The host ubuntu16 is a virtual machine on lunokhod1.

ssh must be configured so that ssh connections from each machine to
lunokhod1 and back, and to itself (both using its name and using
'localhost') work without specifying a user name or password (user
names, ports, etc., can be specified in .ssh/config). For more details,
see the file StereoPipeline/VIRTMACHINES.

The main script is auto_build/launch_master.sh. It gets started on
lunokhod1. That script initiates the jobs on the other machines (and
itself).

Builds are done on ubuntu16 and decoder. The ubuntu16 build is 
tested on lunokhod1.

The test process on lunokhod1 is the strictest, it will fail if any
obtained results differ from the reference. The tests on other
machines use just a subset of the tests done on lunokhod1 (for various
reasons, including runtime, results being too different due to
architecture being different, etc.), and those tests are allowed to
deviate somewhat from the reference results for lunokhod1.

The obtained builds include the latest pdf documentation, generated on
lunokhod1 (as other machines lack LaTeX), and later copied to each
build. The builds are renamed according to the release convention, and
copied to byss at /byss/docroot/stereopipeline/daily_build (the
internal location of the public link from above).

Each time the automated builds are started, a fresh copy is fetched
not only of VisionWorkbench and StereoPipeline, but also of
BinaryBuilder and StereoPipelineTest. As such, all these repositories
must be up-to-date before the builds happen.

We assume that all machines have the needed supporting executables,
such as compilers, Python, git, etc. The complete list of needed
software is in StereoPipeline/INSTALLGUIDE. The paths to these tools
is set via:

 source auto_build/utils.sh

Additional setup information can be found on the internal IRG wiki:
https://babelfish.arc.nasa.gov/trac/irg/wiki/AspBuildSystem
