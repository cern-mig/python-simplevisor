"""
This module implements a :py:class:`Supervisor` class.

An example of supervisor declaration::

    <entry>
        type = supervisor
        name = svisor1
        window = 12
        adjustments = 3
        strategy = one_for_one
        expected = none
        <children>
            .... other supervisors or services
        </children>
    </entry>

Parameters
----------

*name*
    unique name of the supervisor.

*window*
    window of supervision cycles which should be considered when defining
    if a supervisor is in a failing state.

*adjustments*
    maximum number of cycles on which a child adjustment was needed
    in the given window of supervision cycle in order to consider
    it a failure.

*strategy*
    - one_for_one: if a child process terminates, only that process
      is restarted.

    - one_for_all: if a child process terminates, all other
      child processes are terminated and then all child processes,
      including the terminated one, are restarted.

    - rest_for_one: If a child process terminates, the *rest* of the
      child processes i.e. the child processes after the terminated
      process in start order are terminated. Then the terminated
      child process and the rest of the child processes are restarted.

*expected*
    none|running|stopped

*children*
    children structure.

Required Parameters
-------------------

::

- children section is required or supervisor is not useful

Default Parameters
------------------

::

- name = supervisor
- expected = none
- window = 12
- adjustments = 3
- strategy = one_for_one

Copyright (C) 2013 CERN
"""
from simplevisor.errors import SimplevisorError
import simplevisor.log as log
import simplevisor.utils as utils
from simplevisor.service import Service
import sys
import time

DEFAULT_EXPECTED = "none"
DEFAULT_WINDOW = 12
DEFAULT_ADJUSTMENTS = 3


def new_child(options, inherit=dict()):
    """
    Return a new child.
    """
    if options is None:
        return None
    utils.unify_keys(options)
    try:
        tmp_type = options.pop("type")
    except KeyError:
        raise SimplevisorError(
            "type not specified for entry: %s" % (options, ))
    child = None
    tmp_expected = inherit.get("expected", DEFAULT_EXPECTED)
    if (tmp_expected != "none"):
        options["expected"] = tmp_expected
    if tmp_type == "service":
        try:
            child = Service(**options)
        except TypeError:
            error = sys.exc_info()[1]
            raise SimplevisorError(
                "Service entry not valid:\n%s\n%s" % (options, error))
    elif tmp_type == "supervisor":
        try:
            child = Supervisor(**options)
        except TypeError:
            error = sys.exc_info()[1]
            raise SimplevisorError(
                "Supervisor entry not valid:\n%s\n%s" % (options, error))
    else:
        raise SimplevisorError(
            "entry type non supported: %s" % (tmp_type,))
    return child


class Supervisor(object):
    """
    Supervisor class.
    """

    def __init__(self, name="supervisor", expected=DEFAULT_EXPECTED,
                 window=DEFAULT_WINDOW, adjustments=DEFAULT_ADJUSTMENTS,
                 strategy="one_for_one", children=dict(), **kwargs):
        """ Constructor. """
        self.name = name
        self._expected = expected.lower()
        self._window = utils.get_int_or_die(
            window,
            "window value for %s is not a valid integer: %s" %
            (name, window))
        self._adjustments = utils.get_int_or_die(
            adjustments,
            "adjustments value for %s is not a valid integer: %s" %
            (name, adjustments))
        self._strategy = strategy
        for key in kwargs.keys():
            if not key.startswith("var_"):
                raise SimplevisorError(
                    "an invalid property has been specified for %s: %s" %
                    (name, key))
        self._children = list()
        self._children_dict = dict()
        self._children_name = dict()
        self.add_child_set(children.get("entry", []))
        if len(self._children) == 0:
            raise SimplevisorError(
                "a supervisor must have at least one child.")
        self._cycles = list()
        self._is_new = True

    def add_child_set(self, children):
        """
        Add a child set.
        """
        if type(children) == dict:
            self.add_child(children)
        elif type(children) == list:
            for child in children:
                self.add_child(child)
        else:
            raise ValueError(
                "should be a list of children or a single child, "
                "unknown given")

    def add_child(self, options):
        """
        Add a child.
        """
        inherit = {"expected": self._expected, }
        n_child = new_child(options, inherit)
        if n_child is not None:
            if n_child.name in self._children_name:
                raise SimplevisorError(
                    "two entries with the same name: %s" % (n_child.name, ))
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
        self._is_new = False
        log.LOG.debug("adjust supervisor: %s" % (self.name, ))
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
        raise NotImplementedError(
            "status command not supported on a supervisor node, "
            "look at \"check\" command instead")

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
            log.LOG.debug("check for child %s" % (child.name, ))
            (phealth, output) = child.check()
            log.LOG.debug("child %s: %s, %s" % (child.name, phealth, output))
            health_output.extend(output)
            health = health and phealth
        if health:
            msg = "%s: OK, as expected" % (self.name, )
        else:
            msg = "%s: WARNING, not expected" % (self.name, )
        health_output = [msg, health_output]
        return (health, health_output)

    def supervise(self, result=None):
        """
        This method check that children are running/stopped according
        to the configuration.
        """
        if result is None:
            result = dict()
        one_adjustment = False
        for child in self._children:
            fail = None
            if isinstance(child, Supervisor):
                (rcode, _, _) = child.supervise(result)
                if rcode != 0:
                    fail = (child, child.start)
            else:  # it is a Service
                (rcode, _, _) = child.status()
                if rcode == 0:
                    if not child.is_enabled():
                        # FAIL, need to stop it
                        fail = (child, child.stop)
                elif rcode == 3:
                    if child.is_enabled():
                        # FAIL, need to start it
                        fail = (child, child.start)
                else:  # unknown/dead/hang ...
                    if child.is_enabled():
                        # FAIL, need to restart
                        fail = (child, child.restart)
                    else:
                        # FAIL, need to stop
                        fail = (child, child.stop)
                if fail is None:
                    result["ok"] = result.get("ok", 0) + 1
                else:  # failure
                    result["adjusted"] = result.get("adjusted", 0) + 1
            if fail is not None:  # failure
                log.LOG.info("%s found in an unexpected state: %d" %
                             (fail[0], rcode))
                if not one_adjustment:
                    one_adjustment = True
                    self._log_cycle(True)
                log.LOG.info("applying %s strategy to supervisor %s" %
                             (self._strategy, self.name))
                getattr(self, self._strategy)(*fail)
            if self.failed():
                # the supervisor terminates all the child processes
                # and then itself
                self.stop()
                return (3, "", "")
        self._log_cycle(False)
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

    def _log_cycle(self, one_adjustment):
        """
        Log one cycle result.
        """
        self._cycles.append((time.time(), one_adjustment))
        # shorten it, keep only the window of interest
        self._cycles = self._cycles[-self._window:]

    def failed(self):
        """
        Return True if there has been more adjustments actions than
        the provided *adjustments* value in the last *window* of
        supervision cycles configured.
        """
        adjusted = len(
            [1 for (_, adjusted) in self._cycles[-self._window:] if adjusted])
        if adjusted > self._adjustments:
            log.LOG.error(
                "%s handled %d adjustments in %s supervision cycles" %
                (self.name, adjusted, self._window))
            return True
        return False

    def is_enabled(self):
        """
        Return *True* if supervisor is expected to run,
        *False* in other case.
        """
        return self._expected == "running" or self._expected == "none"

    def __str__(self):
        """
        Return the string representation.
        """
        return "supervisor %s" % (self.name, )

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
        self._is_new = False
        children_status = status.pop("children", dict())
        for identifier, child in self._children_dict.items():
            if identifier in children_status:
                child.load_status(children_status[identifier])
        keys = {"cycles": list(), }
        for key, val in keys.items():
            setattr(self, "_%s" % (key, ), status.pop(key, val))

    def dump_status(self):
        """
        Return the status to be saved for future runs.
        """
        children_status = dict()
        for child in self._children:
            children_status[child.get_id()] = child.dump_status()
        values = {
            'name': self.name,
            'cycles': self._cycles,
            'children': children_status, }
        return values
