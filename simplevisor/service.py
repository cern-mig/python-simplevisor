"""
This class implements a :py:class:`Service` abstraction.
As service we mean a process which run in daemon mode.

An example of service declaration::

    <entry>
        type = service
        name = httpd
        expected = stopped
        control = /sbin/service httpd
    </entry>

another example for a standalone script::

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

Parameters
----------

*control*
    the control of the command to run. If specified it will be the prefix
    of *start/stop/status* commands.

*expected*
    expected state of the service.
    Valid values are *running* and *stopped*.
  
*name*
    unique name of the *worker/service*.

*path*
    the path for executing the commands.
    Multiple values should be separated by colons.
  
*pattern*
    used to look for the service in the process table for stop and status
    commands if they are not specified and control is also not specified.

*restart*
    specify a custom restart command.
    If <control> is specified:
    
        - if <restart> is not specified "<control> restart" is executed
        - if <restart> = "stop+start" a "<control> stop" followed by a
          "<control> start" is executed
        - else "<restart>" is executed
        
    If <control> is not specified:
    
        - if <restart> is not specified a "<control> stop" followed by a
          "<control> start" is executed
        - else "<restart>" is executed
  
*start*
    specify a custom start command.
    If <control> is specified:
    
        - if <start> is not specified "<control> start" is executed
        - else "<start>" is executed
        
    If <control> is not specified:
    
        - "<start>" is executed
  
*status*
    specify a custom status command.
    If <control> is specified:
    
        - "<control> status" is executed
        
    If <control> is not specified:
    
        - if <status> is specified "<status>" is executed
        - else it will look for it in the process table either looking
          for the start command or the provided pattern.
    
    Status commands are expected to exit with return code according to    
    the following following:
    
    - *0:* the service is running fine
    - *3:* the service is stopped
    - *other:* return code is interpreted as dirty/zombie/hang state
  
*stop*
    specify a custom stop command.
    If <control> is specified:
    
        - "<control> stop" is executed
        
    If <control> is not specified:
    
        - if <stop> is specified "<stop>" is executed
        - else it will look for it in the process table either looking
          for the start command or the provided pattern and then kill it.

Required Parameters
-------------------

::

- *name*
- either *start* or *control*

Default Parameters
------------------

::

- expected = running
- timeout = 10
- all the others are default to None


Copyright (C) 2012 CERN
"""
import re
from simplevisor.errors import ConfigurationError
import simplevisor.log as log
import sys
import time
from simplevisor import utils

MAXIMUM_LOG = 100

class Service(object):
    """
    Service class.
    """
    
    def __init__(self, name, expected="running",
                 timeout=10,
                 control=None, path=None, pattern=None,
                 restart=None, start=None, status=None, stop=None):
        """ Service constructor. """
        if control is None and start is None:
            raise ConfigurationError("Service entries requires either a "
                                     "control or a start parameter: %s" %
                                     name)
        self.name = name
        self._opts = {"name"    : name,
                      "expected"  : expected,
                      "control"  : control,
                      "path"    : path,
                      "pattern" : pattern,
                      "restart" : restart,
                      "start"   : start,
                      "status"  : status,
                      "stop"    : stop,
                      "timeout" : timeout, }
        self._status = {"name"  : name,
                        "log"   : list(),
                        }
        self.is_new = True
        if control is None and status is None:
            if sys.platform != "linux2":
                msg = "don't know how to read process table, you " + \
                      "must specify a status command for service %s" % name
                raise ValueError(msg)
            if pattern is not None:
                pat = pattern
            else:
                pat = " ".join(self.get_cmd("start"))
            try:
                self._opts["pattern_re"] = re.compile(pat)
                log.LOG.debug("using %s as pattern for service %s" %
                              (pat, name))
            except re.error:
                error = sys.exc_info()[1]
                msg = "%s service pattern not valid: %s" % error
                raise ConfigurationError(msg)
            
    def get_child(self, path):
        """
        Return a child by its path.
        """
        first = path.pop(0)
        if first == self.name:
            return self
        raise ValueError("not found")
    
    def get_cmd(self, subcmd):
        """
        Return a command given the sub command.
        """
        base = []
        if self._opts["control"] is not None: # standard use case
            if self._opts[subcmd] is None:
                base = self._opts["control"].split()
                base.append(subcmd)
            else:
                base = self._opts[subcmd].split()
        else: # other use case
            base = self._opts[subcmd].split()
        return base
        
    def __execute(self, cmd):
        """ Execute the given command. """
        env = None
        if self._opts["path"] is not None:
            env = {"PATH" : self._opts["path"]}
        try:
            log.LOG.debug("executing %s" % " ".join(cmd))
            result = utils.timed_process(cmd, self._opts["timeout"], env)
            log.LOG.debug("%s returned: %s" % (" ".join(cmd), result))
            return result
        except utils.ProcessTimedout:
            log.LOG.error("%s timedout %d seconds" % (" ".join(cmd),
                                                 self._opts["timeout"]))
            return (1, "", "timeout")
        except utils.ProcessError:
            error = sys.exc_info()[1]
            log.LOG.error("error running %s: %s" % (" ".join(cmd),
                                                error))
            return (1, "", "%s" % error)
    
    def adjust(self, timeout=5):
        """
        Start/stop according to expected status.
        """
        log.LOG.debug("adjusting service: %s" % self._opts["name"])
        self.is_new = False
        to_verify = False
        (rcode, _, _) = self.status()
        if rcode == 0:
            if self._opts["expected"] == "stopped":
                result = self.stop()
                log.LOG.info("%s stopped with %s" %
                             (self._opts["name"], result))
                self._status_log("stop", result)
                to_verify = True
        elif rcode == 3:
            if self._opts["expected"] == "running":
                result = self.start()
                log.LOG.info("%s started with %s" %
                             (self._opts["name"], result))
                self._status_log("start", result)
                to_verify = True
        else: # unknown/dead/hang...
            stop_res = self.stop()
            self._status_log("stop", stop_res)
            log.LOG.info("%s stopped for cleaning %s" %
                     (self._opts["name"], stop_res))
            if self._opts["expected"] == "running":
                result = self.start()
                log.LOG.info("%s started with %s" %
                             (self._opts["name"], result))
                self._status_log("start", result)
            to_verify = True
        if to_verify:
            t_max = time.time() + timeout
            while time.time() <= t_max:
                checked_status, _ = self.check()
                if checked_status:
                    return
                time.sleep(0.2)
            log.LOG.critical("service %s could not be adjusted." %
                             self._opts["name"])
            raise ConfigurationError("service %s could not be adjusted." %
                                     self._opts["name"])
        
    def start(self):
        """
        This method takes care of starting the service using the
        start command. If no start command is provided...
        """
        result = self.__execute(self.get_cmd("start"))
        self._status_log("start", result)
        return result
    
    def stop(self):
        """
        This method takes care of stopping the service which means
        it will run the stop command if provided.
        
        If not provided the process id will be looked in the process
        table and the process will be killed with a *SIGTERM* signal
        first and with a *SIGKILL* signal if it fails to stop.
        """
        if self._opts["control"] is None and self._opts["stop"] is None:
            pid_info = self.pidof()
            if pid_info is None:
                result = (0, "", "")
                log.LOG.info("%s already stopped" %
                         (self._opts["name"], ))
            else:
                pids = [x[0] for x in pid_info]
                utils.kill_pids(pids, self._opts["timeout"])
                log.LOG.info("%s killed by killing processes: %s" %
                         (self._opts["name"],
                          " ".join(map(str, pids))))
                result = (0, "", "")
        else:
            result = self.__execute(self.get_cmd("stop"))
        self._status_log("stop", result)
        return result
    
    def status(self):
        """
        This method return the status of the service.
        
        The status of a service is determined using the status command.
        
        If no status command is provided, the status of the process will
        be looked in the process table if any search pattern has been
        provided.
        
        In case a pattern is not provided the start command will be
        used as pattern.
        """
        if self._opts["control"] is None and self._opts["status"] is None:
            pid_info = self.pidof()
            if pid_info is None:
                log.LOG.debug("%s not running" % (self._opts["name"], ))
                result = (3, "", "")
            else:
                log.LOG.debug("%s running" % (self._opts["name"], ))
                result = (0, "", "")
        else:
            result = self.__execute(self.get_cmd("status"))
        self._status_log("status", result)
        return result
    
    def check(self):
        """
        This method check the service status against the expected one.
        """
        (status, _, _) = self.status()
        check_status = True
        output = "OK"
        if self.is_enabled():
            if status == 0:
                output = "%s: OK, running, as expected" % self.name
            elif status == 3:
                check_status = False
                output = "%s: WARNING, not running, not expected" % \
                            (self.name, )
            else:
                check_status = False
                output = "%s: WARNING, in \"dirty\" state: %d" % \
                            (self.name, status)
        else:
            if status == 0:
                check_status = False
                output = "%s: WARNING, found running, not expected" % \
                            (self.name, )
            elif status == 3:
                output = "%s: OK, not running, as expected" % \
                            (self.name, )
            else:
                check_status = False
                output = "%s: WARNING, in \"dirty\" state: %d" % \
                            (self.name, status)
        return (check_status, [output, ])
    
    def restart(self):
        """
        This method takes care of restarting the service.
        
        If the service does not have a restart command the service will be
        restarted doing a *stop+start*.
        
        If the service does have a restart command this will be used in
        order to restart the service.
        """
        restart_cmd = True
        if self._opts["control"] is not None:
            if self._opts["restart"] == "stop+start":
                restart_cmd = False
        else:
            if self._opts["restart"] is None:
                restart_cmd = False
        
        if restart_cmd:
            result = self.__execute(self.get_cmd("restart"))
            log.LOG.info("%s restarted with %s" % (self.name, result))
            self._status_log("restart", result)
            return result
        else:
            rstop = self.stop()
            rstart = self.start()
            rjoint = utils.merge_status(rstop, rstart)
            log.LOG.info("%s stop+start with %s" % (self.name, rjoint))
            self._status_log("stop+start", rjoint)
            return rjoint
        
    def pidof(self):
        """ Return the pid of the service. """
        pat_re = self._opts.get("pattern_re", None)
        if pat_re is not None:
            return utils.pidof(pat_re)
        return None
        
    def _status_log(self, operation, output):
        """
        Log the operation output.
        """
        self._status.setdefault("log", list())
        self._status["log"].append({"time" : time.time(),
                                    "operation" : operation,
                                    "output" : output})
        self._status["log"] = self._status["log"][-MAXIMUM_LOG:]
        
    def is_enabled(self):
        """
        Return *True* if the service is expected to run,
        *False* in other case.
        """
        return self._opts["expected"] == "running"
    
    def __str__(self):
        """
        Return the string representation.
        """
        return "service %s" % self._opts["name"]
            
    def get_id(self):
        """
        Return the id of the service.
        """
        text_id = "%s|%s|%s" % (self._opts["name"],
                                self._opts["expected"],
                                " ".join(self.get_cmd("start")),)
        return utils.md5_hash(text_id).hexdigest()
    
    def load_status(self, status):
        """
        Load the status from the previous run.
        """
        if status is None:
            return
        self.is_new = False
        self._status = status
            
    def dump_status(self):
        """
        Return the status to be saved for future runs.
        """
        # removing log for now
        if "log" in self._status:
            del(self._status["log"])
        return self._status
    