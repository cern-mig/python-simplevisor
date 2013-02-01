"""
Process utilities for :py:mod:`mtb` module.


Copyright (C) 2013 CERN
"""
import os
import signal
from subprocess import Popen, PIPE
import sys
import time

from mtb.file import is_regular_file


CHECK_TIME = 0.05  # milliseconds


def merge_status(main, other):
    """
    Merge two status tuples.
    """
    new_code = main[0] | other[0]
    new_out = "%s%s" % (main[1], other[1])
    new_err = "%s%s" % (main[2], other[2])
    return (new_code, new_out, new_err)


def pidof(pattern_re):
    """
    Given a compiled :py:mod:`re` return a tuple containing the *pid* and
    the *command line* of the process matching it.

    If multiple processes match the pattern a list of tuple containing
    the *pid* and the *command line* is returned.
    """
    pids = [pid for pid in os.listdir("/proc") if pid.isdigit()]
    pids_info = list()
    for pid in pids:
        try:
            pid_f = open(os.path.join("/proc", pid, "cmdline"), "r")
            cmd_line = pid_f.read().replace('\x00', ' ')
            pid_f.close()
        except IOError:
            continue
        if pattern_re.search(cmd_line):
            pids_info.append((int(pid), cmd_line))
    if pids_info:
        return pids_info
    else:
        return None


def kill_pids(pids, timeout=5):
    """
    Kill the pids in the list.

    It will first send a SIGTERM to all the given *pids*, if the timeout
    expires and processes are still running they are killed with a
    brutal SIGKILL.
    """
    tpids = list(pids)
    tmax = time.time() + timeout
    while time.time() < tmax and tpids:
        for pid in tpids:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                # process already gone
                tpids.remove(pid)
        time.sleep(0.005)
    if not tpids:
        # good, all processes terminated
        return
    for pid in tpids:
        try:
            # brutally killing it
            os.kill(pid, signal.SIGKILL)
        except OSError:
            # process already gone
            pass


class ProcessTimedout(Exception):
    """
    Raised if a process timeout.
    """


class ProcessError(Exception):
    """
    Raised if a process fail.
    """


def timed_process(args, timeout=None, env=None):
    """
    Execute a command using :py:mod:`subprocess` module,
    if timeout is specified the process is killed if it does
    not terminate in the maxim required time.

    Parameters:

    args
        the command to run, in a list format

    timeout
        the maximumt time to wait for the process to terminate
        before killing it

    env
        a dictionary representing the environment
    """
    if env is None:
        env = {"PATH": "/usr/bin:/usr/sbin:/bin:/sbin"}
    try:
        proc = Popen(args, stdout=PIPE, stderr=PIPE, shell=False,
                     env=env)
    except OSError:
        error = sys.exc_info()[1]
        raise ProcessError("OSError %s" % error)
    except ValueError:
        error = sys.exc_info()[1]
        raise ProcessError("ValueError %s" % error)
    if timeout is None:
        out, err = proc.communicate()
        return (proc.poll(), out, err)
    maxt = time.time() + timeout
    while proc.poll() is None and time.time() < maxt:
        time.sleep(CHECK_TIME)
    if proc.poll() is None:
        try:
            getattr(proc, "send_signal")
            proc.send_signal(signal.SIGKILL)
        except AttributeError:
            try:
                os.kill(proc.pid, signal.SIGKILL)
            except OSError:  # process already gone
                pass
        raise ProcessTimedout("Process %s timed out after %s seconds." %
                              (" ".join(args), timeout))
    else:
        out, err = proc.communicate()
        return (proc.poll(), out, err)


def send_signal(daemon, sig):
    """ Send a signal to the pid of the given daemon. """
    pid = daemon.readpid()
    if pid is None:
        return
    try:
        os.kill(pid, sig)
    except OSError:
        error = str(sys.exc_info()[1])
        if error.find("No such process") > 0:
            if os.path.exists(daemon.pidfile):
                os.remove(daemon.pidfile)
        else:
            print(str(error))
            sys.exit(1)


#### Daemon helper
def daemonize():
    """ Daemonize. UNIX double fork mechanism. """
    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
            sys.exit(0)
    except OSError:
        error = sys.exc_info()[1]
        sys.stderr.write("fork #1 failed: %d (%s)\n"
                         % (error.errno, error.strerror))
        sys.exit(1)
    # decouple from parent environment
    os.chdir('/')
    os.setsid()
    # do second fork
    try:
        pid = os.fork()
        if pid > 0:
            # exit from second parent
            sys.exit(0)
    except OSError:
        error = sys.exc_info()[1]
        sys.stderr.write("fork #2 failed: %d (%s)\n"
                         % (error.errno, error.strerror))
        sys.exit(1)
    if (not is_regular_file(sys.stdin)):
        stdin = open(os.devnull, 'r')
        os.dup2(stdin.fileno(), sys.stdin.fileno())
    if (not is_regular_file(sys.stdout)):
        sys.stdout.flush()
        stdout = open(os.devnull, 'a+')
        os.dup2(stdout.fileno(), sys.stdout.fileno())
    if (not is_regular_file(sys.stderr)):
        sys.stderr.flush()
        stderr = open(os.devnull, 'a+')
        os.dup2(stderr.fileno(), sys.stderr.fileno())
