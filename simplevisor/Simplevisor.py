"""
Simplevisor module.


Copyright (C) 2013-2016 CERN
"""
import logging
import os
import signal
import sys
import time

import mtb.log as log
import mtb.pid
from mtb.pid import \
    pid_check, pid_quit, pid_read, pid_remove, \
    pid_status, pid_touch, pid_write
from mtb.prnt import print_nested_list
from mtb.proc import daemonize
from mtb.modules import json
from mtb.validation import get_int_or_die

from simplevisor.errors import SimplevisorError
from simplevisor.supervisor import Supervisor
from simplevisor import service, supervisor


QUICK_COMMANDS = ["status", "stop", "stop_supervisor", "stop_children",
                  "wake_up"]
SERVICE_COMMANDS = ["start", "stop", "status", "check", "restart"]
OTHER_COMMANDS = ["single", "check_configuration", "restart_child"]

DEFAULT_INTERVAL = 60


class Simplevisor(object):
    """ Simplevisor class. """
    prog = "simplevisor"

    def __init__(self, config=None, child_config=None):
        """ Initialize Simplevisor. """
        if config is None:
            config = dict()
        elif type(config) != dict:
            raise SimplevisorError("Simplevisor config is not a dictionary")
        if "logname" not in config:
            config["logname"] = self.__class__.__name__
        self.logger = logging.getLogger(config["logname"])
        mtb.pid.LOGGER = self.logger
        self._config = config
        self._status_file = self._config.get("store")
        self._running = False
        if child_config is None:
            self._child = None
        else:
            if "logname" not in child_config:
                child_config["logname"] = config["logname"]
            self._child = supervisor.new_child(child_config)

    def get_child(self, path=""):
        """ Return child by its path. """
        path_list = path.split("/")
        first = path_list.pop(0)
        if not first:
            return self._child
        if self._child.name == first:
            if not path_list:
                return self._child
            try:
                return self._child.get_child(path_list)
            except StandardError:
                pass
        raise ValueError("given path is invalid: %s" % path)

    @log.print_only_exception_error()
    def work(self):
        """ Controller. """
        command = self._config.get("command", "status")
        path = self._config.get("path", None)
        if path is not None and command == "restart_child":
            self.send_action(command + " " + path)
            return
        if path is None and command in QUICK_COMMANDS:
            getattr(self, command)()
            return
        if self._child is None:
            raise SimplevisorError("no entry found")
        if path is None and isinstance(self._child, Supervisor):
            if command != "check_configuration":
                self.load_status()
            getattr(self, command)()
            return
        if command not in SERVICE_COMMANDS:
            raise ValueError("command must be one of: %s" %
                             ", ".join(SERVICE_COMMANDS))
        if path is None:
            target = self._child
        else:
            target = self.get_child(path)
        if command == "check":
            self.check(target)
            return
        self.logger.debug("calling %s.%s", target.name, command)
        (return_code, out, err) = getattr(target, command)()
        if len(out.strip()) > 0:
            print("stdout: %s" % (out.strip(), ))
        if len(err.strip()) > 0:
            print("stderr: %s" % (err.strip(), ))
        sys.exit(return_code)

    def check_configuration(self):
        """ Only check the configuration. """
        # so far so good
        print("the configuration file is valid")
        sys.exit(0)

    def on_signal(self, signum, _):
        """ Handle signals. """
        if signum == signal.SIGINT:
            self.logger.info("caught SIGINT")
            self._running = False
        elif signum == signal.SIGTERM:
            self.logger.info("caught SIGTERM")
            self._running = False
        elif signum == signal.SIGHUP:
            self.logger.info("caught SIGHUP, ignoring it")

    def start(self):
        """ Do start action. """
        signal.signal(signal.SIGINT, self.on_signal)
        signal.signal(signal.SIGTERM, self.on_signal)
        signal.signal(signal.SIGHUP, self.on_signal)
        self.pre_run()
        if self._config.get("daemon"):
            daemonize()
            run_function = log.log_exceptions(
                logger_name=self.prog,
                re_raise=False)(self.run)
        else:
            run_function = log.log_exceptions(
                logger_name=self.prog,
                re_raise=True)(self.run)
        if self._config.get("pidfile"):
            pid_write(self._config["pidfile"], os.getpid(), excl=True)
        try:
            run_function()
        except:
            self.save_status()
            if self._config.get("pidfile"):
                pid_remove(self._config.get("pidfile"))
            raise sys.exc_info()[1]
        if self._config.get("pidfile"):
            pid_remove(self._config.get("pidfile"))

    def single(self):
        """ Do single action. """
        if self._config.get("pidfile"):
            pid_write(self._config["pidfile"], os.getpid(), excl=True)
        self.pre_run()
        self.supervise()
        self.save_status()
        if self._config.get("pidfile"):
            pid_remove(self._config.get("pidfile"))

    def stop(self, action="quit"):
        """ Quit the process. """
        if not self._config.get("pidfile"):
            raise SimplevisorError("%s requires a pidfile" % action)
        pid = pid_read(self._config["pidfile"])
        timeout = 10
        if pid and timeout is not None:
            print("%s (pid %d) is being told to %s..." %
                  (self.prog, pid, action))
            pid_write(self._config["pidfile"], pid, action)
            while timeout >= 0:
                try:
                    os.kill(pid, 0)
                except OSError:
                    break
                timeout -= 1
                time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except OSError:
                print("%s (pid %d) does not seem to be running anymore" %
                      (self.prog, pid))
                sys.exit(0)
        pid_quit(self._config["pidfile"], self.prog)
        sys.exit(0)

    def stop_supervisor(self):
        """ Tell the supervisor to stop without touching the children. """
        self.stop("stop_supervisor")

    def stop_children(self):
        """ Tell the supervisor to stop the children. """
        self.send_action("stop_children")

    def wake_up(self):
        """ Tell the supervisor to wake up. """
        self.send_action("wake_up")

    def send_action(self, action):
        """ Tell the supervisor to execute an action. """
        if not self._config.get("pidfile"):
            raise SimplevisorError("action %s requires a pidfile" % action)
        pid = pid_read(self._config["pidfile"])
        if pid:
            print("%s (pid %d) is being told to %s..." %
                  (self.prog, pid, action))
            pid_write(self._config["pidfile"], pid, action)
        elif pid is not None:
            print("%s does not seem to be running anymore" %
                  (self.prog, ))

    def restart(self):
        """ Restart not accepted. """
        raise SimplevisorError(
            "restart command is accepted only with a path")

    def check(self, child=None):
        """
        Confront the expected status with the real status of
        the children aggregating them and return code associated
        with the state.

        0 if everything is fine.

        1 if status is unexpected.
        """
        child = child or self._child
        (child_status, output) = child.check()
        print_nested_list(output, level=0, indent=2)
        if child_status:
            sys.exit(0)
        else:
            sys.exit(1)

    def status(self):
        """ Execute status command. """
        if not self._config.get("pidfile"):
            raise SimplevisorError("status requires a pidfile")
        (status, message) = pid_status(self._config["pidfile"], 60)
        print("%s" % (message, ))
        sys.exit(status)

    def load_status(self):
        """ Load saved status. """
        if self._status_file is not None:
            old_status = self.read_status()
            if old_status is not None:
                self._child.load_status(
                    old_status.get(self._child.get_id(), None))

    def read_status(self):
        """ Read the status from the specified file. """
        try:
            tmp_file = open(self._status_file, "r")
            try:
                status = json.load(tmp_file)
            except ValueError:
                raise SimplevisorError(
                    "Status file not valid: %s" % (self._status_file, ))
            else:
                tmp_file.close()
                return status
        except IOError:
            # self.logger.info("status file not found, continuing.")
            pass

    def save_status(self):
        """ Save the status in the specified file. """
        if self._status_file is None:
            return
        try:
            self.logger.debug("status file: %s", self._status_file)
            status_f = open(self._status_file, "w")
            try:
                status = {self._child.get_id(): self._child.dump_status()}
                json.dump(status, status_f)
                self.logger.debug("status saved: %s", status)
            except StandardError:
                error_type, error, _ = sys.exc_info()
                msg = "error writing status file %s: %s - %s" % \
                      (self._status_file, error_type, error)
                self.logger.error(msg)
                raise SimplevisorError(msg)
            status_f.close()
        except IOError:
            error = sys.exc_info()[1]
            msg = "error writing to status file %s: %s" % \
                  (self._status_file, error)
            self.logger.error(msg)
            raise IOError(msg)

    def sleep_interval(self):
        """ Return the interval between every supervision cycle. """
        value = self._config.get("interval", DEFAULT_INTERVAL)
        result = get_int_or_die(
            value,
            "interval value must be an integer: %s" % (value, ))
        return result

    def pre_run(self):
        """ Before detaching. """
        if isinstance(self._child, service.Service):
            (rcode, _, _) = self._child.start()
            sys.exit(rcode)
        self._child.start()

    def supervise(self):
        """
        Supervise method helper.
        """
        result = {
            'ok': 0,
            'adjusted': 0,
            'failed': 0, }
        t_start = time.time()
        successful = self._child.supervise(result)
        t_end = time.time()
        if successful:
            self.logger.info(
                "supervision cycle executed successfully in %.3fs: "
                "%s services OK, %s services needed adjustment, "
                "%s services failed adjustment",
                t_end - t_start,
                result.get("ok", "unknown"),
                result.get("adjusted", "unknown"),
                result.get("failed", "unknown"))
        else:
            raise SimplevisorError("supervision interrupted/failed")

    def run(self):
        """ Coordinate the job. """
        self.logger.info("started")
        self._running = True
        action = None
        while self._running:
            self.supervise()
            self.save_status()
            wake_time = self.sleep_interval() + time.time()
            self.logger.debug(
                "sleeping for %d seconds", self.sleep_interval())
            while wake_time >= time.time():
                if self._config.get("pidfile"):
                    pid_touch(self._config["pidfile"])
                    action = pid_check(self._config["pidfile"])
                    if action != "":
                        self.logger.info("asked to %s", action)
                        pid_write(self._config["pidfile"], os.getpid())
                    if action in ["quit", "stop_supervisor"]:
                        self._running = False
                    elif action == "stop_children":
                        self._child.stop()
                    elif action == "wake_up":
                        break
                    elif action[:14] == "restart_child ":
                        target = self.get_child(action[14:])
                        target.restart()
                    elif action != "":
                        self.logger.warning("unknown action: %s", action)
                if not self._running:
                    break
                time.sleep(0.5)
        if action != "stop_supervisor":
            self.logger.info("stopping all the children")
            self._child.stop()
        self.logger.info("stopping")
        self.save_status()
        self.logger.info("stopped")
