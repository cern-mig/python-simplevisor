==========================================
How to release a new version of the module
==========================================

To release a new version of the moduleplease follow these steps:

- update version number and date in the ``__init__.py`` file
- updated ``CHANGES`` file with relative version number and date
- ``git commit -am "preparing for release X.X"``
- ``git push``

You are now almost ready to release a new version of the module.
Make sure you read the pypi guide:
http://wiki.python.org/moin/CheeseShopTutorial#Submitting_Packages_to_the_Package_Index

and the set the ``.pypirc`` file (http://docs.python.org/2/distutils/packageindex.html#pypirc).

You can now proceed and release the package::

    sh release.sh

