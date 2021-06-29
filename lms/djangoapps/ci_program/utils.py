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
    return now > project_deadline and not data['latest_submission']


def endswith(key):
    for field in FIELDS:
        if key.endswith(field):
            return key[:-len(field)], key[-len(field):]
    return None, None


def get_student_deadlines(student_email):
    cache_key = '%s_project_deadlines' % student_email
    if cache.get(cache_key):
        return cache.get(cache_key)

    student_record = get_student_record_from_zoho(student_email)
    if student_record:
        student_deadlines = get_student_deadlines_from_zoho_data(student_record)
        cache.set(cache_key, student_deadlines)
    else:
        student_deadlines = []
    return student_deadlines


def get_student_deadlines_from_zoho_data(zoho_record):
    student_data = {}
    for key, record in zoho_record.items():
        project_key, record_id = endswith(key)
        if not project_key:
            continue

        student_data.setdefault(project_key, {})
        student_data[project_key][record_id] = record

    # Filter Blank submission deadlines
    student_data = dict([
        (key, submission) for (key, submission) in student_data.items() if
        submission.get('submission_deadline')])

    sorted_student_data = sorted(
        student_data.values(),
        key=lambda k: (k.get('submission_deadline') or ''))

    for index, data in enumerate(sorted_student_data, start=1):
        data['name'] = "Milestone Project %s" % index
        data['overdue'] = is_overdue(data)
        data['next_project'] = False

    for data in sorted_student_data:
        if not data.get('submission_deadline'):
            continue

        project_deadline = datetime.strptime(data['submission_deadline'], '%Y-%m-%d')
        if project_deadline > datetime.now() and not data['latest_submission']:
            data['next_project'] = True
            break

    return sorted_student_data
