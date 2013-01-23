Configuration
=============

Simplevisor has one main configuration file. The format of the configuration
file is the Apache Style Config, the configuration parsing is handled
with Perl Config::General module for commodity.

These are the main features supported in the configuration file:

format
    Apache Style Config syntax
comments
    comments are allowed through lines starting with *#*
blank lines
    blank lines are ignored
file inclusion
    file inclusion is supported to allow modularization of the configuration
    file. It is possible to include a file which is in the same folder or in
    its subtree with the following directive:
    <<include relative_file_path.conf>>
variable interpolation
    variable interpolation is supported in order to reduce verbosity and
    duplication in the main blocks of the configuration file.
    
    *simplevisor* and *entry* sections allow variables declaration,
    variables are declared like any other fields with the only restriction
    that their name is prefixed with *var_*::
    
        ...
        var_foo = bar
        ...
    
    You can use variables in the value of a field, you can not use them
    inside keys and their scope is the subtree of declaration.
    They can be used surrounded by curly braces and prefixed by a dollar:
    *${var_name}*.
    
    An usage example::
    
        ...
        var_foo = bar
        property_x = ${var_foo} the rest of the value
        ...
    
    

The options specified through the command line have the priority over
the options declared in the configuration file.

You can find a configuration example in the *examples* folder, it is called::

    simplevisor.conf.example

copy and edit the file::

    # Simplevisor has one main configuration file. The format of the configuration
    # file is the Apache Style Config, the configuration parsing is handled
    # with Perl Config::General module for commodity.
    #
    # Following features are supported:
    # 
    # - Apache Style Config syntax
    # - comments are allowed through lines starting with #
    # - blank lines are ignored
    # - file inclusion is supported to allow modularization of the
    #   configuration file. It is possible to include a file which is in the same
    #   folder or in its subtree with the following directive:
    #   <<include relative_file_path.conf>>
    # - variable interpolation is supported in order to reduce verbosity and
    #   duplication in the main blocks of the configuration file.
    #   simplevisor and entry sections allow variables declaration, variables
    #   are declared like any other fields with the only restriction that their
    #   name is prefixed with var_:
    #       ...
    #       var_foo = bar
    #       property_x = ${var_foo} the rest of the value
    #       ...
    #   You can use variables in the value of a field, you can not use them inside
    #   keys and their scope is the subtree of declaration.
    
    <simplevisor>
        # file used to store the status
        store = /var/cache/simplevisor/simplevisor.json
        
        # pid file, ignored if simplevisor-control is used
        #pidfile = /path/to/pid
        
        # interval between supervision cycles, in seconds
        #interval = 120
        
        # configure the logging system, must be one of: stdout,syslog,file
        log = stdout
    
        # if logging system is file you need to specify a log file,
        # check that the logfile is writable by the specified user.
        #logfile = /var/log/simplevisor/simplevisor.log
        
        # the loglevel is warning by default,
        # the available log levels are: debug,info,warning,error,critical
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


