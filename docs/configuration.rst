Configuration
=============

Simplevisor has one main configuration file. The format of the configuration
file is a simplified Apache Style Config file.
Following features are supported:

- Apache Style Config syntax
- comments are allowed with lines starting with #
- blank lines are ignored
- file inclusion with <<include relative_file_path.conf>>

If a certain value is set for a specific feature in both the configuration
file and the command line then the command line has the priority.

You can find a configuration example in the examples directory called::

    simplevisor.conf.example

copy and edit the file::

	# The format of the configuration
	# file is a simplified Apache Style Config file.
	# Following features are supported:
	# 
	# - Apache Style Config syntax
	# - comments are allowed with lines starting with #
	# - blank lines are ignored
	# - file inclusion with <<include relative_file_path.conf>>
	
	<simplevisor>
	    # File used to store the status
	    store = /var/cache/simplevisor/simplevisor.json
	    
	    # pid file
	    # ignored if simplevisor-control is used
	    #pidfile = /path/to/pid
	    
	    # interval between supervision cycles in seconds
	    #interval = 120
		
	    # Configure the logging system.
	    # 3 are available: print,syslog,simple
	    log = syslog
	
	    # If logging system is simple you need to specify a log file,
	    # check that the logfile is writable by the specified user.
	    #logfile = /var/log/simplevisor/simplevisor.log
		
	    # If logging system is either print or simple you can
	    # specify a loglevel, it is warning by default:
	    # available log levels: debug,info,warning,error,critical
	    #loglevel = info
	</simplevisor>
	
	<<include simplevisor.services.example>>


where *simplevisor.services.example* could look like::

	<entry>
	    type = supervisor
	    name = svisor1
	    max_restarts = 10
	    max_time = 60
	    strategy = one_for_one
	    stop_all = false
	    <children>
		    <entry>
		        type = service
		        name = httpd
		        expected = stopped
		        control = /sbin/service httpd
		    </entry>
	        <<include other_service.conf>>
	    </children>
	</entry>


and *other_service.conf* could look like::

    <entry>
        type = service
        name = custom1
        start = /path/to/script --conf /path/to/conf --daemon
        # If you cannot provide a status or stop command you can specify a
        # pattern which will be used to look for the process in the process
        # table, however this is supported only on linux.
        # If not specified start command is used as pattern.
        pattern = /path/to/script --conf /path/to/conf --daemon
    </entry>


