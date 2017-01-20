from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import models
import jsonfield # https://github.com/bradjasper/django-jsonfield
from django.dispatch import receiver
from django.db.models.signals import post_init
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth import logout
from django.contrib.auth import login

import json
import uuid
import os

import logging
from pylti.common import ( LTINotInSessionException, LTIException,
    LTIRoleException,
    LTIPostMessageException,
    LTI_PROPERTY_LIST,
    LTI_ROLES,
    post_message,
    post_message2,
    generate_request_xml,
    verify_request_common
    )

# Canvas also sends ext_roles to represent any other role the user might have
# in the system
LTI_PROPERTY_LIST.append('ext_roles')

# Add any number of customized attributes into the session
LTI_PROPERTY_LIST.extend(settings.PYLTI_CONFIG.get('lti_properties'))#,'ext_roles')

# This is how Canvas sends the roles
LTI_ROLES['administrator'].append('urn:lti:instrole:ims/lis/Administrator')
LTI_ROLES['instructor'].append('urn:lti:instrole:ims/lis/Instructor')
LTI_ROLES['student'].append('urn:lti:instrole:ims/lis/Learner')

log = logging.getLogger(__name__)  # pylint: disable=invalid-name

def session_roles(request):
    """
    Return the full session roles which can be in 'roles' and 'ext_roles'
    :return: roles
    """
    #return ",".join((request.session.get('roles', ''), request.session.get('ext_roles', '')))
    #return ",".join((request.session.get('roles', ''), request.session.get('ext_roles', '')))
    #return ",".join((request.session.get('roles', ''),))
    return request.session.get('roles')

class LTIConsumer(models.Model):
  name = models.CharField(max_length=255)
  #key = models.CharField(max_length=255) # Make this auto-generate
  secret = models.UUIDField(default=uuid.uuid4, editable=False)

  def __unicode__(self):
    return '{0}:{1}'.format(self.name, self.concat_secret())

  @property
  def key(self):
    return u'{}'.format(self.pk)

  def concat_secret(self):
    return '{0:.<10}'.format(str(self.secret)[:6])

  def for_pylti(self):
    return {
        str(self.pk): { 'secret': str(self.secret)}
        }

# Create your models here.
class BaseLTIObject(models.Model):
  custom_attributes = jsonfield.JSONField(default={}) 

class LTIUserProfile(BaseLTIObject):
  user = models.ForeignKey(User, db_column='user_id_int')
  lti_user_id = models.CharField(max_length=255, blank=False, null=False, unique=True) 
  lis_person_contact_email_primary = models.CharField(max_length=255)
  lis_person_name_family = models.CharField(max_length=255)
  lis_person_name_full = models.CharField(max_length=255)  
  lis_person_name_given = models.CharField(max_length=255)

  def __unicode__(self):
    return "{0.user}".format(self)


@receiver(post_init, sender=LTIUserProfile)
def json_decode_fields(sender, instance, *args, **kwargs):
  if not instance.custom_attributes:
    instance.custom_attributes = '{}'
  instance.custom_attributes = json.loads(instance.custom_attributes)


class LTIResource(BaseLTIObject):
  """A resource represents link in a context. This can take the form of a module,
  a course navigation link item, an assignment link, etc"""
  resource_link_id = models.CharField(max_length=255)
  resource_link_title = models.CharField(max_length=255)
  def __unicode__(self):
    return r'{}:{}'.format(self.resource_link_id, self.resource_link_title)

class LTIContext(BaseLTIObject):
  "A context is usually a course."
  context_id = models.CharField(max_length=255) # "context_id": "fd197bddc79a576f47376cd9665657dff8e5d90e",
  context_label = models.CharField(max_length=255) #"context_label": "Reading Ancient Greek",

class PropertyName(models.Model):
  name = models.CharField(max_length=50)
  choices = jsonfield.JSONField(default=[], blank=True, null=True)
  default = models.CharField(max_length=255, blank=True, null=True)
  def __unicode__(self):
    return u'{}'.format(self.name)

OPTION_NAME_CHOICES = (
    ('course_navigation','Course Navigation'),
    ('account_navigation','Account Navigation'),
    ('user_navigation','User Navigation'),
    ('editor_button','Richtext Editor Button'),
    ('labels','Translations'),
    ('resource_selection','Resource Selection'),
    )

class OptionList(models.Model):
  name = models.CharField(max_length=50, choices=OPTION_NAME_CHOICES) 
  parent = models.ForeignKey('OptionList', null=True, blank=True, related_name='children')
  config = models.ForeignKey('Configuration', null=True, blank=True, related_name='options')

  def __unicode__(self):
    return u'{}'.format(self.name)

  def num_properties(self):
    return self.properties.count()

class OptionProperty(models.Model):
  option = models.ForeignKey(PropertyName)
  value = models.CharField(max_length=255)
  option_list = models.ForeignKey(OptionList, related_name='properties')

  def __unicode__(self):
    return '{0.option.name}:{0.value}'.format(self)

PRIVACY_LEVELS = (
    ('public','public'),
    ('email','email'),
    ('name', 'name'),
    ('anonymous','anonymous'),
    )

class Configuration(models.Model):
  launch_url = models.CharField(max_length=255)
  title = models.CharField(max_length=255)
  description = models.TextField()
  properties_domain = models.CharField(max_length=255, default=settings.CUST_HOSTNAME)
  properties_privacy_level = models.CharField(max_length=255, choices=PRIVACY_LEVELS)
  properties_text = models.CharField(max_length=255, blank=True, null=True)

  def __unicode__(self):
    return u'({}) {}'.format(self.pk, self.title)

  def build_launch_url_orig(self):
    protocol = getattr(settings,'PROTOCOL','http')
    return '{}://{}{}'.format(protocol, settings.CUST_HOSTNAME, self.launch_url)

  def build_launch_url(self):
    return self.launch_url

class LTI(object):
    """
    LTI Object represents abstraction of current LTI session. It provides
    callback methods and methods that allow developer to inspect
    LTI basic-launch-request.

    This object is instantiated by @lti wrapper.
    """

    def __init__(self, lti_args, lti_kwargs, request, **kwargs):
        self.lti_args = lti_args
        self.lti_kwargs = lti_kwargs
        #self.resource = kwargs.get('resource')
        #self.context = kwargs.get('context')

        self.request = request
        self.__consumers = None

    def verify(self):
        """
        Verify if LTI request is valid, validation
        depends on @lti wrapper arguments

        :raises: LTIException
        """
        if self.lti_kwargs.get('request') == 'session':
            self._verify_session()
        elif self.lti_kwargs.get('request') == 'initial':
            self.verify_request()
        elif self.lti_kwargs.get('request') == 'any':
            self._verify_any()
        else:
            raise LTIException("Unknown request type")
        return True

    def _verify_any(self):
        """
        Verify that request is in session or initial request

        :raises: LTIException
        """
        try:
            self._verify_session()
        except LTINotInSessionException:
            self.verify_request()

    def _verify_session(self):
        """
        Verify that session was already created

        :raises: LTIException
        """
        # Use django's builtin user session
        # authentication. 

        if not self.request.user.is_authenticated:
            log.debug('verify_session failed')
            raise LTINotInSessionException('Session expired or unavailable')

    @property
    def consumers(self):
        """
        Gets consumer's map from settings 
        :return: consumers map
        """
        # TODO moving from static settings to consumers in the db
        config = getattr(settings, 'PYLTI_CONFIG', {})
        # If 'consumers' is a callable, call it at this point
        # i.e. app_name.utils.get_consumers
        #consumers = config.get('consumers', {})
        #return consumers
        found_consumers = {}
        if not self.__consumers:
          try:
            consumer = LTIConsumer.objects.get(pk=self.key)

            ''' consumers needs to look like this: 
            consumers = {
                "uvu-khansen": {"secret": "khansen-123"},
            }
            '''
            found_consumers = consumer.for_pylti()
          except LTIConsumer.DoesNotExist:
            log.debug('consumer does not exist key:{}'.format(self.key))
            found_consumers = None
        return found_consumers

    @property
    def name(self):  # pylint: disable=no-self-use
        """
        Name returns user's name or user's email or user_id
        :return: best guess of name to use to greet user
        """
        s = dict(self.request.session)
        user = self.request.user
        if user and user.get_full_name():
          return user.get_full_name() 
        elif 'lis_person_sourcedid' in s:
          return s['lis_person_sourcedid']
        elif 'lis_person_contact_email_primary' in s:
          return s['lis_person_contact_email_primary']
        elif 'user_id' in s:
          return s['user_id']
        else:
          return ''

    @property
    def key(self):  # pylint: disable=no-self-use
        """
        OAuth Consumer Key
        :return: key
        """
        #k = self.request.POST.get('oauth_consumer_key')

        try:
          key = self.request.POST['oauth_consumer_key']
        except Exception as exc:
          key = None
        return int(key)

    @staticmethod
    def message_identifier_id():
        """
        Message identifier to use for XML callback

        :return: non-empty string
        """
        return "edX_fix"

    @property
    def lis_result_sourcedid(self):  # pylint: disable=no-self-use
        """
        lis_result_sourcedid to use for XML callback

        :return: LTI lis_result_sourcedid
        """
        return self.request.session['lis_result_sourcedid']

    @property
    def role(self):  # pylint: disable=no-self-use
        """
        LTI roles

        :return: roles
        """
        return session_roles(self.request)

    #@staticmethod
    def is_role(self, role):
        """
        Verify if user is in role

        :param: role: role to verify against
        :return: if user is in role
        :exception: LTIException if role is unknown
        """
        roles = session_roles(self.request).split(',')
        if role in LTI_ROLES:
            role_list = LTI_ROLES[role]
            # find the intersection of the roles
            roles = set(role_list) & set(roles)
            is_user_role_there = len(roles) >= 1
            log.debug('roles %s', roles)
            return is_user_role_there
        else:
            raise LTIException("Unknown role {}.".format(role))

    def _check_role(self):
        """
        Check that user is in role specified as wrapper attribute

        :exception: LTIRoleException if user is not in roles
        """
        role_required = u'any'
        log.debug('lti_kwargs: %s', self.lti_kwargs)
        if 'role' in self.lti_kwargs:
            role_required = self.lti_kwargs['role']
        log.debug(
            "check_role lti_role=%s decorator_role=%s", self.role, role_required
        )
        if not (role_required == u'any' or self.is_role(role_required)):
            raise LTIRoleException('Not authorized.')

    @property
    def response_url(self):
        """
        Returns remapped lis_outcome_service_url
        uses PYLTI_URL_FIX map to support edX dev-stack

        :return: remapped lis_outcome_service_url
        """
        url = self.request.session['lis_outcome_service_url']
        app_config = getattr(settings, 'PYLTI_CONFIG', {})
        urls = app_config.get('PYLTI_URL_FIX', dict())
        for prefix, mapping in urls.iteritems():
            if url.startswith(prefix):
                for _from, _to in mapping.iteritems():
                    url = url.replace(_from, _to)
        return url

    @property
    def resource(self):
      resource, created = LTIResource.objects.get_or_create(resource_link_id=self.request.session['resource_link_id'])
      return resource

    @property
    def context(self):
      context, created = LTIContext.objects.get_or_create(context_id=self.request.session['context_id'])
      return context

    def verify_request(self):
        """
        Verify LTI request

        :raises: LTIException is request validation failed
        """
        if self.request.method == 'POST':
            params = self.request.POST.dict()
        #else:
        #    params = self.request.GET.dict()

        url = self.request.build_absolute_uri()
        log.debug('verify_request url: %s', url)
        log.debug('https: {}'.format(os.getenv('HTTPS')))
        if os.getenv('HTTPS') == 'on':
          url = url.replace('http','https')
        log.debug('verify_request url: %s', url)
        try:
            #self._key = params['oauth_consumer_key']
            verify_request_common(self.consumers, 
                url,
                self.request.method, 
                dict(self.request.META),
                params)

            # get or create LTIResource
            if params.get('resource_link_id'):
              resource, created = LTIResource.objects.get_or_create(resource_link_id=params['resource_link_id'])
              if created and params.get('resource_link_title'):
                resource.resource_link_title = params['resource_link_title']
                resource.save()
              #self.resource = resource
  
            if params.get('context_id'):
              context, created = LTIContext.objects.get_or_create(context_id=params['context_id'])
              if created and params.get('context_label'):
                context.context_label = params['context_label']
                context.save()
              #self.context = context

            # get_or_create LTIUserProfile
            # Authenticate user
            user = authenticate(params=params)
            user_profile = user.ltiuserprofile_set.first()
            login(self.request, user_profile.user)
            for prop in LTI_PROPERTY_LIST:
                if params.get(prop, None):
                    #log.debug("params %s=%s", prop, params.get(prop, None))
                    self.request.session[prop] = params[prop]
                    if prop !='user_id': # Don't need to add it again
                      if not 'custom' in prop:
                        setattr(user_profile, prop, params.get(prop, None))
                      else:
                        user_profile.custom_attributes[prop] = params.get(prop, None)
            user_profile.save()


            return user is not None
        except LTIException as exc:
            log.debug('verify_request failed %s' % exc)
            for prop in LTI_PROPERTY_LIST:
                if self.request.session.get(prop, None):
                    del self.request.session[prop]

            # Do django logout instead
            logout(self.request)
            raise

    def post_grade(self, grade):
        """
        Post grade to LTI consumer using XML

        :param: grade: 0 <= grade <= 1
        :return: True if post successful and grade valid
        :exception: LTIPostMessageException if call failed
        """
        message_identifier_id = self.message_identifier_id()
        operation = 'replaceResult'
        lis_result_sourcedid = self.lis_result_sourcedid
        # # edX devbox fix
        score = float(grade)
        if 0 <= score <= 1.0:
            xml = generate_request_xml(
                message_identifier_id, operation, lis_result_sourcedid,
                score)
            ret = post_message(self.consumers, self.key,
                               self.response_url, xml)
            if not ret:
                raise LTIPostMessageException("Post Message Failed")
            return True

        return False

    def post_grade2(self, grade, user=None, comment=''):
        """
        Post grade to LTI consumer using REST/JSON
        URL munging will is related to:
        https://openedx.atlassian.net/browse/PLAT-281

        :param: grade: 0 <= grade <= 1
        :return: True if post successful and grade valid
        :exception: LTIPostMessageException if call failed
        """
        content_type = 'application/vnd.ims.lis.v2.result+json'
        if user is None:
          user = self.request.session['user_id']
        lti2_url = self.response_url.replace(
          "/grade_handler",
          "/lti_2_0_result_rest_handler/user/{}".format(user))
        score = float(grade)
        if 0 <= score <= 1.0:
          body = json.dumps({
              "@context": "http://purl.imsglobal.org/ctx/lis/v2/Result",
              "@type": "Result",
              "resultScore": score,
              "comment": comment
          })
          ret = post_message2(self.consumers, self.key, lti2_url, body,
                              method='PUT',
                              content_type=content_type)
          if not ret:
              raise LTIPostMessageException("Post Message Failed")
          return True

        return False

    def is_instructor(self):
      return self.is_role('instructor')
    def is_student(self):
      return self.is_role('student')
    def is_admin(self):
      return self.is_role('administrator')

    def close_session(self):
        """
        Invalidates session
        """
        for prop in LTI_PROPERTY_LIST:
            if self.request.session.get(prop, None):
                del self.request.session[prop]
        #self.request.session[LTI_SESSION_KEY] = False
        logout(self.request)
