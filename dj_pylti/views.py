from django.shortcuts import render
from django.http import HttpResponse

from pylti.common import LTI_SESSION_KEY
from auth_backend import lti
# Create your views here.
from django.views.decorators.csrf import csrf_exempt

@lti(request='any')
@csrf_exempt
def name(request, *args, **kwargs):
    """
    Access route with 'initial' request.

    :param lti: `lti` object
    :return: string "hi"
    """
    _lti = kwargs.get('lti', {})
    
    #name = _lti.name
    return HttpResponse(_lti.name, status=200)# , mimetype='application/json')

@lti(request='any')
def any(request, **kwargs):
    """
    Access route with 'any' request.

    :param lti: `lti` object
    :return: string "hi"
    """
    return HttpResponse('any', status=200)# , mimetype='application/json')

@lti(request='initial')
def initial(request, **kwargs):
    """
    Access route with 'initial' request.

    :param lti: `lti` object
    :return: string "hi"
    """
    return HttpResponse('initial', status=200)

@csrf_exempt
@lti(request='initial')
def session_info(request, **kwargs):
  return render(request, 'session_info.html', {'post':request.POST})

def setup_session(request, *args, **kwargs):
    """
    Access 'setup_session' route with 'Student' role and oauth_consumer_key.

    :return: string "session set"
    """
    request.session[LTI_SESSION_KEY] = True
    request.session['oauth_consumer_key'] = '__consumer_key__'
    request.session['roles'] = 'Student'
    return HttpResponse('session set', status=200)


@lti( request='session')
def session(request, **kwargs):
    # pylint: disable=unused-argument,
    _lti = kwargs.get('lti')
    """
    Access route with 'session' request.

    :param lti: `lti` object
    :return: string "hi"
    """
    return HttpResponse('hi', status=200)


@lti(request='session')
def close_session(request, **kwargs):
    _lti = kwargs.get('lti')
    """
    Access 'close_session' route.

    :param lti: `lti` object
    :return: string "session closed"
    """
    _lti.close_session()
    return HttpResponse('hi', status=200)

@lti(request='session')
def post_grade(request, grade, *args, **kwargs):
    """
    Access route with 'session' request.

    :param lti: `lti` object
    :return: string "grade={}"
    """
    _lti = kwargs.get('lti')
    ret = _lti.post_grade(grade)
    return HttpResponse("grade={}".format(ret), status=200)


@lti(request='session')
def post_grade2(request, grade, *args, **kwargs):
    """
    Access route with 'session' request.

    :param lti: `lti` object
    :return: string "grade={}"
    """
    _lti = kwargs.get('lti')
    return HttpResponse('grade={}'.format(_lti.post_grade2(grade)), status=200)


@lti(request='initial', role='staff')
def initial_staff(request, *args, **kwargs):
    # pylint: disable=unused-argument,
    """
    Access route with 'initial' request and 'staff' role.

    :param lti: `lti` object
    :return: string "hi"
    """
    return HttpResponse('hi', status=200)

@lti(request='initial', role='student')
def initial_student(request, *args, **kwargs):
    # pylint: disable=unused-argument,
    """
    Access route with 'initial' request and 'student' role.

    :param lti: `lti` object
    :return: string "hi"
    """
    return HttpResponse('hi', status=200)

@lti()
def default_lti(request, *args, **kwargs):
    # pylint: disable=unused-argument,
    """
    Make sure default LTI decorator works.
    """
    return HttpResponse('hi', status=200)

@lti(request='initial', role='unknown')
def initial_unknown(request, *args, **kwargs):
    # pylint: disable=unused-argument,
    """
    Access route with 'initial' request and 'unknown' role.

    :param lti: `lti` object
    :return: string "hi"
    """
    return HttpResponse('hi', status=200)

@lti(request='notreal')
def unknown_protection(request, *args, **kwargs):
    # pylint: disable=unused-argument,
    """
    Access route with unknown protection.

    :param lti: `lti` object
    :return: string "hi"
    """
    return HttpResponse('hi', status=200)

from django.views.generic.detail import DetailView
from .models import Configuration
class ConfigurationView(DetailView):
  model = Configuration
  template_name = 'config.xml'
  content_type='application/xml'
