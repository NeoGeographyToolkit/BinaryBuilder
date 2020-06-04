#!/usr/bin/env python

from __future__ import print_function

import sys
code = -1
# Must have this check before importing other BB modules
if sys.version_info < (2, 6, 1):
    print('\nERROR: Must use Python 2.6.1 or greater.')
    sys.exit(code)

import time
import os.path as P
import os
import re
import logging
import string
from optparse import OptionParser
from BinaryBuilder import get_platform, die, Apps, \
     write_vw_config, write_asp_config
from BinaryDist import fix_install_paths, run
from Packages import geoid
from glob import glob

global logger
logger = logging.getLogger()

def usage(msg, code):
    parser.print_help()
    print('\n%s' % msg)
    sys.exit(code)

if __name__ == '__main__':

    parser = OptionParser(usage='%s tarball installdir' % sys.argv[0])
    parser.add_option('--debug',       dest='loglevel',  default=logging.INFO, action='store_const', const=logging.DEBUG, help='Turn on debug messages')
    parser.add_option("--skip-extracting-tarball",
                      action="store_true", dest="skip_extraction", default=False,
                      help="Skip the time-consuming tarball extraction (for debugging purposes)")

    global opt
    (opt, args) = parser.parse_args()

    if not len(args) == 2:
        usage('Missing required argument: installdir', code)
    tarball    = P.realpath(args[0])
    installdir = P.realpath(args[1])
    if not P.exists(tarball):
        usage('Invalid tarball %s (does not exist)' % tarball, code)
    if not (P.exists(installdir)):
        os.makedirs(installdir)
    if not (P.isdir(installdir)):
        usage('Invalid installdir %s (not a directory)' % installdir, code)
    logging.basicConfig(level=opt.loglevel)

    if not opt.skip_extraction:
        print('Extracting tarball')
        run('tar', 'xf', tarball, '-C', installdir, '--strip-components', '1')

    arch = get_platform()
    fix_install_paths(installdir, arch)

    # Replace /home/user with $HOME, looks nicer in the output
    vardir = installdir
    r = re.compile('^' + os.environ["HOME"] + '(.*?)$')
    m = r.search(vardir)
    if m:
        vardir = '$HOME' + m.group(1)
        
    prefix       = '$PWD/build'
    config_file  = P.join(installdir, 'config.options.vw')
    write_vw_config(prefix, vardir, arch, config_file)

    use_env_flags = False
    prefix       = '$PWD/build'
    vw_build     = '$HOME/projects/visionworkbench/build'
    if 'VisionWorkbench' not in tarball:
        config_file  = P.join(installdir, 'config.options.asp')
        write_asp_config(use_env_flags,
                         prefix, vardir, vw_build, arch, geoid, config_file)

