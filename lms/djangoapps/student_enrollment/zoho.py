from itertools import count
import re
import requests
from django.conf import settings

CLIENT_ID = settings.ZOHO_CLIENT_ID
CLIENT_SECRET = settings.ZOHO_CLIENT_SECRET
REFRESH_TOKEN = settings.ZOHO_REFRESH_TOKEN
REFRESH_ENDPOINT = settings.ZOHO_REFRESH_ENDPOINT
COQL_ENDPOINT = settings.ZOHO_COQL_ENDPOINT

CREDIT_RATING_BODY_LIST = settings.LMS_CREDIT_RATING_BODY

# NOTE: ZOHO COQL's IN operator requires a comma-separated sequence of strings, either wrapped
# in () or without any wrapping. Formatting a JSON array (from settings) into a COQL-acceptable format (no [] allowed)
# with Python requires either a simple string (for a single-element array) or a tuple (for multiple elements).
# If a tuple is used for a one-element array, it results in an (X,) format, which triggers a COQL query error.
# On the other hand, if the single element is injected into the query as a simple string, it "loses" its wrapping quotes,
# which again triggers a COQL query error.
#
# Hence the solution:
# - for single-element array, index the single element, and wrap it into parentheses AND quotes before injecting it
# - for multiple-element array, convert it into a tuple (of strings) and inject it

if len(CREDIT_RATING_BODY_LIST) == 1:
    CREDIT_RATING_BODY = '(\'{}\')'.format(CREDIT_RATING_BODY_LIST[0])
else:
    CREDIT_RATING_BODY = tuple(CREDIT_RATING_BODY_LIST)

# COQL Queries
# NOTE: "Excessive" parentheses added because Zoho COQL requires every subsequent
# chained condition to be wrapped in separate parentheses e.g. (A AND (B AND (C OR D)))
# otherwise a Syntax Error is received

ENROLL_QUERY = """
SELECT Email, Full_Name, Programme_ID, Student_Source
FROM Contacts
WHERE (
    Credit_Rating_Body in {credit_rating_body}
    AND (
    Lead_Status = 'Enroll'
    AND (
    Programme_ID is not null
)))
LIMIT {page},{per_page}
"""

UNENROLL_QUERY = """
SELECT Email, Full_Name, Programme_ID
FROM Contacts
WHERE (
    Credit_Rating_Body in {credit_rating_body}
    AND (
    LMS_Access_Status = 'To be removed'
    AND (
    Reason_for_Unenrollment is not null
)))
LIMIT {page},{per_page}
"""

ENROLL_SPECIALISATION_QUERY = """
SELECT Email, Full_Name, Programme_ID, Specialisation_programme_id, Specialization_Enrollment_Date, Specialisation_Change_Requested_Within_7_Days
FROM Contacts
WHERE (
    Credit_Rating_Body in {credit_rating_body}
    AND (
    Specialisation_Enrollment_Status = 'Approved'
    AND (
    Specialisation_programme_id is not null
)))
LIMIT {page},{per_page}
"""

# Currently not used - Careers enrolment handled by CRM + Zapier automation
ENROLL_IN_CAREERS_MODULE_QUERY = """
SELECT Email, Full_Name, Programme_ID
FROM Contacts
WHERE ((
        (Access_to_Careers_Module = 'Enroll') AND (Programme_ID is not null)
    )
    AND (LMS_Version = 'Juniper (learn.codeinstitute.net)')
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
            credit_rating_body=CREDIT_RATING_BODY,
            page=page*RECORDS_PER_PAGE,
            per_page=RECORDS_PER_PAGE
        )

        students_resp = requests.post(
            COQL_ENDPOINT,
            headers=auth_headers,
            json={"select_query":query})
        if students_resp.status_code != 200:
            return students

        students.extend(students_resp.json()['data'])
        if not students_resp.json()['info']['more_records']:
            return students


def get_students_to_be_enrolled_into_specialisation():
    """Fetch from Zoho all students
    with a Specialisation Enrollment Status of 'Approved'
    API documentation for this endpoint:
    https://www.zohoapis.com/crm/v2/coql
    """
    students = []
    auth_headers = get_auth_headers()

    for page in count():
        query = ENROLL_SPECIALISATION_QUERY.format(
            credit_rating_body=CREDIT_RATING_BODY,
            page=page*RECORDS_PER_PAGE,
            per_page=RECORDS_PER_PAGE,
        )
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
            credit_rating_body=CREDIT_RATING_BODY,
            page=page*RECORDS_PER_PAGE,
            per_page=RECORDS_PER_PAGE,
        )
        students_resp = requests.post(
            COQL_ENDPOINT,
            headers=auth_headers,
            json={"select_query":query})
        if students_resp.status_code != 200:
            return students

        students.extend(students_resp.json()['data'])
        if not students_resp.json()['info']['more_records']:
            return students


# Currently not used
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
