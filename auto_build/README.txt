The Ames Stereo Pipeline automatic build/test/release framework
launches every day builds for all supported platforms, tests them, and
notifies the maintainers of the status. In case of success, it copies
the obtained builds to the release area and updates the link at:

https://byss.arc.nasa.gov/stereopipeline/daily_build

Machines:
lunokhod1:    Master machine on which the framework starts
ubuntu-64-13: Newer Linux, 64 bit 
centos-64-5:  Older Linux, 64 bit
centos-32-5:  Older Linux, 32 bit
amos:         Mac OS X 10.6
andey:        Mac OS X 10.8
byss:         The machine storing the obtained builds

The hosts ubuntu-64-13, centos-64-5, and centos-32-5 are virtual
machines on lunokhod1.

ssh must be configured so that ssh connections from each machine to
lunokhod1 and back, and to itself (both using its name and using
'localhost') work without specifying a user name or password (user
names, ports, etc., can be specified in .ssh/config).

The main script is auto_build/launch_master.sh. It gets started on
lunokhod1. That script initiates the jobs on the other machines (and
itself).

Builds are done on the following machines: ubuntu-64-13, centos-64-5,
centos-32-5, and amos. Each build is being tested on the same
machine. In addition, the centos-64-5 build is also tested on
lunokhod1, while the amos build is also tested on andey.

The test process on lunokhod1 is the strictest, it will fail if any
obtained results differ from the reference. The tests on other
machines use just a subset of the tests done on lunokhod1 (for various
reasons, including runtime, results being too different due to
architecture being different, etc.), and those tests are allowed to
deviate somewhat from the reference results for lunokhod1.

The obtained builds include the latest pdf documentation, generated on
ubuntu-64-13 (as other machines lack LaTeX). The builds are renamed
according to the release convention, and copied to byss at
/byss/docroot/stereopipeline/daily_build (the internal location of the
public link from above).

Each time the automated builds are started, a fresh copy is fetched
not only of VisionWorkbench and StereoPipeline, but also of
BinaryBuilder and StereoPipelineTest. As such, all these repositories
must be up-to-date before the builds happen.

We assume that all machines have the needed supporting executables,
such as compilers, Python, git, etc. The complete list of needed
software is in StereoPipeline/INSTALLGUIDE.

