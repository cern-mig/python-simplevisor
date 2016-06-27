"""
This class implements a :py:class:`Service` abstraction.
As service we mean a process which runs in daemon mode.

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
        # table, however this is supported only on Linux.
        # If not specified start command is used as pattern.
        pattern = /path/to/script --conf /path/to/conf --daemon
    </entry>

If one of the parameters contains one or more spaces you should quote them
in url-like style, invoked commands are :py:func:`urllib.unquote`
before being launched like in this example::

    ...
    start = /path/to/script --conf /path/to/conf --space hello%20world start
    ...

The stdout and the stderr of the commands executed is logged as debug level
within the configured log system.

The commands declared should provide return codes according to the default
LSB Unix return codes,
for more info visit `LSB Core Specification <http://goo.gl/vQqaC>`_::

    0        program is running or service is OK
    1        program is dead and /var/run pid file exists
    2        program is dead and /var/lock lock file exists
    3        program is not running
    4        program or service status is unknown
    5-99     reserved for future LSB use
    100-149  reserved for distribution use
    150-199  reserved for application use
    200-254  reserved


Parameters
----------

*control*
    the control of the command to run. If specified it will be the prefix
    of *start/stop/status* commands.

*daemon*
    if the service command runs in foreground and you wish to daemonize
    it you can declare this option with value the pidfile path that should
    be used for the daemonization.

    If control is specified this option is ignored.

    Given the start command::

        start = /path/to/script --conf /path/to/conf

    and declaring::

        daemon = /path/to/script_pidfile.pid

    it is like specifying the following pair of commands/values::

     start = /usr/bin/simplevisor-loop -c 1 --pidfile \
/path/to/script_pidfile.pid --daemon /path/to/script --conf /path/to/conf

     stop = /usr/bin/simplevisor-loop --pidfile /path/to/script_pidfile.pid \
--quit

     status = /usr/bin/simplevisor-loop --pidfile /path/to/script_pidfile.pid \
--status

    Hence, if *daemon* is specified *stop* and *status* command
    are overwritten.

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
    Accepted values are valid python regular expressions: :py:mod:`re`.

*restart*
    specify a custom restart command.

    If <control> is specified:

        - if <restart> is not specified "<control> restart" is executed
        - if <restart> = "stop+start" a "<control> stop" followed by a
          "<control> start" is executed
        - else "<restart>" is executed

    If <control> is not specified:

        - if <restart> is not specified "<stop>" followed by
          "<start>" is executed
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

*timeout*
    the maximum timeout for any service command, set to 60 seconds by default.

Required Parameters
-------------------

::

- name
- one of: start, control

Default Parameters
------------------

::

- expected = running
- timeout = 60
- all the others are default to None


Copyright (C) 2013-2016 CERN
"""
import logging
import os
import re
import sys
import time

from mtb.modules import md5_hash, unquote
from mtb.proc import \
    timed_process, ProcessTimedout, ProcessError, \
    kill_pids, merge_status, pidof, which
from mtb.validation import mutex, reqall, reqany, get_int_or_die

from simplevisor.errors import ServiceError

MAX_LOG_MESSAGES = 100
DEFAULT_TIMEOUT = 60
DEFAULT_EXPECTED = "running"


class Service(object):
    """
    Service class.
    """

    def __init__(self, name,
                 control=None,
                 daemon=None,
                 expected=DEFAULT_EXPECTED,
                 logname=None,
                 path=None,
                 pattern=None,
                 restart=None,
                 start=None,
                 status=None,
                 stop=None,
                 timeout=DEFAULT_TIMEOUT,
                 **kwargs):
        """ Service constructor. """
        if logname is None:
            logname = self.__class__.__name__
        self.logger = logging.getLogger(logname)
        self.name = name
        self._opts = {
            "name": name,
            "expected": expected,
            "control": control,
            "daemon": daemon,
            "path": path,
            "pattern": pattern,
            "restart": restart,
            "start": start,
            "status": status,
            "stop": stop,
            "timeout": get_int_or_die(
                timeout,
                "timeout value for %s is not a valid integer: %s" %
                (name, timeout)), }
        self._status = {
            "name": name,
            "log": list(), }
        for key in kwargs:
            if not key.startswith("var_"):
                raise ValueError(
                    "invalid property for service %s: %s" % (name, key))
        self._is_new = True
        try:
            self._validate_opts()
        except ValueError:
            error = sys.exc_info()[1]
            raise ValueError(
                "service %s is not properly configured: %s" %
                (self.name, error))
        if control is None and daemon is not None:
            si_loop = which("simplevisor-loop")
            if si_loop is None:
                raise RuntimeError(
                    "cannot find simplevisor-loop command in the "
                    "environment: %s" % (os.environ["PATH"], ))
            common_path = "%s --pidfile %s" % (si_loop, daemon, )
            self._opts["start"] = (
                "%s -c 1 --daemon %s" % (common_path, start))
            self._opts["stop"] = ("%s --quit" % (common_path, ))
            self._opts["status"] = ("%s --status" % (common_path, ))
        elif control is None and status is None:
            if sys.platform != "linux2":
                raise ValueError(
                    "don't know how to read process table, you must specify "
                    "a status command for service: %s" % (name, ))
            if pattern is not None:
                pat = pattern
            else:
                pat = " ".join(self.get_cmd("start"))
            try:
                self._opts["pattern_re"] = re.compile(pat)
                self.logger.debug(
                    "using %s as pattern for service %s", pat, name)
            except re.error:
                error = sys.exc_info()[1]
                raise ValueError(
                    "%s service pattern not valid: %s" % (name, error))

    def _validate_opts(self):
        """ Validate options. """
        options = self._opts
        # at least start or control
        reqany(options, None, "start", "control")
        # either start or control
        mutex(options, "start", "control")
        # either control or daemon
        mutex(options, "daemon", "control")
        # if daemon then start is required
        reqall(options, "daemon", "start")
        # if pattern no status, stop, control
        mutex(options, "pattern", "status")
        mutex(options, "pattern", "stop")
        mutex(options, "pattern", "control")

    def get_child(self, path):
        """
        Return a child by its path.
        :param path: list containing the tokens representing the path to the
        requested child
        """
        first = path.pop(0)
        if first == self.name:
            return self
        raise ValueError("not found")

    def get_cmd(self, sub_command):
        """
        Return a command given the sub command.
        :param sub_command: the sub-command
        """
        if self._opts["control"] is not None:  # standard use case
            if self._opts[sub_command] is None:
                base = self._opts["control"].split()
                base.append(sub_command)
            else:
                base = self._opts[sub_command].split()
        else:  # other use case
            base = self._opts[sub_command].split()
        base = [unquote(token) for token in base]
        return base

    def __execute(self, cmd):
        """
        Execute the given command.
        :param cmd: list containing the command to execute
        """
        if self._opts["path"] is not None:
            env = {"PATH": self._opts["path"], }
        else:
            env = None
        cmd_str = " ".join(cmd)
        try:
            self.logger.debug("executing %s", cmd_str)
            result = timed_process(cmd, self._opts["timeout"], env)
            self.logger.debug("%s returned: %s", cmd_str, result)
            return result
        except ProcessTimedout:
            self.logger.warning(
                "%s timed out %d seconds", cmd_str, self._opts["timeout"])
            return 1, "", "timeout"
        except ProcessError:
            error = sys.exc_info()[1]
            self.logger.warning("error running %s: %s", cmd_str, error)
            return 1, "", "%s" % (error, )

    def cond_adjust(self, careful=False):
        """
        Start/stop according to expected status.

        :param careful: specify if the action should be careful,
        which means it will make sure that action was performed
        successfully and that the service is in the expected status
        @return: True if adjustment performed, False otherwise
        """
        self.logger.debug("conditional adjust for service: %s", self.name)
        changed = None
        (return_code, _, _) = self.status()
        result = (0, "", "")
        if return_code == 0 and (not self.is_enabled()):
            result = self.stop()
            self.logger.info(
                "service %s stopped with result: %s", self.name, result)
            self._status_log("stop", result)
            changed = "stop"
        elif return_code == 3 and self._opts["expected"] == "running":
            result = self.start()
            self.logger.info(
                "service %s started with result: %s", self.name, result)
            self._status_log("start", result)
            changed = "start"
        elif return_code not in [0, 3]:  # unknown/dead/hang...
            stop_result = self.stop()
            self._status_log("stop", stop_result)
            self.logger.info(
                "service %s stopped for cleaning with result: %s",
                self.name, stop_result)
            if self._opts["expected"] == "running":
                result = self.start()
                self.logger.info(
                    "service %s started with result: %s",
                    self.name, result)
                self._status_log("start", result)
            changed = "stop+start"
        if changed and result[0] != 0:
            error_message = "error during service %s action %s: %s" % \
                            (self.name, changed, result, )
            self.logger.error(error_message)
            raise ServiceError(error_message, result)
        if changed and careful:  # let's do it carefully
            t_max = time.time() + self._opts["timeout"]
            check_status = (True, "")
            while time.time() <= t_max:
                check_status = self.check()
                if check_status[0]:
                    return changed
                time.sleep(0.5)
            error_message = "error adjusting service %s, " \
                            "have been waiting %s" % \
                            (self.name, self._opts["timeout"])
            self.logger.error(error_message)
            raise ServiceError(
                error_message, (1, check_status[1], ""))
        return changed

    def cond_start(self, careful=False):
        """
        Conditional start based on status.

        :param careful: specify if the action should be careful,
        which means it will make sure that action was performed
        successfully and that the service is in the expected status
        """
        self.logger.debug("conditional start for service: %s", self.name)
        changed = None
        (return_code, _, _) = self.status()
        result = (0, "", "")
        if return_code == 3 and self._opts["expected"] == "running":
            result = self.start()
            self.logger.info(
                "service %s started with result: %s", self.name, result)
            self._status_log("start", result)
            changed = "start"
        elif return_code != 0 and self._opts["expected"] == "running":
            # unknown/dead/hang...
            stop_result = self.stop()
            self._status_log("stop", stop_result)
            self.logger.info(
                "service %s stopped for cleaning with result: %s",
                self.name, stop_result)
            result = self.start()
            self.logger.info(
                "service %s started with result: %s", self.name, result)
            self._status_log("start", result)
            changed = "stop+start"
        if changed and result[0] != 0:
            error_message = "error during service %s action %s: %s" % \
                (self.name, changed, result, )
            self.logger.error(error_message)
            raise ServiceError(error_message, result)
        if changed and careful:
            t_max = time.time() + self._opts["timeout"]
            while time.time() <= t_max:
                result = self.status()
                if result[0] == 0:
                    return changed
                time.sleep(0.5)
            error_message = "error starting service %s, " \
                            "have been waiting %s" % \
                            (self.name, self._opts["timeout"])
            self.logger.error(error_message)
            raise ServiceError(error_message)
        return changed

    def cond_stop(self, careful=False):
        """
        Conditional stop based on status.

        :param careful: specify if the action should be careful,
        which means it will make sure that action was performed
        successfully and that the service is in the expected status
        """
        self.logger.debug("conditional stop for service: %s", self.name)
        changed = None
        (return_code, _, _) = self.status()
        result = (0, "", "")
        if return_code == 0:
            result = self.stop()
            self.logger.info(
                "service %s found running, stopped with result: %s",
                self.name, result)
            self._status_log("stop", result)
            changed = "stop"
        elif return_code != 3:  # unknown/dead/hang...
            result = self.stop()
            self._status_log("stop", result)
            self.logger.info(
                "service %s found in dirty state: %s, stopped for cleaning"
                "with result: %s",
                self.name, return_code, result)
            changed = "stop"
        if changed and result[0] != 0:
            error_message = "error during service %s action %s: %s" % \
                            (self.name, changed, result, )
            self.logger.error(error_message)
            raise ServiceError(error_message, result)
        if changed and careful:
            t_max = time.time() + self._opts["timeout"]
            while time.time() <= t_max:
                result = self.status()
                if result[0] == 3:
                    return changed
                time.sleep(0.5)
            error_message = "error stopping service %s, expected return" \
                "code: 3, received: %s" % (self.name, result[0])
            self.logger.error(error_message)
            raise ServiceError(error_message, result)
        return changed

    def start(self):
        """
        This method takes care of starting the service using the
        start command.
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
                self.logger.info("service %s already stopped", self.name)
            else:
                pids = [x[0] for x in pid_info]
                kill_pids(pids, self._opts["timeout"])
                self.logger.info(
                    "%s killed by killing processes: %s",
                    self.name, " ".join([str(p) for p in pids]))
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
                self.logger.debug("%s not running", self.name)
                result = (3, "", "")
            else:
                self.logger.debug("%s running", self.name)
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
        if self.is_enabled():
            if status == 0:
                output = "%s: OK, running, as expected" % (self.name, )
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
        return check_status, [output, ]

    def restart(self):
        """
        This method takes care of restarting the service.

        If the service does not have a restart command the service will be
        restarted doing a *stop+start*.

        If the service does have a restart command this will be used in
        order to restart the service.
        """
        restart_cmd = True
        if self._opts["restart"] is None:
            restart_cmd = False
        if self._opts["restart"] == "stop+start":
            restart_cmd = False
        if restart_cmd:
            result = self.__execute(self.get_cmd("restart"))
            self.logger.info(
                "service %s restarted with result: %s", self.name, result)
            self._status_log("restart", result)
        else:
            stop_result = self.stop()
            start_result = self.start()
            result = merge_status(stop_result, start_result)
            self.logger.info(
                "service %s stop+start result: %s", self.name, result)
            self._status_log("stop+start", result)
        return result

    def pidof(self):
        """ Return the pid of the service. """
        pat_re = self._opts.get("pattern_re", None)
        if pat_re is not None:
            return pidof(pat_re)
        return None

    def _status_log(self, operation, output):
        """
        Log the operation output.
        """
        self._status.setdefault("log", list())
        self._status["log"].append({"time": time.time(),
                                    "operation": operation,
                                    "output": output})
        self._status["log"] = self._status["log"][-MAX_LOG_MESSAGES:]

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
        return "service %s" % (self.name, )

    def get_id(self):
        """
        Return the id of the service.
        :rtype : str the string representing the service
        """
        text_id = "%s|%s|%s" % (self.name,
                                self._opts["expected"],
                                " ".join(self.get_cmd("start")), )
        return md5_hash(text_id.encode()).hexdigest()

    def load_status(self, status):
        """
        Load the status from the previous run.
        """
        if status is None:
            return
        self._is_new = False
        self._status = status

    def dump_status(self):
        """
        Return the status to be saved for future runs.
        """
        # removing log for the time being
        if "log" in self._status:
            del(self._status["log"])
        return self._status
