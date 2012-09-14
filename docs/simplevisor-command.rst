simplevisor command
===================

simplevisor 0.4 - simple daemons supervisor

SYNOPSIS
--------

**simplevisor**
[--conf CONF] [--daemon] [-h] [--interval INTERVAL] [--log LOG] [--logfile LOGFILE] [--loglevel LOGLEVEL] [-p PIDFILE] [--store STORE] [--version] 
command [path] 

DESCRIPTION
-----------

Simplevisor is a simple daemons supervisor, it is inspired
by Erlang OTP and it can supervise hierarchies of services.

COMMANDS

If a path is given or only one service entry is given:

for given command X
    run the service X command where service is the only entry provided
    or the entry identified by its path

If path is not given and root entry is a supervisor:

start
    start the simplevisor process which start the supervision.
    It can be used with --daemon if you want it as daemon

stop
    stop the simplevisor process and all its children, if running
    
status
    return the status of the simplevisor process
    
check
    return the comparison between the expected state and the actual state.
    0 -> everything is fine
    1 -> warning, not expected
    
restart
    stop + start the simplevisor process
    
single
    execute one cycle of supervision and exit.
    Useful to be run in a cron script
    
stop_supervisor
    stop only the simplevisor process and the supervision
    
stop_children
    stop only the children
    
configuration_check
    just check the configuration
    
pod
    generate pod format help to be used by pod2man to generate man page
    
pod
    generate rst format help to be used in the web doc
    
help
    same as -h/--help, print help page




OPTIONS
-------

**positional arguments:**

**command**
	check, configuration_check, help, pod, restart, rst, single, start, status, stop, stop_children, stop_supervisor

**path**
	path to a service, subset of commands available: start, stop, status, check, restart

**optional arguments:**

**--conf CONF**
	configuration file

**--daemon**
	daemonize, ONLY with start

**-h, --help**
	print the help page

**--interval INTERVAL**
	interval to wait between supervision cycles

**--log LOG**
	available: null, print, syslog, simple

**--logfile LOGFILE**
	log file, ONLY for simple

**--loglevel LOGLEVEL**
	log level, ONLY for simple and print

**-p, --pidfile PIDFILE**
	the pidfile

**--store STORE**
	file where to store the state

**--version**
	print the program version

EXAMPLES
--------

Create and edit the main configuration file::
    
    ## look for simplevisor.conf.example in the examples.

Run it::

    simplevisor --conf /path/to/simplevisor.conf start

to run it in daemon mode::

    simplevisor --conf /path/to/simplevisor.conf --daemon start

For other commands::

    simplevisor --help

Given the example configuration, to start the httpd service::

    simplevisor --conf /path/to/simplevisor.conf start svisor1/httpd


AUTHOR
------

Massimo Paladin <massimo.paladin@gmail.com> - Copyright (C) 2012 CERN


