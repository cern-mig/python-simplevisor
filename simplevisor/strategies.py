"""
Strategies implemented.

Copyright (C) 2013 CERN
"""
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
        logged = False
        for child in children:
            if isinstance(child, Supervisor):
                successful = child.supervise(result)
                if not successful:
                    # start it, it should be stopped already
                    child.start()
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
                if not logged:
                    logged = True
                    self._parent.log_adjustment(True)
                    if self._parent.failed():
                        # the supervisor should stop the children
                        return False
        if not logged:
            self._parent.log_adjustment(False)
        return True


class DependentStrategy(SupervisionStrategy):
    """
    Pseudo strategy with common actions between *rest_for_one*
    and *one_for_all*.
    """

    def __init__(self, parent):
        """ Constructor. """
        super(DependentStrategy, self).__init__(parent)

    def start(self, children):
        """
        Start children carefully and in order.
        """
        for child in children:
            if isinstance(child, Supervisor):
                child.start()
            elif isinstance(child, Service):
                # wait for the service to be started before moving
                # to the next child
                child.cond_start(careful=True)
            else:
                raise AssertionError(
                    "unexpected child type: %s" % (type(child), ))

    def stop(self, children):
        """
        Stop children carefully and in reverse order.
        """
        for child in children.reverse():  # reverse order
            if isinstance(child, Supervisor):
                child.stop()
            elif isinstance(child, Service):
                # wait for the service to be stopped before moving
                # to the next child
                child.cond_stop(careful=True)
            else:
                raise AssertionError(
                    "unexpected child type: %s" % (type(child), ))

    def adjust(self, children, child):
        """ To be implemented. """

    def supervise(self, children, result=None):
        """
        Supervise children and call adjust in case of problems.
        """
        if result is None:
            result = dict()
        logged = False
        for child in children:
            to_be_adjusted = False
            if isinstance(child, Supervisor):
                to_be_adjusted = not child.supervise(result)
            elif isinstance(child, Service):
                to_be_adjusted = not child.check()[0]
                if to_be_adjusted:
                    result["adjusted"] = result.get("adjusted", 0) + 1
                else:  # not adjusted
                    result["ok"] = result.get("ok", 0) + 1
            else:  # unexpected
                raise AssertionError(
                    "unexpected child type: %s" % (type(child), ))
            if to_be_adjusted:
                self.adjust(children, child)
                if not logged:
                    logged = True
                    self._parent.log_adjustment(True)
                    if self._parent.failed():
                        # the supervisor should stop the children
                        return False
        if not logged:
            self._parent.log_adjustment(False)
        return True


class RestForOne(SupervisionStrategy):
    """
    Implements *rest_for_one* strategy.

    If a child process terminates, the *rest* of the child processes
    (i.e. the child processes after the terminated process in start order)
    are terminated. Then the terminated child process and the rest
    of the child processes are restarted.
    """

    def __init__(self, parent):
        """ Constructor. """
        super(RestForOne, self).__init__(parent)

    def adjust(self, children, child):
        """ Implement adjust. """
        children_subset = children[children.index(child):]
        self.stop(children_subset)
        self.start(children_subset)


class OneForAll(SupervisionStrategy):
    """
    Implements *one_for_all* strategy.

    If a child process terminates, all other child processes are
    terminated and then all child processes, including the terminated
    one, are restarted.
    """

    def __init__(self, parent):
        """ Constructor. """
        super(OneForAll, self).__init__(parent)

    def adjust(self, children, _):
        """ Implement adjust. """
        self.stop(children)
        self.start(children)


