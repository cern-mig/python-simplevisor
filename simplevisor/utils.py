"""
Common utilities used by :py:mod:`simplevisor` module.


Copyright (C) 2013 CERN
"""
import datetime
import os
import signal
from simplevisor.log import log_debug, log_error, log_warning
from subprocess import Popen, PIPE
import sys
import time
import traceback

try:
    import hashlib
    md5_hash = hashlib.md5
except ImportError:
    import md5
    md5_hash = md5.md5

try:
    import simplejson as json
except (SyntaxError, ImportError):
    import json
    try:
        getattr(json, "dumps")
    except AttributeError:
        raise ImportError("No available json module.")

CHECK_TIME = 0.05  # milliseconds

PY2 = sys.hexversion < 0x03000000
PY3 = not PY2


def read_apache_config(path):
    """
    Read Apache style config files.
    """
    if path is None:
        return None
    cmd = "perl -e 'use Config::General qw(ParseConfig);" + \
          "use JSON qw(to_json);print(to_json({ParseConfig(" + \
          "-ConfigFile => $ARGV[0], -InterPolateVars => 1)}))' %s" % (path, )
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = proc.communicate()
    if err:
        raise ValueError(err)
    data = json.loads(out)
    return data


def merge_status(main, other):
    """
    Merge two status tuples.
    """
    new_code = main[0] | other[0]
    new_out = "%s%s" % (main[1], other[1])
    new_err = "%s%s" % (main[2], other[2])
    return (new_code, new_out, new_err)


def print_nested_list(items, level=0, indent=2):
    """
    Print nested lists elements with indentation.
    """
    for item in items:
        if type(item) == list:
            print_nested_list(item, level + 1, indent)
        else:
            print("%s%s" % (level * indent * " ", item))


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
    if (type(sys.stdin) is not file):
        stdin = open(os.devnull, 'r')
        os.dup2(stdin.fileno(), sys.stdin.fileno())
    if (type(sys.stdout) is not file):
        sys.stdout.flush()
        stdout = open(os.devnull, 'a+')
        os.dup2(stdout.fileno(), sys.stdout.fileno())
    if (type(sys.stderr) is not file):
        sys.stderr.flush()
        stderr = open(os.devnull, 'a+')
        os.dup2(stderr.fileno(), sys.stderr.fileno())


#### PID helpers
class PIDError(Exception):
    """ PID related errors. """


def pid_read(path, action=False):
    """ Return the pid content. """
    content = (None, None)
    if not os.path.exists(path):
        if action:
            return ("", None)
        return ""
    try:
        pid_file = open(path, "r")
        pid_content = pid_file.readlines()
        if len(pid_content) == 1:
            content = (int(pid_content[0]), None)
        else:
            content = (int(pid_content[0]), pid_content[1].strip())
    except (IOError, ValueError):
        error = sys.exc_info()[1]
        raise IOError("cannot read pidfile %s: %s" % (path, error))
    else:
        pid_file.close()
    if action:
        return content
    return content[0]


def pid_touch(path):
    """ Touch the pid. """
    try:
        os.utime(path, None)
    except OSError:
        raise OSError("cannot utime pidfile %s" % path)
    else:
        return True


def pid_write(path, pid, action=None, excl=False):
    """ Write content to the pid. """
    try:
        if excl:
            mode = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        else:
            mode = os.O_WRONLY | os.O_CREAT
        pid_file = os.open(path, mode)
        content = "%s\n" % pid
        if action is not None:
            content += "%s\n" % action
        os.write(pid_file, content)
    except IOError:
        error = sys.exc_info()[1]
        raise IOError("cannot write to %s: %s" % (path, error.strerror))
    except OSError:
        error = sys.exc_info()[1]
        raise IOError("cannot open pidfile %s: %s" %
                      (path, error.strerror))
    else:
        os.close(pid_file)
        return pid
    return None


def pid_check(path):
    """ Check the pid content and return the action if present. """
    (pid, action) = pid_read(path, True)
    if pid is None:
        return
    if not pid:
        raise PIDError("lost or corrupted pid file: %s\n" % path)
    if pid != os.getpid():
        raise PIDError("pidfile has been taken by another pid: %s\n" % pid)
    if action is None:
        return ""
    return action


def pid_quit(path, program=""):
    """ Write quit to the pid. """
    pid = pid_read(path)
    if pid is None:
        return
    if pid:
        if program:
            print("%s (pid %d) is being told to quit..." %
                  (program, pid))
        if pid_write(path, pid, "quit") is None:
            return
        for _ in range(5):
            try:
                os.kill(pid, 0)
                time.sleep(1)
            except OSError:
                break
        try:
            os.kill(pid, 0)
            if program:
                print("%s (pid %d) is still running, killing it now...\n" %
                      (program, pid))
            signals = [signal.SIGTERM, signal.SIGINT,
                       signal.SIGQUIT, signal.SIGKILL]
            for sig in signals:
                try:
                    os.kill(pid, sig)
                except OSError:
                    log_warning("cannot kill(%d, %d)" % (pid, sig))
                try:
                    os.kill(pid, 0)
                except OSError:
                    break
                time.sleep(1)
            try:
                os.kill(pid, 0)
                raise PIDError("could not kill %d" % pid)
            except OSError:
                if program:
                    print("%s (pid %d) has been successfully killed\n" %
                          (program, pid))
        except OSError:
            if program:
                print("%s (pid %d) does not seem to be running anymore" %
                      (program, pid))
    elif program:
        print("%s does not seem to be running" % (program, ))
    if os.path.isfile(path):
        try:
            log_warning("removing pid file %s\n" % path)
            os.remove(path)
        except OSError:
            raise PIDError("failed to remove pid file: %s" % path)
    return pid


def pid_status(path, maxage=None):
    """ Return the pid status. """
    pid = pid_read(path)
    if pid is None:
        return (None, None)
    if not pid:
        return (3, "does not seem to be running")
    try:
        os.kill(pid, 0)
    except OSError:
        return (3, "pid %s does not seem to be running anymore" % pid)
    if maxage is None:
        return (0, "seems to be running")
    try:
        stat = os.stat(path)
    except OSError:
        return (3, "(pid %d) does not have its pidfile anymore" % pid)
    fileage = time.time() - stat.st_mtime
    mdate = datetime.datetime.fromtimestamp(stat.st_mtime)
    if fileage > maxage:
        return (1, "(pid %d) is not running since %s" % (pid, mdate))
    return (0, "(pid %d) was active on %s" % (pid, mdate))


def pid_remove(path):
    """ Remove the pidfile. """
    pid = pid_read(path)
    if pid is None:
        return
    if os.getpid() != pid:
        return
    try:
        os.remove(path)
    except OSError:
        error = sys.exc_info()[1]
        raise OSError("cannot remove pidfile %s: %s" % (path, error))
    else:
        return pid


def print_only_exception_error():
    """
    Print only exception error message.
    """
    def out_function(in_function):
        """ Wrap function. """
        def out_function(*args, **kwargs):
            """ Wrapping and catching exceptions. """
            __name__ = in_function.__name__
            try:
                in_function(*args, **kwargs)
            except SystemExit:
                raise sys.exc_info()[1]
            except Exception:
                (_, error, error_tb) = sys.exc_info()
                print("%s" % (error,))
                sys.exit(1)
        return out_function
    return out_function


def log_exceptions(re_raise=True):
    """
    Log exceptions to configured log and re raise the exception or exit.
    """
    def out_function(in_function):
        """ Wrap function. """
        def out_function(*args, **kwargs):
            """ Wrapping and catching exceptions. """
            __name__ = in_function.__name__
            try:
                in_function(*args, **kwargs)
            except SystemExit:
                raise sys.exc_info()[1]
            except Exception:
                (_, error, error_tb) = sys.exc_info()
                log_debug("%s" % (" ".join(traceback.format_tb(error_tb)),))
                log_error("%s" % (error,))
                if re_raise:
                    raise error
                else:
                    sys.exit(1)
        return out_function
    return out_function


def unify_keys(dictionary):
    """
    Unify dictionary's keys, if they are unicode transform them to strings.
    This is for interoperability with old versions of Python.
    """
    if type(dictionary) is not dict:
        return dictionary
    for element in dictionary:
        if PY2 and type(element) is not str:
            value = dictionary.pop(element)
            dictionary[str(element)] = value
        elif PY3 and type(element) is bytes:
            value = dictionary.pop(element)
            dictionary[element.decode()] = value
        tmp = dictionary.get(element)
        if type(tmp) is dict:
            unify_keys(tmp)
    return dictionary


def get_int_or_die(value, message=None):
    """
    Return the integer value or die with the error message provided.
    """
    if type(value) == int:
        return value
    try:
        value = int(value)
    except ValueError:
        if message is None:
            raise sys.exc_info()[1]
        else:
            raise ValueError(message)
    return value
