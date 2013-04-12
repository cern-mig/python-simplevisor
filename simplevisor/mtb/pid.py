"""
Pid file utilities for :py:mod:`mtb` module.


Copyright (C) 2013 CERN
"""
import datetime
import logging
import os
import signal
import sys
import time

LOGGER = logging.getLogger("mtb.pid")


#### PID helpers
class PIDError(Exception):
    """ PID related errors. """


def pid_read(path, action=False):
    """ Return the pid content. """
    content = (None, None)
    if not os.path.exists(path):
        if action:
            return "", None
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
        # int('0666', 8) is for compatibility with python2.4
        # which support only octal with the form 0666
        # since python 2.6 0o666 must be used
        pid_file = os.open(path, mode, int('0666', 8))
        content = "%s\n" % pid
        if action is not None:
            content += "%s\n" % action
        os.write(pid_file, content)
    except IOError:
        error = sys.exc_info()[1]
        raise IOError("cannot write to %s: %s" % (path, error.strerror))
    except OSError:
        error = sys.exc_info()[1]
        raise IOError("cannot open pidfile %s: %s" % (path, error.strerror))
    else:
        os.close(pid_file)
        return pid


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
                    LOGGER.warning("cannot kill(%d, %d)" % (pid, sig))
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
            LOGGER.warning("removing pid file %s\n" % path)
            os.remove(path)
        except OSError:
            raise PIDError("failed to remove pid file: %s" % path)
    return pid


def pid_status(path, maxage=None):
    """ Return the pid status. """
    pid = pid_read(path)
    if pid is None:
        return None, None
    if not pid:
        return 3, "does not seem to be running"
    try:
        os.kill(pid, 0)
    except OSError:
        return 3, "pid %s does not seem to be running anymore" % (pid, )
    if maxage is None:
        return 0, "seems to be running"
    try:
        stat = os.stat(path)
    except OSError:
        return 3, "(pid %d) does not have its pidfile anymore" % (pid, )
    fileage = time.time() - stat.st_mtime
    mdate = datetime.datetime.fromtimestamp(stat.st_mtime)
    if fileage > maxage:
        return 1, "(pid %d) is not running since %s" % (pid, mdate)
    return 0, "(pid %d) was active on %s" % (pid, mdate)


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
