from edxmako.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .utils import attempt_to_store_lrs_record


@login_required
def test_lrs(request):
    """
    View to test LRS implementation
    """
    data = {
        'activity_time': timezone.now()
        'actor': request.user.id
        'verb': 'completed'
        'activity_object': 'problem 1'
        'extra_data': {}
    }
    attempt_to_store_lrs_record.apply_async(args=[data])
    return render_to_response('ci_lrs/test_view.html')
