"""
This module implements a :py:class:`Supervisor` class.

An example of supervisor declaration::

    <entry>
        type = supervisor
        name = supervisor1
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

Copyright (C) 2013-2016 CERN
"""
import logging
import sys
import time

from mtb.conf import unify_keys
from mtb.modules import md5_hash
from mtb.validation import get_int_or_die

from simplevisor.errors import SimplevisorError, ServiceError
from simplevisor.service import Service


ALLOWED_STRATEGIES = {
    'one_for_one': 'OneForOne',
    'rest_for_one': 'RestForOne',
    'one_for_all': 'OneForAll',
}
DEFAULT_ADJUSTMENTS = 3
DEFAULT_EXPECTED = "none"
DEFAULT_STRATEGY = "one_for_one"
DEFAULT_WINDOW = 12


def new_child(options, inherit=None):
    """
    Return a new child.
    """
    if options is None:
        return None
    if inherit is None:
        inherit = dict()
    unify_keys(options)
    try:
        tmp_type = options.pop("type")
    except KeyError:
        raise SimplevisorError(
            "type not specified for entry: %s" % (options, ))
    tmp_expected = inherit.get("expected", DEFAULT_EXPECTED)
    if tmp_expected != "none":
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

    @classmethod
    def _strategy_by_name(cls, name):
        """
        Return the strategy by its name.
        :param name: the name of the strategy
        """
        if not hasattr(cls, "strategies"):
            cls.strategies = getattr(__import__(
                "simplevisor.strategies"), "strategies")
        return getattr(cls.strategies, name)

    def __init__(self,
                 adjustments=DEFAULT_ADJUSTMENTS,
                 children=None,
                 expected=DEFAULT_EXPECTED,
                 logname=None,
                 name="supervisor",
                 strategy=DEFAULT_STRATEGY,
                 window=DEFAULT_WINDOW,
                 **kwargs):
        """
        Constructor.
        :param name: the supervisor name
        :param expected: the expected status (running|stopped)
        :param window: the window of adjustments cycles to consider
        :param adjustments: the maximum number of adjustments allowed
        :param strategy: the strategy to be applied
        :param children: the list of children attached to the supervisor
        :param kwargs: extra parameters
        """
        if children is None:
            children = dict()
        if logname is None:
            logname = self.__class__.__name__
        self.logname = logname
        self.logger = logging.getLogger(logname)
        self.name = name
        self._expected = expected.lower()
        self._window = get_int_or_die(
            window,
            "supervisor %s should have a valid integer window value: %s" %
            (name, window))
        self._adjustments = get_int_or_die(
            adjustments,
            "supervisor %s should have a valid integer adjustments value: %s" %
            (name, adjustments))
        if strategy not in ALLOWED_STRATEGIES:
            raise ValueError(
                "supervisor %s does not support given strategy: %s" %
                (name, strategy, ))
        self._strategy_name = strategy
        self._strategy = Supervisor._strategy_by_name(
            ALLOWED_STRATEGIES[strategy])(self)
        for key in kwargs.keys():
            if not key.startswith("var_"):
                raise SimplevisorError(
                    "an invalid property has been specified for"
                    "supervisor %s: %s" %
                    (name, key))
        self._children = list()
        self._children_by_id = dict()
        self._children_by_name = dict()
        self.add_child_set(children.get("entry", list()))
        if len(self._children) == 0:
            raise SimplevisorError(
                "empty supervisor found: %s" % (self.name, ))
        self._cycles = list()
        self._is_new = True

    def add_child_set(self, children):
        """
        Add a set of children.
        :param children: the list of children, if a dict is given it will be
        interpreted as a single child
        """
        given_type = type(children)
        if given_type == dict:
            self.add_child(children)
        elif given_type == list:
            for child in children:
                self.add_child(child)
        else:
            raise ValueError(
                "supervisor %s accept a list of children or a single child, "
                "%s given" % (self.name, given_type))

    def add_child(self, options):
        """
        Add a child.
        :param options: the child configuration
        """
        if "logname" not in options:
            options["logname"] = self.logname
        n_child = new_child(options, {"expected": self._expected, })
        if n_child is not None:
            if n_child.name in self._children_by_name:
                raise SimplevisorError(
                    "supervisor %s got two entries with the same name: %s" %
                    (self.name, n_child.name))
            # list where order is preserved
            self._children.append(n_child)
            # dict for fast access by id
            self._children_by_id[n_child.get_id()] = n_child
            # dict for fast access by name
            self._children_by_name[n_child.name] = n_child

    def get_child(self, path):
        """
        Return a child by its path.
        :param path: a list which identifies the path tokens to identify a
        single child by its name
        """
        first = path.pop(0)
        if first in self._children_by_name:
            if not path:
                # found
                return self._children_by_name[first]
            else:
                return self._children_by_name[first].get_child(path)
        raise ValueError("path not found: %s" % (path, ))

    def start(self):
        """
        This method takes care of starting the supervisor and its children.
        """
        self.logger.debug(
            "calling start on supervisor %s.%s",
            self.name, self._strategy_name)
        try:
            self._strategy.start(self._children)
        except ServiceError:
            error = sys.exc_info()[1]
            return error.result
        return None

    def stop(self):
        """
        This method takes care of stopping the supervisor and its children.
        """
        self.logger.debug(
            "calling stop on supervisor %s.%s",
            self.name, self._strategy_name)
        try:
            self._strategy.stop(self._children)
        except ServiceError:
            error = sys.exc_info()[1]
            return error.result
        return None

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
        self.logger.debug(
            "calling stop+start on supervisor %s.%s",
            self.name, self._strategy_name)
        result = self.stop()
        if result is not None:
            return result
        return self.start()

    def check(self):
        """
        This method check the children status against the expected one.
        """
        healthy = True
        health_output = list()
        for child in self._children:
            self.logger.debug("checking child: %s", child.name)
            (child_health, output) = child.check()
            self.logger.debug(
                "child check result for %s: %s, %s",
                child.name, child_health, output)
            health_output.extend(output)
            healthy = healthy and child_health
        if healthy:
            msg = "%s: OK, as expected" % (self.name, )
        else:
            msg = "%s: WARNING, not expected" % (self.name, )
        health_output = [msg, health_output, ]
        return healthy, health_output

    def supervise(self, result=None):
        """
        This method check that children are running/stopped according
        to the configuration.
        :param result: dictionary where children result should be added
        """
        self.logger.debug(
            "calling supervise on supervisor %s.%s",
            self.name, self._strategy_name)
        successful = self._strategy.supervise(self._children, result)
        if (not successful) and self.failed():
            # the supervisor should stop the children
            self.stop()
            return False
        return True

    def log_adjustment(self, one_adjustment):
        """ Log cycle adjustment.
        :param one_adjustment: if at least an adjustment has been performed
        :rtype : bool
        """
        self._cycles.append((time.time(), one_adjustment))
        # shorten it, keep only the window of interest
        self._cycles = self._cycles[-self._window:]

    def adjustments(self):
        """
        Return the number of adjustments in the logged cycles.
        """
        return len(
            [1 for (_, adjusted) in self._cycles[-self._window:] if adjusted])

    def failed(self):
        """
        Return True if there has been more adjustments actions than
        the provided *adjustments* value in the last *window* of
        supervision cycles configured.
        """
        adjusted = self.adjustments()
        if adjusted > self._adjustments:
            self.logger.error(
                "%s handled %d adjustments in %s supervision cycles",
                self.name, adjusted, self._window)
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
        return md5_hash(self.name.encode()).hexdigest()

    def load_status(self, status):
        """
        Load the status from the previous run.
        :param status: status dictionary
        """
        if status is None:
            return
        self._is_new = False
        children_status = status.pop("children", dict())
        for identifier, child in self._children_by_id.items():
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
