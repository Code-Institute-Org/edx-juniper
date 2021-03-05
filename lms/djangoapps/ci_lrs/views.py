from edxmako.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required

from .utils import store_lrs_record


@login_required
def test_lrs(request):
    """
    View to test LRS implementation
    """
    actor = request.user.id
    verb = 'completed'
    activity_object = 'problem 1'

    store_lrs_record(actor, verb, activity_object)

    return render_to_response('ci_lrs/test_view.html')
