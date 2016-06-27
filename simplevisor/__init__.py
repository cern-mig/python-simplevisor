"""
Simplevisor is a simple daemons supervisor, it is inspired by
`Erlang OTP <http://www.erlang.org/doc/design_principles/sup_princ.html>`_
and it can supervise hierarchies of services.

Dependencies::

    argparse for python < 3.2
    simplejson for python < 2.6

Install it::

    easy_install simplevisor
    # look at the installation page for details

create and edit the main configuration file::

    simplevisor.conf.example available in the examples
    # check the configuration page for details

run it with::

    simplevisor --conf /path/to/simplevisor.conf start
    # or as a daemon
    simplevisor --conf /path/to/simplevisor.conf --daemon start

check the help page::

    simplevisor help

if you want to run it as a service user simplevisor-control as init script.


Author: Massimo.Paladin@gmail.com

Copyright (C) CERN 2013-2016
"""

import sys
import simplevisor.mtb as mtb

AUTHOR = "Massimo Paladin <massimo.paladin@gmail.com>"
COPYRIGHT = "Copyright (C) CERN 2013-2016"
VERSION = "1.2"
DATE = "27 June 2016"
__author__ = AUTHOR
__version__ = VERSION
__date__ = DATE

if "mtb" not in sys.modules:
    sys.modules["mtb"] = mtb
