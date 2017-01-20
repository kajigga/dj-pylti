# -*- coding: utf-8 -*-
"""
Test django_pylti module
"""
from django.test import TestCase, Client
from django.conf import settings
#from django.urls import reverse
from django.core.urlresolvers import reverse

import urllib
import urlparse
import logging
log = logging.getLogger(__name__)

import httpretty
import oauthlib.oauth1
from oauthlib.oauth1.rfc5849 import SIGNATURE_TYPE_BODY

from pylti.common import LTIException
from .auth_backend import LTI
from .models import LTIResource, LTIConsumer
from .models import LTIContext

"""
Setting up app test settings.
"""
from django.test import modify_settings, override_settings

bad_consumers = {
        "__consumer_key2__": {"secret": "__lti_secret2__"}
}

def abs_reverse(path, *args, **kwargs):
  uri = reverse(path, *args, **kwargs)
  return 'http://{}{}?'.format(SERVER_NAME, uri)

#SERVER_NAME = 'testserver'
SERVER_NAME = 'testserver'
@override_settings(
    DEBUG = True,
    SERVER_NAME = SERVER_NAME,
    SECRET_KEY = 'you-will-never-guess',
    PYLTI_URL_FIX = {
        "https://testserver/": {
            "https://testserver/": "https://testserver/"
        }
    }
)
class BaseLTITestClass(TestCase):

    def generate_launch_request(self, url,
                                lis_outcome_service_url=None,
                                roles=u'Instructor',
                                add_params=None):
        """
        Generate valid basic-lti-launch-request request with options.
        :param consumers: consumer map
        :param url: URL to sign
        :param lit_outcome_service_url: LTI callback
        :param roles: LTI role
        :return: signed request
        """
        # pylint: disable=unused-argument, too-many-arguments
        params = {'resource_link_id': u'edge.edx.org-i4x-MITx-ODL_ENG-lti-'
                                      u'94173d3e79d145fd8ec2e83f15836ac8',
                  'user_id': u'008437924c9852377e8994829aaac7a1',
                  'lis_result_sourcedid': u'MITx/ODL_ENG/2014_T1:'
                                          u'edge.edx.org-i4x-MITx-ODL_ENG-lti-'
                                          u'94173d3e79d145fd8ec2e83f15836ac8:'
                                          u'008437924c9852377e8994829aaac7a1',
                  'context_id': u'MITx/ODL_ENG/2014_T1',
                  'lti_version': u'LTI-1p0',
                  'launch_presentation_return_url': u'emptyhere',
                  'lis_outcome_service_url': (lis_outcome_service_url or
                                              u'https://example.edu/'
                                              u'courses/MITx/ODL_ENG/'
                                              u'2014_T1/xblock/i4x:;_;'
                                              u'_MITx;_ODL_ENG;_lti;'
                                              u'_94173d3e79d145fd8ec2e'
                                              u'83f15836ac8'
                                              u'/handler_noauth/'
                                              u'grade_handler'),
                  'lti_message_type': u'basic-lti-launch-request'}

        if roles is not None:
            params['roles'] = roles

        if add_params is not None:
            params.update(add_params)

        urlparams = urllib.urlencode(params)

        client = oauthlib.oauth1.Client(self.consumer.key,
                                        client_secret=unicode(self.consumer.secret),
                                        signature_method=oauthlib.oauth1.SIGNATURE_HMAC,
                                        signature_type=SIGNATURE_TYPE_BODY)
        headers = {'Content-Type':u'application/x-www-form-urlencoded'}
        uri, headers, body = client.sign(url, http_method='POST', body=params, headers=headers)
        body = urlparse.parse_qs(body)
        return uri, body

class TestDjangoPylti(BaseLTITestClass):
    """
    Consumers.
    """
    # pylint: disable=too-many-public-methods

    # Valid XML response from LTI 1.0 consumer
    expected_response = """<?xml version="1.0" encoding="UTF-8"?>
<imsx_POXEnvelopeResponse xmlns = "http://www.imsglobal.org/services/ltiv1p1\
/xsd/imsoms_v1p0">
    <imsx_POXHeader>
        <imsx_POXResponseHeaderInfo>
            <imsx_version>V1.0</imsx_version>
            <imsx_messageIdentifier>edX_fix</imsx_messageIdentifier>
            <imsx_statusInfo>
                <imsx_codeMajor>success</imsx_codeMajor>
                <imsx_severity>status</imsx_severity>
                <imsx_description>Score for StarX/StarX_DEMO/201X_StarX:\
edge.edx.org-i4x-StarX-StarX_DEMO-lti-40559041895b4065b2818c23b9cd9da8\
:18b71d3c46cb4dbe66a7c950d88e78ec is now 0.0</imsx_description>
                <imsx_messageRefIdentifier>
                </imsx_messageRefIdentifier>
            </imsx_statusInfo>
        </imsx_POXResponseHeaderInfo>
    </imsx_POXHeader>
    <imsx_POXBody><replaceResultResponse/></imsx_POXBody>
</imsx_POXEnvelopeResponse>
        """

    def setUp(self):
        self.app = Client()
        self.consumer = LTIConsumer.objects.create(name='uvu-khansen')

    def test_lti_context_created_after_launch(self):
        """
        Accessing oauth_resource.
        """
        url = abs_reverse('lti-tests:initial')
        context_id = u'MITx/ODL_ENG/2014_T1'
        context_label = u'MITx/ODL_ENG/2014_T1'

        new_url, body = self.generate_launch_request(url, add_params={
          'custom_canvas_user_id':'599',
          'custom_canvas_user_login_id':'gomer',
          'lis_person_name_family':'Pile',
          'lis_person_name_given':'Gomer',
          'lis_person_contact_email_primary':'gomer@gmail.com',
          'context_id': context_id,
          'context_label': context_label,
          })

        ret = self.app.post(new_url, body) #, content_type='application/octet-stream')
        self.assertEqual(200, ret.status_code)
        lti_context = LTIContext.objects.get(context_id=context_id)

        assert lti_context.context_id == context_id
        assert lti_context.context_label == context_label

    def test_lti_info_in_session(self):
        """
        Accessing oauth_resource.
        """
        url = abs_reverse('lti-tests:initial')
        context_id = u'MITx/ODL_ENG/2014_T1'
        context_label = u'MITx/ODL_ENG/2014_T1'
        new_url, body = self.generate_launch_request(url, add_params={
          'custom_canvas_user_id':'599',
          'custom_canvas_user_login_id':'gomer',
          'lis_person_name_family':'Pile',
          'lis_person_name_given':'Gomer',
          'lis_person_contact_email_primary':'gomer@gmail.com',
          'context_id': context_id,
          'context_label': context_label,
          })

        #ret = self.app.get(new_url)
        ret = self.app.post(new_url, body)
        assert 'custom_canvas_user_id' in self.app.session
        assert 'lis_person_contact_email_primary' in self.app.session
        assert 'lis_person_name_given' in self.app.session
        assert 'lis_person_name_family' in self.app.session
        self.assertEqual(200, ret.status_code)
        lti_context = LTIContext.objects.get(context_id=context_id)

        assert lti_context.context_id == context_id
        assert lti_context.context_label == context_label

