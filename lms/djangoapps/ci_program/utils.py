from collections import OrderedDict
from datetime import datetime, timedelta

from django.core.cache import cache

from ci_support.utils import get_student_record_from_zoho

CACHE_TIMEOUT_SECONDS = 24 * 60 * 60
FIELDS = ['latest_submission', 'submission_deadline']


def is_overdue(data):
    """ Check if the project submission deadline has passed"""
    submission_deadline = data.get('submission_deadline')
    # In case no deadline is set in the CRM
    if not submission_deadline:
        return False

    now = datetime.now()
    project_deadline = datetime.strptime(submission_deadline, '%Y-%m-%d')
    project_deadline = project_deadline + timedelta(hours=12)
    return now > project_deadline and not data['submission']
