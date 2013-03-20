"""
Strategies implemented.

Copyright (C) 2013 CERN
"""
import mtb.log as log
from mtb.proc import merge_status

from simplevisor.service import Service
from simplevisor.supervisor import Supervisor


class SupervisionStrategy(object):
    """ Strategy interface. """

    def __init__(self, parent):
        """ Constructor. """
        self._parent = parent

    def start(self, children):
        """ Start children according to implemented strategy. """

    def stop(self, children):
        """ Start children according to implemented strategy. """

    def supervise(self, children, result=None):
        """ Supervise children according to implemented strategy. """


class OneForOne(SupervisionStrategy):
    """
    Implements *one_for_one* strategy.

    If a child process terminates, only that process is restarted.
    """

    def __init__(self, parent):
        """ Constructor. """
        super(OneForOne, self).__init__(parent)

    def start(self, children):
        """ Start children with one for one strategy. """
        for child in children:
            if isinstance(child, Supervisor):
                child.start()
            elif isinstance(child, Service):
                child.cond_start()
            else:
                raise AssertionError(
                    "unexpected child type: %s" % (type(child), ))

    def stop(self, children):
        """
        This method takes care of stopping all the children.
        """
        for child in children:
            if isinstance(child, Supervisor):
                child.stop()
            elif isinstance(child, Service):
                child.cond_stop()
            else:
                raise AssertionError(
                    "unexpected child type: %s" % (type(child), ))

    def supervise(self, children, result=None):
        """ Supervise children according to implemented strategy. """
        if result is None:
            result = dict()
        one_adjustment = False
        for child in children:
            if isinstance(child, Supervisor):
                successful = child.supervise(result)
                if not successful:
                    child.restart()
                    adjusted = True
            elif isinstance(child, Service):
                adjusted = child.cond_adjust()
                if adjusted:
                    result["adjusted"] = result.get("adjusted", 0) + 1
                else:  # not adjusted
                    result["ok"] = result.get("ok", 0) + 1
            else:  # unexpected
                raise AssertionError(
                    "unexpected child type: %s" % (type(child), ))
            if adjusted:
                if not one_adjustment:
                    one_adjustment = True
                    self._parent.log_adjustment(True)
                    if self._parent.failed():
                        # the supervisor should stop the children
                        return False
        self._parent.log_adjustment(one_adjustment)
        return True
