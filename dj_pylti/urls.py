from django.conf.urls import url
from django.views.generic.base import TemplateView
from django.views.decorators.cache import cache_page

from . import views 

urlpatterns = [ 
    url(r'^any/', views.any, name='any'),
    url(r'^initial/', views.initial, name='initial'),
    url(r'^setup_session', views.setup_session, name='setup_session'),
    url(r'^close_session', views.close_session, name='close_session'),
    url(r'^session_info', views.session_info, name='session'),
    url(r'^name/', views.name, name='name'),
    url(r'^post_grade/([\d.]+)/', views.post_grade, name='post_grade'),
    url(r'^post_grade2/([\d.]+)/', views.post_grade2, name='post_grade2'),
    url(r'^unknown_protection/', views.unknown_protection, name='unknown_protection'),
    #url(r'^default_lti/', views.default_lti, name='default_lti'),
    # Add config URL
    url(r'^config/(?P<pk>[\d]+)', cache_page(60*15)(views.ConfigurationView.as_view()), name='lti_config'),
]
