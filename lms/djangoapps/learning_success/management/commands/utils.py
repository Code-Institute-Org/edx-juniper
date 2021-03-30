from itertools import count
import requests

from django.conf import settings

from student_enrollment.zoho import get_auth_headers

RECORDS_PER_PAGE = 200
COQL_ENDPOINT = settings.ZOHO_COQL_ENDPOINT
STUDENT_PROGRAMMES_QUERY = """
SELECT Email, Programme_ID, LMS_Version
FROM Contacts
WHERE Programme_ID is not null
LIMIT {page},{per_page}
"""


def get_students_programme_ids_and_lms_version():
    """Fetch from Zoho all students
    with an LMS_Access_Status of 'To be removed'
    and a provided 'Reason for Removal'
    API documentation for this endpoint:
    https://www.zohoapis.com/crm/v2/coql
    """
    students = []
    auth_headers = get_auth_headers()

    for page in count():
        query = STUDENT_PROGRAMMES_QUERY.format(
                    page=page*RECORDS_PER_PAGE,
                    per_page=RECORDS_PER_PAGE)
        students_resp = requests.post(
            COQL_ENDPOINT,
            headers=auth_headers,
            json={"select_query":query})
        if students_resp.status_code != 200:
            return {student.get('Email'): student.get('Programme_ID')
                    for student in students}

        students.extend(students_resp.json()['data'])
        if not students_resp.json()['info']['more_records']:
            return students
