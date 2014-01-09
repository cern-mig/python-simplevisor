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

Copyright (C) 2013-2014 CERN
"""

AUTHOR = "Massimo Paladin <massimo.paladin@gmail.com>"
COPYRIGHT = "Copyright (C) 2013-2014 CERN"
VERSION = "0.8"
DATE = "26 Apr 2013"
__author__ = AUTHOR
__version__ = VERSION
__date__ = DATE

import sys
import simplevisor.mtb as mtb

if "mtb" not in sys.modules:
    sys.modules["mtb"] = mtb
