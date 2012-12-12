"""
Simplevisor module.


Copyright (C) 2012 CERN
"""
import os
import signal
import sys
import time
try:
    import json
except ImportError:
    import simplejson as json

from simplevisor.errors import ConfigurationError
from simplevisor.log import get_log
import simplevisor.log as log
from simplevisor.supervisor import Supervisor
from simplevisor.service import Service
from simplevisor import service, supervisor
import simplevisor.utils as utils
from simplevisor.utils import pid_check, pid_quit, pid_read, pid_remove, \
    pid_status, pid_touch, pid_write

import pprint
PP = pprint.PrettyPrinter(indent=2)

SERVICE_COMMAND = ["start", "stop", "status", "check", "restart"]
NORMAL_COMMAND = list(SERVICE_COMMAND)
NORMAL_COMMAND.remove("restart")
NORMAL_COMMAND.extend(["single", "stop_supervisor", "stop_children",
                       "configuration_check"])


class Simplevisor(object):
    """ Simplevisor class. """
    prog = "simplevisor"

    def __init__(self, config=dict(), entry_config=None):
        """ Initialize Simplevisor. """
        if type(config) != dict:
            raise ConfigurationError("Simplevisor expect a dictionary.")
        if entry_config is None:
            raise ConfigurationError("Simplevisor expect at least one entry.")
        elif type(entry_config) == list:
            raise ConfigurationError("Simplevisor expect a single entry.")
        self.config = config
        self.status_file = self.config.get("store")
        self.entry_config = entry_config
        self.running = False
        self.child = supervisor.new_child(self.entry_config)

    def get_child(self, path=""):
        """ Return child by its path. """
        path_list = path.split("/")
        first = path_list.pop(0)
        if not first:
            return self.child
        if self.child.name == first:
            if not path_list:
                return self.child
            try:
                return self.child.get_child(path_list)
            except StandardError:
                pass
        raise ValueError("given path is invalid: %s" % path)

    @utils.log_exceptions(re_raise=False)
    def work(self):
        """ Controller. """
        command = self.config.get("command", "status")
        path = self.config.get("path", None)
        if path is None and isinstance(self.child, Supervisor):
            self.initialize_log(stdout=True)
            self.load_status()
            action = getattr(self, command)
            action()
            return
        if command not in SERVICE_COMMAND:
            raise ValueError("command must be one of: %s" %
                             ", ".join(SERVICE_COMMAND))
        self.initialize_log(stdout=True)
        if isinstance(self.child, Service):
            target = self.child
        else:
            # command service at path
            target = self.get_child(path)
            if target is None:
                raise ValueError("element at path not found: %s" %
                                 (path, ))
        if command == "check":
            self.check(target)
        else:
            log.LOG.debug("calling %s.%s" % (target.name, command))
            (return_code, out, err) = getattr(target, command)()
            if len(out.strip()) > 0:
                print("stdout: %s" % out.strip())
            if len(err.strip()) > 0:
                print("stderr: %s" % err.strip())
            sys.exit(return_code)

    def configuration_check(self):
        """ Check only the configuration. """
        # so far so good
        print("Configuration is valid.")
        sys.exit(0)

    def on_signal(self, signum, _):
        """ Handle signals. """
        if signum == signal.SIGINT:
            log.LOG.info("caught SIGINT")
            self.running = False
        elif signum == signal.SIGTERM:
            log.LOG.info("caught SIGTERM")
            self.running = False
        elif signum == signal.SIGHUP:
            log.LOG.info("caught SIGHUP, ignoring it")

    def start(self):
        """ Do start action. """
        signal.signal(signal.SIGINT, self.on_signal)
        signal.signal(signal.SIGTERM, self.on_signal)
        signal.signal(signal.SIGHUP, self.on_signal)
        self.pre_run()
        self.initialize_log()
        if self.config.get("daemon"):
            utils.daemonize()
        if self.config.get("pidfile"):
            pid_write(self.config["pidfile"], os.getpid(), excl=True)
        self.run()
        if self.config.get("pidfile"):
            pid_remove(self.config.get("pidfile"))

    def single(self):
        """ Do single action. """
        if self.config.get("pidfile"):
            pid_write(self.config["pidfile"], os.getpid(), excl=True)
        self.pre_run()
        self.run()
        if self.config.get("pidfile"):
            pid_remove(self.config.get("pidfile"))

    def stop(self, action="quit"):
        """ Quit the process. """
        if not self.config.get("pidfile"):
            raise ConfigurationError("%s requires a pidfile" % action)
        pid = pid_read(self.config["pidfile"])
        timeout = 10
        if pid and timeout is not None:
            print("%s (pid %d) is being told to %s..." %
                  (self.prog, pid, action))
            pid_write(self.config["pidfile"], pid, action)
            while timeout >= 0:
                try:
                    os.kill(pid, 0)
                except OSError:
                    break
                timeout -= 1
                time.sleep(1)
            try:
                os.kill(pid, 0)
            except OSError:
                print("%s (pid %d) does not seem to be running anymore" %
                      (self.prog, pid))
                sys.exit(0)
        pid_quit(self.config["pidfile"], self.prog)
        sys.exit(0)

    def stop_supervisor(self):
        """ Tell the supervisor to stop without touching the children. """
        self.stop("stop_supervisor")

    def stop_children(self):
        """ Tell the supervisor to stop without touching the children. """
        if not self.config.get("pidfile"):
            raise ConfigurationError("status requires a pidfile")
        self.send_action("stop_children")

    def send_action(self, action="stop_children"):
        """ Tell the supervsisor to execute an action. """
        if not self.config.get("pidfile"):
            raise ConfigurationError("%s requires a pidfile" % action)
        pid = pid_read(self.config["pidfile"])
        if pid:
            print("%s (pid %d) is being told to %s..." %
                  (self.prog, pid, action))
            pid_write(self.config["pidfile"], pid, action)
        elif pid is not None:
            print("%s does not seem to be running anymore" %
                  (self.prog, ))

    def restart(self):
        """ Restart not accepted. """
        raise ConfigurationError(
            "restart command is accepted only with a path")

    def check(self, child=None):
        """
        Confront the expected status with the real status of
        the children aggregating them and return code associated
        with the state.

        0 if everything is fine.

        1 if status is unexpected.
        """
        child = child or self.child
        (child_status, output) = child.check()
        utils.print_nested_list(output, level=0, indent=2)
        if child_status:
            sys.exit(0)
        else:
            sys.exit(1)

    def status(self):
        """ Do status action. """
        if not self.config.get("pidfile"):
            raise ConfigurationError("status requires a pidfile")
        (status, message) = pid_status(self.config["pidfile"], 60)
        print("%s %s" % (status, message))
        sys.exit(status)

    def initialize_log(self, stdout=False):
        """ Initialize the log.LOG. """
        if stdout:
            log.LOG = get_log("print")("simplevisor", **self.config)
        else:
            log.LOG = get_log(self.config.get("log", "print"))("simplevisor",
                                                               **self.config)

    def load_status(self):
        """ Load saved status. """
        if self.status_file is not None:
            old_status = self.read_status()
            if old_status is not None:
                self.child.load_status(
                    old_status.get(self.child.get_id(), None))

    def read_status(self):
        """ Read the status from the specified file. """
        try:
            tmp_file = open(self.status_file, "r")
            try:
                status = json.load(tmp_file)
            except ValueError:
                msg = "Status file not valid: %s" % self.status_file
                raise ConfigurationError(msg)
            else:
                tmp_file.close()
                return status
        except IOError:
            # log.LOG.info("status file not found, continuing.")
            pass

    def save_status(self):
        """ Save the status in the specified file. """
        if self.status_file is None:
            log.LOG.info("status file not specified")
            return
        try:
            log.LOG.debug("status file: %s" % self.status_file)
            staus_f = open(self.status_file, "w")
            try:
                status = {self.child.get_id(): self.child.dump_status()}
                json.dump(status, staus_f)
                log.LOG.debug("status saved: %s" % status)
            except StandardError:
                error_type, error, _ = sys.exc_info()
                msg = "error writing status file %s: %s - %s" % \
                      (self.status_file, error_type, error)
                log.LOG.error(msg)
                raise ConfigurationError(msg)
            staus_f.close()
        except IOError:
            error = sys.exc_info()[1]
            msg = "error writing to status file %s: %s" % \
                  (self.status_file, error)
            log.LOG.error(msg)
            raise IOError(msg)

    def sleep_interval(self, default=60):
        """ Return the interval between every supervision run. """
        if type(self.config.get("interval", default)) != int:
            try:
                self.config["interval"] = int(self.config.get("interval",
                                                              default))
            except ValueError:
                msg = "interval must be an integer"
                log.LOG.error(msg)
                raise ValueError(msg)
        return self.config.get("interval", default)

    def pre_run(self):
        """ Before detaching. """
        if isinstance(self.child, service.Service):
            (rcode, _, _) = self.child.start()
            sys.exit(rcode)
        self.child.adjust()
        log.LOG.debug("all elements adjusted")

    def run(self):
        """ Coordinate the job. """
        log.LOG.info("supervisor started")
        self.running = True
        action = None
        while self.running:
            self.child.supervise()
            log.LOG.debug("supervised")
            self.save_status()
            if self.config.get("command") == "single":
                log.LOG.debug("single mode, exiting")
                return
            wake_time = self.sleep_interval() + time.time()
            log.LOG.debug("sleeping for %d seconds" % self.sleep_interval())
            while wake_time >= time.time():
                if self.config.get("pidfile"):
                    pid_touch(self.config["pidfile"])
                    action = pid_check(self.config["pidfile"])
                    if action in ["quit", "stop_supervisor"]:
                        log.LOG.info("asked to %s" % action)
                        self.running = False
                        break
                    elif action == "stop_children":
                        log.LOG.info("stopping all the children")
                        self.child.stop()
                        pid_write(self.config["pidfile"], os.getpid())
                    elif action != "":
                        log.LOG.warning("unknown action: %s" % action)
                if not self.running:
                    break
                time.sleep(0.2)
        if action != "stop_supervisor":
            log.LOG.info("stopping all the children")
            self.child.stop()
        log.LOG.info("stopping the supervisor")
        self.save_status()
