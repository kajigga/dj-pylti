=====
Usage
=====

To use Django PYLTI in a project, add it to your `INSTALLED_APPS`:

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
