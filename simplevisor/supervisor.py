"""
This module implements a :py:class:`Supervisor` class.

An example of supervisor declaration::

    <entry>
        type = supervisor
        name = svisor1
        max_restarts = 10
        max_time = 60
        strategy = one_for_one
        stop_all = false
        <children>
            .... other supervisors or services
        </children>
    </entry>
    
Parameters
----------

name
    unique name of the supervisor.

max_restarts
    max number of restarts (linked with max_time), None to restart infinitely.

max_time
    window time to count the number of restarts, None to restart infinitely.
    
timeout
    the maximum timeout for start, stop, status and restart commands,
    set to one minute by default.

strategy
    - one_for_one: if a child process terminates, only that process
      is restarted.
    
    - one_for_all: if a child process terminates, all other
      child processes are terminated and then all child processes,
      including the terminated one, are restarted.
    
    - rest_for_one: If a child process terminates, the *rest* of the
      child processes i.e. the child processes after the terminated
      process in start order are terminated. Then the terminated
      child process and the rest of the child processes are restarted.
      
stop_all
    set to *true* if you want to stop the supervisor and its children.
    Default value is *false*.
    
children
    children structure.

Required Parameters
-------------------

::

- children section is required or supervisor is not useful

Default Parameters
------------------

::

- name = supervisor
- stop_all = false
- max_restarts = 10
- max_time = 60
- timeout = 60
- strategy = one_for_one

Copyright (C) 2012 CERN
"""
from simplevisor.errors import ConfigurationError
import simplevisor.log as log
import simplevisor.utils as utils
from simplevisor.service import Service
import sys
import time

MAXIMUM_RESTARTS = 10

def new_child(options, inherit=dict()):
    """
    Return a new child.
    """
    if "timeout" not in options:
        options["timeout"] = inherit.get("timeout", 60)
    try:
        tmp_type = options.pop("type")
    except KeyError:
        msg = "type not specified for entry: %s" % options
        log.LOG.error(msg)
        raise ConfigurationError(msg)
    child = None
    if tmp_type == "service":
        try:
            if inherit.get("stop_all", False):
                options["expected"] = "stopped"
            child = Service(**options)
        except TypeError:
            error = sys.exc_info()[1]
            msg = "Service entry not valid:\n%s\n%s" % (options, error)
            log.LOG.error(msg)
            raise ConfigurationError(msg)
    elif tmp_type == "supervisor":
        try:
            if inherit.get("stop_all", False):
                options["stop_all"] = "true"
            child = Supervisor(**options)
        except TypeError:
            error = sys.exc_info()[1]
            msg = "Supervisor entry not valid:\n%s\n%s" % (options, error)
            log.LOG.error(msg)
            raise ConfigurationError(msg)
    else:
        msg = "entry type non supported: %s" % (tmp_type,)
        log.LOG.error(msg)
        raise ConfigurationError(msg)
    return child

class Supervisor(object):
    """
    Supervisor class.
    """
    
    def __init__(self, name="supervisor", stop_all="false",
                 max_restarts=10, max_time=60, timeout=60,
                 strategy="one_for_one",
                 children = dict()):
        """ Constructor. """
        self.name = name
        self.stop_all = stop_all == "true"
        self.max_restarts = max_restarts
        if self.max_restarts == "" or self.max_restarts == "None":
            self.max_restarts = None
        self.max_time = max_time
        if self.max_time == ""  or self.max_time == "None":
            self.max_time = None
        self.timeout = timeout
        self.strategy = strategy
        self._children = list()
        self._children_dict = dict()
        self._children_name = dict()
        self.add_child_set(children.get("entry", []))
        if len(self._children) == 0:
            raise ConfigurationError(
                    "A supervisor must have at least one child.")
        self.restarts = list()
        self.is_new = True
    
    def add_child_set(self, children):
        """
        Add a child set.
        """
        if type(children) == dict:
            self.add_child(children)
        elif type(children) == list:
            for child in children:
                self.add_child(child)
    
    def add_child(self, options):
        """
        Add a child.
        """
        inherit = {"timeout" : self.timeout,
                   "stop_all" : self.stop_all}
        n_child = new_child(options, inherit)
        if n_child is not None:
            if n_child.name in self._children_name:
                raise ConfigurationError(
                    "Two entries with the same name: %s" % n_child.name)
            self._children.append(n_child)
            self._children_dict[n_child.get_id()] = n_child
            self._children_name[n_child.name] = n_child
            
    def get_child(self, path):
        """
        Return a child by its path.
        """
        first = path.pop(0)
        if first in self._children_name:
            if not path:
                # found
                return self._children_name[first]
            else:
                return self._children_name[first].get_child(path)
        raise ValueError("not found")
            
    def adjust(self):
        """
        Start/stop all elements according to their expected state.
        """
        self.is_new = False
        log.LOG.debug("adjust supervisor: %s" % self.name)
        for child in self._children:
            child.adjust()
            
    def start(self):
        """
        This method takes care of starting the supervisor and its children.
        """
        result = (0, "", "")
        for child in self._children:
            presult = child.start()
            result = utils.merge_status(result, presult)
            log.LOG.debug("%s started with %s" % (self.name, result))
        return result
    
    def stop(self):
        """
        This method takes care of stopping the supervisor and its children.
        """
        result = (0, [], [])
        for child in self._children:
            presult = child.stop()
            result = utils.merge_status(result, presult)
            log.LOG.debug("%s stopped with %s" % (self.name, result))
        return result
    
    def status(self):
        """
        This method is not implemented.
        """
        raise NotImplementedError
    
    def restart(self):
        """
        This method takes care of restarting the supervisor.
        """
        result = (0, [], [])
        for child in self._children:
            presult = child.restart()
            result = utils.merge_status(result, presult)
            log.LOG.debug("%s restarted with %s" % (self.name, result))
        return result
    
    def check(self):
        """
        This method check the children status against the expected one.
        """
        health = True
        health_output = list()
        for child in self._children:
            log.LOG.debug("check for child %s" % child.name)
            (phealth, output) = child.check()
            log.LOG.debug("child %s: %s, %s" % (child.name, phealth, output))
            health_output.extend(output)
            health = health and phealth
        if health:
            msg = "%s: OK, as expected" % self.name
        else:
            msg = "%s: WARNING, not expected" % self.name
        health_output = [msg, health_output]
        return (health, health_output)
                        
            
    def supervise(self):
        """
        This method check that children are running/stopped according
        to the configuration.
        """
        for child in self._children:
            fail = None
            if isinstance(child, Supervisor):
                (rcode, _, _ ) = child.supervise()
                if rcode != 0:
                    fail = (child, child.start)
            else: # it is a Service
                (rcode, _, _ ) = child.status()
                if rcode == 0:
                    if not child.is_enabled():
                        # FAIL, need to stop it
                        fail = (child, child.stop)
                elif rcode == 3:
                    if child.is_enabled():
                        # FAIL, need to start it
                        fail = (child, child.start)
                else: # unknown/dead/hang ...
                    if child.is_enabled():
                        # FAIL, need to restart
                        fail = (child, child.restart)
                    else:
                        # FAIL, need to stop
                        fail = (child, child.stop)
            if fail is not None:
                log.LOG.error("%s found in an unexpected state: %d" %
                            (fail[0], rcode))
                self.restarts.append(time.time())
                log.LOG.error("applying %s strategy to supervisor %s" %
                          (self.strategy, self.name))
                getattr(self, self.strategy)(*fail)
            if self.failed():
                # the supervisor terminates all the child processes
                # and then itself
                self.stop()
                return (3, "", "")
        return (0, "", "")
    
    def one_for_one(self, child, child_action):
        """
        Implement *one_for_one* strategy.
        
        If a child process terminates, only that process is restarted.
        """
        child_action()
    
    def one_for_all(self, child, child_action):
        """
        Implement *one_for_all* strategy.
        
        If a child process terminates, all other child processes are
        terminated and then all child processes, including the terminated
        one, are restarted.
        """
        for temp_child in self._children:
            if temp_child is child:
                continue
            if temp_child.is_enabled():
                temp_child.stop()
        for temp_child in self._children:
            if temp_child is child:
                child_action()
                continue
            if temp_child.is_enabled():
                temp_child.start()
    
    def rest_for_one(self, child, child_action):
        """
        Implement *rest_for_one* strategy.
        
        If a child process terminates, the *rest* of the child processes
        (i.e. the child processes after the terminated process in start order)
        are terminated. Then the terminated child process and the rest
        of the child processes are restarted.
        """
        index = self._children.index(child)
        for temp_child in self._children[index:]:
            if temp_child is child:
                continue
            if temp_child.is_enabled():
                temp_child.stop()
        for temp_child in self._children[index:]:
            if temp_child is child:
                child_action()
                continue
            if temp_child.is_enabled():
                temp_child.start()
                    
    def failed(self):
        """
        Return True if there has been more than *max_restarts* restarts
        in the last *max_time* seconds of time.
        """
        if self.max_restarts is None or self.max_time is None:
            self.restarts = self.restarts[-MAXIMUM_RESTARTS:]
            return False
        num = 0
        new = list()
        now = time.time()
        for restart in self.restarts:
            if now - restart <= self.max_time:
                new.append(restart)
                num += 1
        self.restarts = new
        if num > self.max_restarts:
            log.LOG.error("%s handled %d restarts in less than %d seconds" %
                        (self.name, num, self.max_time))
            return True
        return False
    
    def is_enabled(self):
        """
        Return *True* if supervisor is expected to run, 
        *False* in other case.
        """
        return not self.stop_all
    
    def __str__(self):
        """
        Return the string representation.
        """
        return "supervisor %s" % self.name
            
    def get_id(self):
        """
        Return the id of the supervisor.
        """
        return utils.md5_hash(self.name).hexdigest()
    
    def load_status(self, status):
        """
        Load the status from the previous run.
        """
        if status is None:
            return
        self.is_new = False
        cstatus = status.pop("children", dict())
        for identifier, child in self._children_dict.items():
            if identifier in cstatus:
                child.load_status(cstatus[identifier])
        keys = {"restarts" : list(), }
        for key, val in keys.items():
            setattr(self, key, status.pop(key, val))
            
    def dump_status(self):
        """
        Return the status to be saved for future runs.
        """
        children_status = dict()
        for child in self._children:
            children_status[child.get_id()] = child.dump_status()
        values = dict()
        values["name"] = self.name
        values["restarts"] = self.restarts
        values["children"] = children_status
        return values
