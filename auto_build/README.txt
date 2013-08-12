The Ames Stereo Pipeline automatic build/test/release framework launches every day builds for all supported platforms, tests them, and, in case of success, copies the obtained builds to the release area and updates the link at:

https://byss.arc.nasa.gov/stereopipeline/daily_build

In any case, a success/failure notification is sent to the ASP developers.

The main script is launch_master.sh. It gets started on pfe25 (Pleiades SuSE Linux machine). That script calls launch_slave.sh on pfe25, amos (Mac OS X) and zula (Ubuntu Linux).

On pfe25 and on amos, builds are launched, and then tested on the same machine. The process on zula launches builds on zula, centos-64-5 (older 64 bit Linux distribution) and on centos-32-5 (older 32 bit Linux distribution). 

The builds done on zula and centos-64-5 are tested on zula. The build launched on centos-32-5 is tested on that machine, as zula is missing some libraries expected by that build.

The test process on pfe25 is the strictest, it will fail if any obtained resuls differ from the reference. The tests on other machines use just a subset of the tests done on pfe25 (for various reasons, including runtime, results being too different due to architecture being different, etc.), and those tests are allowed to deviate somewhat from the reference results for pfe25.

The obtained builds include the latest pdf documentation, generated on zula. The builds are renamed according to the release convention, and copied to /byss/docroot/stereopipeline/daily_build (the internal location of the public link from above).

Each time the automated builds are started, they get a fresh copy not only of VisionWorkbench and StereoPipeline, but also of BinaryBuilder and StereoPipelineTest. As such, all these repositories must be up-to-date before builds happen.

We assume that that any machine which needs to talk to another machine is properly set up using ssh without password. Particularly, if the IP address or port of zula changes, that information must be updated in .ssh/config. 

We also assume that all machines have the needed supporting executables installed in the right places, such as compilers, Python, git, tar, bzip2, etc. 

