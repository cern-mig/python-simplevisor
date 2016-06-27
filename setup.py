from distutils.core import setup, Command
import os
import sys
import simplevisor

NAME = 'simplevisor'
VERSION = simplevisor.VERSION
DESCRIPTION = "Simple daemon supervisor"
LONG_DESCRIPTION = """
Simplevisor is a simple daemons supervisor, it is inspired by
Erlang OTP and it can supervise hierarchies of services.
"""
AUTHOR = 'Massimo Paladin'
AUTHOR_EMAIL = 'massimo.paladin@gmail.com'
LICENSE = "ASL 2.0"
PLATFORMS = "Any"
URL = "https://github.com/cern-mig/python-simplevisor"
CLASSIFIERS = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: Unix",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2.4",
    "Programming Language :: Python :: 2.5",
    "Programming Language :: Python :: 2.6",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3.0",
    "Programming Language :: Python :: 3.1",
    "Programming Language :: Python :: 3.2",
    "Programming Language :: Python :: 3.3",
    "Topic :: Software Development :: Libraries :: Python Modules"
]


class test(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        os.environ["PATH"] += os.pathsep + "./bin"
        from test import run_tests
        run_tests.main()

_with_data_files = "--with-data-files"
with_data_files = False
if _with_data_files in sys.argv:
    with_data_files = True
    sys.argv.remove(_with_data_files)

if with_data_files:
    data_files = [
        ('/usr/share/man/man1',
         ['man/simplevisor.1',
          'man/simplevisor-control.1',
          'man/simplevisor-loop.1']), ]
else:
    data_files = list()

setup(name=NAME,
      version=VERSION,
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      author=AUTHOR,
      author_email=AUTHOR_EMAIL,
      license=LICENSE,
      platforms=PLATFORMS,
      url=URL,
      classifiers=CLASSIFIERS,
      packages=['simplevisor', 'simplevisor.mtb', ],
      scripts=['bin/simplevisor',
               'bin/simplevisor-control',
               'bin/simplevisor-loop'],
      data_files=data_files,
      cmdclass={'test': test, }, )
