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
import logging
from logging.handlers import SysLogHandler
import sys
import traceback


class CustomNullHandler(logging.Handler):
    """ Custom and easy null handler for python prior to 2.6. """
    def emit(self, record):
        pass

if not hasattr(logging, "NullHandler"):
    setattr(logging, "NullHandler", CustomNullHandler)


LOG_SYSTEMS = {
    'null': {'handler': logging.NullHandler, },
    'stdout': {
        'handler': logging.StreamHandler,
        'handler_options': {
            'args': [sys.stdout, ],
        },
        'formatter': logging.Formatter,
        'formatter_options': {
            'fmt': '%(asctime)s %(name)s[%(process)d]: '
                   '[%(levelname)s] %(message)s',
        },
    },
    'file': {
        'handler': logging.FileHandler,
        'formatter': logging.Formatter,
        'formatter_options': {
            'fmt': '%(asctime)s %(name)s[%(process)d]: '
                   '[%(levelname)s] %(message)s',
        }
    },
    'syslog': {
        'handler': SysLogHandler,
        'handler_options': {
            'kwargs': {
                'address': '/dev/log',
                'facility': SysLogHandler.LOG_DAEMON,
            }
        },
        'formatter': logging.Formatter,
        'formatter_options': {
            'fmt': ' %(name)s %(process)d: [%(levelname)s] %(message)s',
        }
    },
}

if sys.platform == "linux2":
    LOG_SYSTEMS['syslog']['handler_options']['kwargs']['address'] = \
        '/dev/log'
elif sys.platform == "darwin":
    LOG_SYSTEMS['syslog']['handler_options']['kwargs']['address'] = \
        '/var/run/syslog'
LOG_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
}


def remove_log_handlers(name):
    """
    Remove all logger handlers.
    """
    logger = logging.getLogger(name)
    for handler in logger.handlers:
        handler.close()
        logger.removeHandler(handler)


def add_log_handler(name, log_type, log_level=logging.WARNING, extra=None):
    """
    Helper to add a logging handler.
    """
    if log_type not in LOG_SYSTEMS:
        raise ValueError(
            "%s is an invalid log system, must be one of: %s" %
            (log_type, ", ".join(LOG_SYSTEMS.keys())))
    if extra is None:
        extra = dict()
    # get main logger
    logger = logging.getLogger(name)
    log_level = LOG_LEVELS.get(log_level, logging.WARNING)
    logger.setLevel(log_level)
    # create handler
    handler_class = LOG_SYSTEMS[log_type]['handler']
    handler_options = LOG_SYSTEMS[log_type].get('handler_options', dict())
    kwargs = handler_options.get("kwargs", dict())
    kwargs.update(extra.get('handler_options', dict()))
    args = handler_options.get("args", list())
    handler = handler_class(*args, **kwargs)
    handler.setLevel(log_level)
    # create formatter
    if 'formatter' in LOG_SYSTEMS[log_type]:
        formatter_class = LOG_SYSTEMS[log_type]['formatter']
        formatter_options = LOG_SYSTEMS[log_type].get(
            'formatter_options', dict())
        formatter_options.update(extra.get('formatter_options', dict()))
        formatter = formatter_class(**formatter_options)
        handler.setFormatter(formatter)
    # finally add handler to the logger
    logger.addHandler(handler)


def setup_log(name, log_type, log_level=logging.WARNING, extra=None):
    """
    Helper to setup the logging facility.
    """
    if log_type not in LOG_SYSTEMS:
        raise ValueError(
            "%s is an invalid log system, must be one of: %s" %
            (log_type, ", ".join(LOG_SYSTEMS.keys())))
    remove_log_handlers(name)
    add_log_handler(name, log_type, log_level, extra)

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


def log_exceptions(logger_name, re_raise=True):
    """
    Log exceptions to configured log and re raise the exception or exit.
    """
    logger = logging.getLogger(logger_name)

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
                logger.debug(
                    "%s" % (" ".join(traceback.format_tb(error_tb)),))
                logger.error("%s" % (error,))
                if re_raise:
                    raise error
                else:
                    sys.exit(1)
        return out_function
    return out_function
