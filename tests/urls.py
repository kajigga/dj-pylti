# -*- coding: utf-8
from __future__ import unicode_literals, absolute_import

from django.conf.urls import url, include

from dj_pylti.urls import urlpatterns as dj_pylti_urls

urlpatterns = [
    url(r'^', include(dj_pylti_urls, namespace='dj_pylti')),
]
