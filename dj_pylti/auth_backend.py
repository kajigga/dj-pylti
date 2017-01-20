# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.auth.models import User
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.clickjacking import xframe_options_exempt

from models import *
import json
import logging

from django.contrib.auth import authenticate
from django.contrib.auth import logout
from django.contrib.auth import login

from functools import wraps

from pylti.common import LTIException

log = logging.getLogger('django_lti')  # pylint: disable=invalid-name

def default_error(exception=None):
    """Render simple error page.  This should be overidden in applications."""
    # pylint: disable=unused-argument
    return HttpResponse("There was an LTI communication error: {}".format(exception), status=500)# , mimetype='application/json')
    #return , 500

class DjangoLTIAuthBackend(object):

  def authenticate(self, params=None):
    """authenticate should check the credentials it gets, and it should return
    a User object that matches those credentials, if the credentials are valid.
    If they’re not valid, it should return None."""

    if params and params.get('user_id'):

      # do the lti authentication here
      lti_user_id = params.get('user_id')

      try:
        user_profile = LTIUserProfile.objects.get(lti_user_id=lti_user_id)
      except LTIUserProfile.DoesNotExist:
        user, created = User.objects.get_or_create(username=params['user_id'],
            first_name=params.get('lis_person_name_given'),
            last_name=params.get('lis_person_name_family'),
            email=params.get('lis_person_contact_email_primary'),
            )
        user_profile = LTIUserProfile.objects.create(lti_user_id=params['user_id'], user=user)


      return user_profile.user

  def get_user(self, user_id): #user_id is the primary key for a user
    """The get_user method takes a user_id – which could be a username,
    database ID or whatever, but has to be the primary key of your User object
    – and returns a User object."""
    return User.objects.get(pk=user_id)

  #def has_perm(self, user_obj, perm, obj,  **kwargs):
  #  print 'user', user_obj
  #  print 'perm', perm
  #  print 'obj', obj
  #  print 'kwargs', kwargs
  #  #return True



def lti( request='any', error=default_error, role='any',
        *lti_args, **lti_kwargs):
    """
    LTI decorator

    :param: error - Callback if LTI throws exception (optional).
        :py:attr:`pylti.flask.default_error` is the default.
    :param: request - Request type from
        :py:attr:`pylti.common.LTI_REQUEST_TYPE`. (default: any)
    :param: roles - LTI Role (default: any)
    :return: wrapper
    """

    def _lti(function):
        """
        Inner LTI decorator

        :param: function:
        :return:
        """

        @wraps(function)
        def wrapper(*args, **kwargs):
            """
            Pass LTI reference to function or return error.
            """
            request = args[0]
            try:
                the_lti = LTI(lti_args, lti_kwargs, args[0])
                the_lti.verify()
                the_lti._check_role()  # pylint: disable=protected-access
                kwargs['lti'] = the_lti

                # All good to go, store all of the LTI params in a
                # session dict for use in views
                #if request.method == 'POST':
                #  request.session['lti_vals'] = request.POST

                return function(*args, **kwargs)
            except LTIException as lti_exception:
                error = lti_kwargs.get('error')
                exception = dict()
                exception['exception'] = lti_exception
                exception['kwargs'] = kwargs
                exception['args'] = args
                return error(exception=exception)


        return wrapper

    lti_kwargs['request'] = request
    lti_kwargs['error'] = error
    lti_kwargs['role'] = role

    return _lti

