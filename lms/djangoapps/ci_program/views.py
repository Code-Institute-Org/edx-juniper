
import math

from django.shortcuts import redirect, reverse
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from edxmako.shortcuts import render_to_response
from ci_program.models import Program
from openedx.core.djangoapps.bookmarks.models import Bookmark
from django.http import Http404
from django.http import HttpResponseRedirect


@login_required
def show_programs(request, program_name):
    """
    Display the programs page
    """
    student_email = request.user.email
    cache_key = '%s_program_name' % student_email

    try:
        program = Program.objects.get(marketing_slug=program_name)
    except Program.DoesNotExist:
        raise Http404
    if request.user not in program.enrolled_students.all():
        return redirect(reverse('dashboard'))

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
    bookmark_sort_by_desc = request.COOKIES.get('bookmark_sort_by_desc', 'false')

    if bookmark_sort_by_desc == 'true':
        bookmarks = Bookmark.objects.filter(user=request.user).order_by('-created')
    else:
        bookmarks = Bookmark.objects.filter(user=request.user)
    
    page_data = bookmarks[(page - 1) * page_size: page * page_size]

    return render_to_response('programs/program_bookmarks.html', {
        "bookmarks": page_data,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(len(bookmarks) / page_size),
        "program_name": program_name,
        "bookmark_sort_by_desc": bookmark_sort_by_desc,
    })


@login_required
def set_bookmark_preference(request, program_name):
    """
    Set the bookmark preference for sort by date desc
    """
    sort_by_desc = request.POST.get('bookmark_preference', 'false')

    response = HttpResponseRedirect(reverse('show_program_bookmarks', args=[program_name]))
    
    if sort_by_desc == 'true':
        response.set_cookie('bookmark_sort_by_desc', 'true', max_age=30 * 24 * 60 * 60)  # Expires in 30 days
    else:
        response.set_cookie('bookmark_sort_by_desc', 'false', max_age=30 * 24 * 60 * 60)

    return response