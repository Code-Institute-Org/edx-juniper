
import math

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from edxmako.shortcuts import render_to_response
from ci_program.models import Program
from ci_program.utils import get_student_deadlines
from openedx.core.djangoapps.bookmarks.models import Bookmark


@login_required
def show_programs(request, program_name):
    """
    Display the programs page
    """
    student_email = request.user.email
    cache_key = '%s_program_name' % student_email

    program = Program.objects.get(marketing_slug=program_name)
    cache.set(cache_key, program_name)
    program_descriptor = program.get_program_descriptor(request)
    context = {
        'program': program_descriptor,
        'disable_courseware_js': True,
        'uses_bootstrap': True,
        'on_course_outline_page': True,
        'program_slug': program_name,
    }
    return render_to_response('programs/programs.html', context)


@login_required
def show_program_bookmarks(request, program_name):
    """
    Display the programs page
    """
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 10))

    program = Program.objects.get(marketing_slug=program_name)
    bookmarks = Bookmark.objects.filter(
        course_key__in=program.get_course_locators(),
        user=request.user)
    page_data = bookmarks[(page - 1) * page_size: page * page_size]

    return render_to_response('programs/program_bookmarks.html', {
        "bookmarks": page_data,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(len(bookmarks) / page_size),
        "program_name": program_name,
    })
