from django.contrib.auth.decorators import login_required
from edxmako.shortcuts import render_to_response
from ci_program.models import Program


@login_required
def show_programs(request, program_name):
    """
    Display the programs page
    """
    program = Program.objects.get(marketing_slug=program_name)
    program_descriptor = program.get_program_descriptor(request.user, request)
    enrolled_courses = request.user.courseenrollment_set.filter(is_active=True)
    enrolled_keys = set(enrolled_courses.values_list('course_id', flat=True))
    enrolled_keys = {str(key) for key in enrolled_keys}
    context = {
        'program': {
            'full_description': program_descriptor['full_description'],
            'length': program_descriptor['length'],
            'subtitle': program_descriptor['subtitle'],
            'name': program_descriptor['name'],
            'number_of_modules': len(enrolled_keys),
            'video': program_descriptor['video'],
            'image': program_descriptor['image'],
            'effort': program_descriptor['effort'],
            'modules': [m for m in program_descriptor['modules']
                        if m['course_key'].html_id() in enrolled_keys],
            'marketing_slug': program_name,
        },
        'disable_courseware_js': True,
        'uses_bootstrap': True,
        'on_course_outline_page': True,
        'program_slug': program_name,
    }
    return render_to_response('programs/programs.html', context)
