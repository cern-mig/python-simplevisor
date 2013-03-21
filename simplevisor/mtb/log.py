"""
Logging utilities used by :py:mod:`mtb` module.

Three unified log classes to manage in a coherent way logs
between different logging systems:

null
    log black hole, it simply discard log messages

syslog
    log standard messages to
    :py:mod:`syslog`: http://en.wikipedia.org/wiki/Syslog

file
    use standard Python :py:mod:`logging` customizable to log to a file

stdout
    print log messages on the standard output, works only if not daemonized


Copyright (C) 2013 CERN
"""
import datetime
import logging
import sys
import syslog
import traceback


class SysLog(object):
    """
    Class which logs with :py:mod:`syslog`

    Parameters:

    name
        the name of the logger
    """
    level = {'debug': syslog.LOG_DEBUG,
             'info': syslog.LOG_INFO,
             'warning': syslog.LOG_WARNING,
             'error': syslog.LOG_ERR,
             'critical': syslog.LOG_CRIT,
             }

    def __init__(self, name, **kwargs):
        """ Initialize syslog logging. """
        self.level_threshold = self.level.get(
            kwargs.get('loglevel', 'warning'), syslog.LOG_WARNING)
        syslog.openlog("%s" % (name, ),
                       syslog.LOG_PID,
                       syslog.LOG_DAEMON)

    def _log(self, criticality, message):
        """ Filter. """
        if self.level_threshold >= self.level[criticality]:
            syslog.syslog(self.level[criticality], "[%s] %s" %
                          (criticality.upper(), message))

    def debug(self, message):
        """ Log a debug message. """
        self._log('debug', message)

    def info(self, message):
        """ Log an info message. """
        self._log('info', message)

    def warning(self, message):
        """ Log a warning message. """
        self._log('warning', message)

    def error(self, message):
        """ Log an error message. """
        self._log('error', message)

    def critical(self, message):
        """ Log a critical message. """
        self._log('critical', message)


class FileLog(object):
    """
    Class which logs with Python standard :py:mod:`logging`.

    Parameters:

    name
        the name of the logger

    logfile
        the file where to log

    loglevel
        the logging level
    """
    level = {'debug': logging.DEBUG,
             'info': logging.INFO,
             'warning': logging.WARN,
             'error': logging.ERROR,
             'critical': logging.CRITICAL,
             }

    def __init__(self, name, **kwargs):
        """ Initialize standard logging. """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(
            self.level.get(kwargs.get('loglevel', 'warning'),
                           self.level['warning']))
        custom_format = logging.Formatter(
            '%(asctime)s - %(name)s:%(lineno)s -' +
            ' %(levelname)s [%(process)d] %(message)s ')
        if kwargs.get('logfile') is not None:
            file_hdlr = logging.FileHandler(filename=kwargs.get('logfile'), )
            file_hdlr.setFormatter(custom_format)
            self.logger.addHandler(file_hdlr)

    def debug(self, message):
        """ Log a debug message. """
        self.logger.debug(message)

    def info(self, message):
        """ Log an info message. """
        self.logger.info(message)

    def warning(self, message):
        """ Log a warning message. """
        self.logger.warning(message)

    def error(self, message):
        """ Log an error message. """
        self.logger.error(message)

    def critical(self, message):
        """ Log a critical message. """
        self.logger.critical(message)


class StdOutLog(object):
    """
    Class which logs on standard output.

    Parameters:

    name
        the name of the logger

    loglevel
        the logging level
    """
    level = {'debug': 4,
             'info': 3,
             'warning': 2,
             'error': 1,
             'critical': 0,
             }

    def __init__(self, name, **kwargs):
        """ Initialize stdout logging. """
        self.level_threshold = self.level.get(
            kwargs.get('loglevel', 'warning'), 2)
        self.name = name

    def debug(self, message):
        """ Log a debug message. """
        self._print('debug', message)

    def info(self, message):
        """ Log an info message. """
        self._print('info', message)

    def warning(self, message):
        """ Log a warning message. """
        self._print('warning', message)

    def error(self, message):
        """ Log an error message. """
        self._print('error', message)

    def critical(self, message):
        """ Log a critical message. """
        self._print('critical', message)

    def _print(self, criticality, message):
        """ Custom print. """
        if self.level_threshold >= self.level[criticality]:
            print("%s - %s: %s" % (
                  datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                  criticality.upper(), message))


class NullLog(object):
    """
    Class which log on a black hole.

    Parameters:

    name
        the name of the logger

    loglevel
        the logging level
    """

    def __init__(self, name, **kwargs):
        """ Initialize stdout logging. """

    def debug(self, message):
        """ Log a debug message. """

    def info(self, message):
        """ Log an info message. """

    def warning(self, message):
        """ Log a warning message. """

    def error(self, message):
        """ Log an error message. """

    def critical(self, message):
        """ Log a critical message. """

    def _print(self, criticality, message):
        """ Custom print. """


class LogSystemNotSupported(Exception):
    """ Raised when a log system which is not supported is specified. """


def get_log(type_t):
    """
    Return the class representing the *type* of log required.
    """
    try:
        log = LOG_SYSTEM[type_t]
    except KeyError:
        raise LogSystemNotSupported(
            "%s is not valid as log system, must be one of: %s" %
            (type_t, ", ".join(LOG_SYSTEM.keys()), ))
    else:
        return log


def set_log(new_log):
    """ Set LOG to provided log system. """
    global LOG
    LOG = new_log


def log_debug(message):
    """ Log a debug message on LOG. """
    LOG.debug(message)


def log_warning(message):
    """ Log a warning message on LOG. """
    LOG.warning(message)


def log_error(message):
    """ Log an error message on LOG. """
    LOG.error(message)


LOG_SYSTEM = {"null": NullLog,
              "stdout": StdOutLog,
              "file": FileLog,
              "syslog": SysLog, }
LOG = StdOutLog("stdout")


################################ Useful decorators for logging

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
                # (_, error, error traceback)
                (_, error, _) = sys.exc_info()
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
