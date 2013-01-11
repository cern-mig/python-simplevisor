simplevisor-control command
===========================

NAME
----

simplevisor-control - run simplevisor as a service

SYNOPSIS
--------

**simplevisor-control** command [path]

DESCRIPTION
-----------

simplevisor-control command can be used to run simplevisor as a service.


OPTIONS
-------

**command**
one of: start, stop, restart, status, check

**path**
look at simplevisor man page for path behavior

EXAMPLES
--------

On linux you can look at the script shipped in the examples folder
which is called simplevisor-new-instance, it creates folders and
the configuration to run a simplevisor instance.

::

    mkdir -p /var/lib/myinstance/bin
    mkdir -p /var/lib/myinstance/data
    mkdir -p /var/lib/myinstance/etc

Create a file /var/lib/myinstance/bin/service with content
and make it executable::

    #!/bin/sh
    #
    # init script that can be symlinked from /etc/init.d
    #
    
    # chkconfig: - 90 15
    # description: my simplevisor instance
    
    . "/var/lib/myinstance/etc/simplevisor.profile"
    exec "/usr/bin/simplevisor-control" ${1+"$@"}

*/var/lib/myinstance/etc/simplevisor.profile* could look like::

    # main
    export SIMPLEVISOR_NAME=myinstance
    # if you want to run it as another user:
    #export SIMPLEVISOR_USER=games
    export SIMPLEVISOR_CONF=/var/lib/myinstance/etc/simplevisor.conf
    export SIMPLEVISOR_PIDFILE=/var/lib/myinstance/data/simplevisor.pid
    export SIMPLEVISOR_LOCKFILE=/var/lib/myinstance/data/simplevisor.lock

Create */var/lib/myinstance/etc/simplevisor.conf* according to simplevisor
documentation.

For Red Hat or Fedora you can symlink service script::

    ln -s /var/lib/myinstance/bin/service /etc/init.d/myinstance
	
And use it as a normal service::

    /sbin/service myinstance start|stop|status|restart|check

AUTHOR
------

Massimo Paladin <massimo.paladin@gmail.com> - Copyright (C) 2013 CERN

