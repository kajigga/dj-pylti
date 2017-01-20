=============================
Django PYLTI
=============================

.. image:: https://badge.fury.io/py/dj-pylti.svg
    :target: https://badge.fury.io/py/dj-pylti

.. image:: https://travis-ci.org/kajigga/dj-pylti.svg?branch=master
    :target: https://travis-ci.org/kajigga/dj-pylti

.. image:: https://codecov.io/gh/kajigga/dj-pylti/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/kajigga/dj-pylti

Your project description goes here

Documentation
-------------

The full documentation is at https://dj-pylti.readthedocs.io.

Quickstart
----------

Install Django PYLTI::

    pip install dj-pylti

Add it to your `INSTALLED_APPS`:

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'dj_pylti.apps.DjPyltiConfig',
        ...
    )

Add Django PYLTI's URL patterns:

.. code-block:: python

    from dj_pylti import urls as dj_pylti_urls


    urlpatterns = [
        ...
        url(r'^', include(dj_pylti_urls)),
        ...
    ]

Features
--------

* TODO

Running Tests
-------------

Does the code actually work?

::

    source <YOURVIRTUALENV>/bin/activate
    (myenv) $ pip install tox
    (myenv) $ tox

Credits
-------

Tools used in rendering this package:

*  Cookiecutter_
*  `cookiecutter-djangopackage`_

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`cookiecutter-djangopackage`: https://github.com/pydanny/cookiecutter-djangopackage
