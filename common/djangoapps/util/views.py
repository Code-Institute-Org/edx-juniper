

import ast
import json
import logging
import sys
from functools import wraps

import calc
import crum
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, HttpResponseForbidden, HttpResponseServerError
from django.views.decorators.csrf import ensure_csrf_cookie, requires_csrf_token
from django.views.defaults import server_error
from django.shortcuts import redirect
from django.urls import reverse
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey
from six.moves import map
from lms.djangoapps.courseware.access import has_access
from lms.djangoapps.courseware.masquerade import setup_masquerade
from openedx.core.djangoapps.schedules.utils import reset_self_paced_schedule
from openedx.features.course_experience.utils import dates_banner_should_display

import track.views
from edxmako.shortcuts import render_to_response
from student.roles import GlobalStaff

log = logging.getLogger(__name__)


def ensure_valid_course_key(view_func):
    """
    This decorator should only be used with views which have argument course_key_string (studio) or course_id (lms).
    If course_key_string (studio) or course_id (lms) is not valid raise 404.
    """
    @wraps(view_func)
    def inner(request, *args, **kwargs):
        course_key = kwargs.get('course_key_string') or kwargs.get('course_id')
        if course_key is not None:
            try:
                CourseKey.from_string(course_key)
            except InvalidKeyError:
                raise Http404

        response = view_func(request, *args, **kwargs)
        return response

    return inner


def ensure_valid_usage_key(view_func):
    """
    This decorator should only be used with views which have argument usage_key_string.
    If usage_key_string is not valid raise 404.
    """
    @wraps(view_func)
    def inner(request, *args, **kwargs):
        usage_key = kwargs.get('usage_key_string')
        if usage_key is not None:
            try:
                UsageKey.from_string(usage_key)
            except InvalidKeyError:
                raise Http404

        response = view_func(request, *args, **kwargs)
        return response

    return inner


def require_global_staff(func):
    """View decorator that requires that the user have global staff permissions. """
    @wraps(func)
    def wrapped(request, *args, **kwargs):
        if GlobalStaff().has_user(request.user):
            return func(request, *args, **kwargs)
        else:
            raise PermissionDenied
    return login_required(wrapped)


def fix_crum_request(func):
    """
    A decorator that ensures that the 'crum' package (a middleware that stores and fetches the current request in
    thread-local storage) can correctly fetch the current request. Under certain conditions, the current request cannot
    be fetched by crum (e.g.: when HTTP errors are raised in our views via 'raise Http404', et. al.). This decorator
    manually sets the current request for crum if it cannot be fetched.
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if not crum.get_current_request():
            crum.set_current_request(request=request)
        return func(request, *args, **kwargs)
    return wrapper


@requires_csrf_token
def jsonable_server_error(request, template_name='500.html'):
    """
    500 error handler that serves JSON on an AJAX request, and proxies
    to the Django default `server_error` view otherwise.
    """
    if request.is_ajax():
        msg = {"error": "The edX servers encountered an error"}
        return HttpResponseServerError(json.dumps(msg))
    else:
        return server_error(request, template_name=template_name)


def handle_500(template_path, context=None, test_func=None):
    """
    Decorator for view specific 500 error handling.
    Custom handling will be skipped only if test_func is passed and it returns False

    Usage:

        @handle_500(
            template_path='certificates/server-error.html',
            context={'error-info': 'Internal Server Error'},
            test_func=lambda request: request.GET.get('preview', None)
        )
        def my_view(request):
            # Any unhandled exception in this view would be handled by the handle_500 decorator
            # ...

    """
    def decorator(func):
        """
        Decorator to render custom html template in case of uncaught exception in wrapped function
        """
        @wraps(func)
        def inner(request, *args, **kwargs):
            """
            Execute the function in try..except block and return custom server-error page in case of unhandled exception
            """
            try:
                return func(request, *args, **kwargs)
            except Exception:  # pylint: disable=broad-except
                if settings.DEBUG:
                    # In debug mode let django process the 500 errors and display debug info for the developer
                    raise
                elif test_func is None or test_func(request):
                    # Display custom 500 page if either
                    #   1. test_func is None (meaning nothing to test)
                    #   2. or test_func(request) returns True
                    log.exception("Error in django view.")
                    return render_to_response(template_path, context)
                else:
                    # Do not show custom 500 error when test fails
                    raise
        return inner
    return decorator


def calculate(request):
    ''' Calculator in footer of every page. '''
    equation = request.GET['equation']
    try:
        result = calc.evaluator({}, {}, equation)
    except:
        event = {'error': list(map(str, sys.exc_info())),
                 'equation': equation}
        track.views.server_track(request, 'error:calc', event, page='calc')
        return HttpResponse(json.dumps({'result': 'Invalid syntax'}))
    return HttpResponse(json.dumps({'result': str(result)}))


def info(request):
    """ Info page (link from main header) """
    return render_to_response("info.html", {})


def add_p3p_header(view_func):
    """
    This decorator should only be used with views which may be displayed through the iframe.
    It adds additional headers to response and therefore gives IE browsers an ability to save cookies inside the iframe
    Details:
    http://blogs.msdn.com/b/ieinternals/archive/2013/09/17/simple-introduction-to-p3p-cookie-blocking-frame.aspx
    http://stackoverflow.com/questions/8048306/what-is-the-most-broad-p3p-header-that-will-work-with-ie
    """
    @wraps(view_func)
    def inner(request, *args, **kwargs):
        """
        Helper function
        """
        response = view_func(request, *args, **kwargs)
        response['P3P'] = settings.P3P_HEADER
        return response
    return inner


@ensure_csrf_cookie
def reset_course_deadlines(request):
    """
    Set the start_date of a schedule to today, which in turn will adjust due dates for
    sequentials belonging to a self paced course
    """
    from lms.urls import RENDER_XBLOCK_NAME
    from openedx.features.course_experience.urls import COURSE_HOME_VIEW_NAME

    detail_id_dict = ast.literal_eval(request.POST.get('reset_deadlines_redirect_url_id_dict'))
    redirect_url = request.POST.get('reset_deadlines_redirect_url_base', COURSE_HOME_VIEW_NAME)
    course_key = CourseKey.from_string(detail_id_dict['course_id'])
    masquerade_details, masquerade_user = setup_masquerade(
        request,
        course_key,
        has_access(request.user, 'staff', course_key)
    )
    if masquerade_details and masquerade_details.role == 'student' and masquerade_details.user_name and (
        redirect_url == COURSE_HOME_VIEW_NAME
    ):
        # Masquerading as a specific student, so reset that student's schedule
        user = masquerade_user
    else:
        user = request.user

    missed_deadlines, missed_gated_content = dates_banner_should_display(course_key, user)
    if missed_deadlines and not missed_gated_content:
        reset_self_paced_schedule(user, course_key)
    if redirect_url == RENDER_XBLOCK_NAME:
        detail_id_dict.pop('course_id')
    return redirect(reverse(redirect_url, kwargs=detail_id_dict))
