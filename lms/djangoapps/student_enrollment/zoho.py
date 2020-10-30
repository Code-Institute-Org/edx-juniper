from itertools import count
import re
import requests
from django.conf import settings

CLIENT_ID = settings.ZOHO_CLIENT_ID
CLIENT_SECRET = settings.ZOHO_CLIENT_SECRET
REFRESH_TOKEN = settings.ZOHO_REFRESH_TOKEN
REFRESH_ENDPOINT = settings.ZOHO_REFRESH_ENDPOINT
COQL_ENDPOINT = settings.ZOHO_COQL_ENDPOINT

# COQL Queries
# LMS_Version can be removed from where clause when Ginkgo is decommissioned 
# Target decommission date: End of Q1 2020

ENROLL_QUERY = """
SELECT Email, Full_Name, Programme_Id
FROM Contacts
WHERE (
    (
        (Lead_Status = 'Enroll')
        AND (LMS_Version is 'Juniper')
    )
    AND (Programme_Id is not null)
)
LIMIT {page},{per_page}
"""
UNENROLL_QUERY = """
SELECT Email, Full_Name, Programme_Id
FROM Contacts
WHERE (
    (
        (LMS_Access_Status = 'To be removed')
        AND (Reason_for_Unenrollment is not null)
    )
    AND 
    (
        (Programme_Id is not null)
        AND (LMS_Version is 'Juniper')
    )
)
LIMIT {page},{per_page}
"""
ENROLL_IN_CAREERS_MODULE_QUERY = """
SELECT Email, Full_Name, Programme_Id
FROM Contacts
WHERE (
    (
        (Access_to_Careers_Module = 'Enroll')
        AND (LMS_Version is 'Juniper')
    )
    AND (Programme_Id is not null)
)
LIMIT {page},{per_page}
"""
RECORDS_PER_PAGE = 200


def get_students_to_be_enrolled():
    """Fetch from Zoho all students
    with a Lead Status of 'Enroll'
    API documentation for this endpoint:
    https://www.zohoapis.com/crm/v2/coql
    """
    students = []
    auth_headers = get_auth_headers()

    for page in count():
        query = ENROLL_QUERY.format(
                    page=page*RECORDS_PER_PAGE,
                    per_page=RECORDS_PER_PAGE)
        students_resp = requests.post(
            COQL_ENDPOINT,
            headers=auth_headers,
            json={"select_query":query})
        if students_resp.status_code != 200:
            return students

        students.extend(students_resp.json()['data'])
        if not students_resp.json()['info']['more_records']:
            return students


def get_students_to_be_unenrolled():
    """Fetch from Zoho all students
    with an LMS_Access_Status of 'To be removed'
    and a provided 'Reason for Removal'
    API documentation for this endpoint:
    https://www.zohoapis.com/crm/v2/coql
    """
    students = []
    auth_headers = get_auth_headers()

    for page in count():
        query = UNENROLL_QUERY.format(
                    page=page*RECORDS_PER_PAGE,
                    per_page=RECORDS_PER_PAGE)
        students_resp = requests.post(
            COQL_ENDPOINT,
            headers=auth_headers,
            json={"select_query":query})
        if students_resp.status_code != 200:
            return students

        students.extend(students_resp.json()['data'])
        if not students_resp.json()['info']['more_records']:
            return students


def get_students_to_be_enrolled_in_careers_module():
    """Fetch from Zoho all students
    with the Access_to_Careers_Module status
    of Enroll
    API documentation for this endpoint:
    https://www.zohoapis.com/crm/v2/coql
    """
    students = []
    auth_headers = get_auth_headers()

    for page in count():
        query = ENROLL_IN_CAREERS_MODULE_QUERY.format(
                    page=page*RECORDS_PER_PAGE,
                    per_page=RECORDS_PER_PAGE)
        students_resp = requests.post(
            COQL_ENDPOINT,
            headers=auth_headers,
            json={"select_query":query})
        if students_resp.status_code != 200:
            return students

        students.extend(students_resp.json()['data'])
        if not students_resp.json()['info']['more_records']:
            return students


def get_access_token():
    refresh_resp = requests.post(REFRESH_ENDPOINT, params={
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token"
    })
    return refresh_resp.json()['access_token']


def get_auth_headers():
    access_token = get_access_token()
    return {"Authorization": "Zoho-oauthtoken " + access_token}


def parse_course_of_interest_code(course_of_interest_code):
    """
    Course codes in Zoho are created based on the following criteria:

    <year_and_month><course_identifier>-<course_location>

    For example, a course of interest code of 1708FS-ON translates to:
    17 -> the year (2017)
    08 -> the month (August)
    FS -> Fullstack
    ON -> Online

    We need to strip away the excess and focus on the course identifier,
    in this case `FS`

    `course_of_interest_code` is the code that's retrieved from the
        student's Zoho record

    Returns the course_identifier without the year/month/location
    """
    regex_matcher = "\d|\-.*$"
    course_code = re.sub(regex_matcher, '', course_of_interest_code)
    return 'FS' if course_code == 'SBFS' else course_code


def update_student_record(zap_url, student_email):
    """
    Update the Zoho record for a student to indicate their new status
    within the LMS.

    `student_email` is the email of the student that is to be updated
    """

    params = {
        'student_email': student_email
    }
    response = requests.post(zap_url, data=params)
