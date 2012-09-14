Installation
============

You can install simplevisor through different sources.

pip/easy_install way
--------------------

You can automatically install it through *easy_install*::

    easy_install simplevisor

or *pip*::

    pip install simplevisor

tarball
-------

You can install it through the tarball, download the latest
one from http://pypi.python.org/pypi/simplevisor, unpack it, cd
into the directory and install it::

    version=X
    wget http://pypi.python.org/packages/source/s/simplevisor/simplevisor-${version}.tar.gz
    tar xvzf simplevisor-${version}.tar.gz
    cd simplevisor-${version}
    # Run the tests
    python setup.py test
    # Install it
    python setup.py install

rpm
---

RPMs are available for *Fedora* main branches and *EPEL 5/6*, you can simply
install it with *yum*::

    yum install python-simplevisor


