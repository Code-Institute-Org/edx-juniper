# pylint: disable=missing-module-docstring

# View for semi-static templatized content.
#
# List of valid templates is explicitly managed for (short-term)
# security reasons.


import mimetypes

from django.conf import settings
from django.http import Http404, HttpResponseNotFound, HttpResponseServerError
from django.http.response import HttpResponseForbidden
from django.shortcuts import redirect
from django.template import TemplateDoesNotExist
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import ensure_csrf_cookie
from mako.exceptions import TopLevelLookupException

from edxmako.shortcuts import render_to_response, render_to_string
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from util.cache import cache_if_anonymous
from util.views import fix_crum_request

valid_templates = []

if settings.STATIC_GRAB:
    valid_templates = valid_templates + [
        'server-down.html',
        'server-error.html'
        'server-overloaded.html',
    ]


def index(request, template):
    if template in valid_templates:
        return render_to_response('static_templates/' + template, {})
    else:
        return redirect('/')


@ensure_csrf_cookie
@cache_if_anonymous()
def render(request, template):
    """
    This view function renders the template sent without checking that it
    exists. Do not expose template as a regex part of the url. The user should
    not be able to ender any arbitray template name. The correct usage would be:

    url(r'^jobs$', 'static_template_view.views.render', {'template': 'jobs.html'}, name="jobs")
    """

    # Guess content type from file extension
    content_type, __ = mimetypes.guess_type(template)

    try:
        context = {}
        # This is necessary for the dialog presented with the TOS in /register
        if template == 'honor.html':
            context['allow_iframing'] = True
        # Format Examples: static_template_about_header
        configuration_base = 'static_template_' + template.replace('.html', '').replace('-', '_')
        page_header = configuration_helpers.get_value(configuration_base + '_header')
        page_content = configuration_helpers.get_value(configuration_base + '_content')
        if page_header:
            context['page_header'] = mark_safe(page_header)
        if page_content:
            context['page_content'] = mark_safe(page_content)
        result = render_to_response('static_templates/' + template, context, content_type=content_type)
        return result
    except TopLevelLookupException:
        raise Http404
    except TemplateDoesNotExist:
        raise Http404


@ensure_csrf_cookie
@cache_if_anonymous()
def render_press_release(request, slug):
    """
    Render a press release given a slug.  Similar to the "render" function above,
    but takes a slug and does a basic conversion to convert it to a template file.
    a) all lower case,
    b) convert dashes to underscores, and
    c) appending ".html"
    """
    template = slug.lower().replace('-', '_') + ".html"
    try:
        resp = render_to_response('static_templates/press_releases/' + template, {})
    except TemplateDoesNotExist:
        raise Http404
    else:
        return resp


@fix_crum_request
def render_404(request, exception):
    request.view_name = '404'
    return HttpResponseNotFound(render_to_string('static_templates/404.html', {}, request=request))


@fix_crum_request
def render_500(request):
    return HttpResponseServerError(render_to_string('static_templates/server-error.html', {}, request=request))


@fix_crum_request
def render_403(request, exception):
    request.view_name = '403'
    return HttpResponseForbidden(render_to_string('static_templates/403.html', {}, request=request))
