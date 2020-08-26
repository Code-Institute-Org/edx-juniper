import requests
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.views.decorators.cache import cache_control
from django.conf import settings
from django.contrib import messages
from django.template.context_processors import csrf
from django.core.mail import send_mail
from util.views import ensure_valid_course_key
from opaque_keys.edx.keys import CourseKey
from courseware.courses import get_course_with_access
from edxmako.shortcuts import render_to_response
from lms.djangoapps.ci_support.utils import get_a_students_mentor
from lms.djangoapps.ci_support.utils import get_mentor_details
from lms.djangoapps.ci_support.utils import send_email_from_zapier


@transaction.non_atomic_requests
@login_required
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def support(request, program_slug, student_id=None):
    """ Display the support page. """

    return render_to_response(
        'ci_support/support.html',
        {"program_slug": program_slug, 'student': request.user})


@transaction.non_atomic_requests
@login_required
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def tutor(request, program_slug, student_id=None):
    """ Display the tutor page. """

    return render_to_response(
        'ci_support/support/tutor_page.html',
        {"program_slug": program_slug, 'student': request.user})


@transaction.non_atomic_requests
@login_required
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def mentor(request, program_slug, student_id=None):
    """ Display the mentor page. """

    mentor = get_mentor_details(request.user.email)

    return render_to_response(
        "ci_support/support/mentor.html",
        {
            "program_slug": program_slug,
            "student": request.user,
            "mentor": mentor
        })


@transaction.non_atomic_requests
@login_required
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def slack(request, program_slug, student_id=None):
    """ Display the slack page. """

    return render_to_response(
        'ci_support/support/slack.html',
        {"program_slug": program_slug, 'student': request.user})


@transaction.non_atomic_requests
@login_required
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def troubleshooting(request, program_slug, student_id=None):
    """ Display the troubleshooting page. """

    return render_to_response(
        'ci_support/support/troubleshooting.html',
        {"program_slug": program_slug, 'student': request.user})


@transaction.non_atomic_requests
@login_required
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def studentcare(request, program_slug, student_id=None):
    """ Display the studentcare page. """

    if request.method == 'POST':
        student_email = request.user.email
        email_subject = request.POST["email-subject"]
        email_body = request.POST["email-body"]

        resp = send_email_from_zapier({
            'student_email': student_email,
            'email_subject': email_subject,
            'email_body': email_body
        })

        messages.success(request, 'Thank you! Your message has been sent to our Student Care team. We\'ll respond to you shortly.')


    return render_to_response(
        "ci_support/support/student_care.html",
        {
            "program_slug": program_slug,
            "student": request.user,
            "csrftoken": csrf(request)["csrf_token"]
        })
