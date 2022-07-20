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
SELECT Email, Full_Name, Programme_ID, Student_Source
FROM Contacts
WHERE ((
        (Lead_Status = 'Enroll') AND (Programme_ID is not null)
    )
    AND (
        (LMS_Version = 'Upgrade to Juniper') OR (LMS_Version = 'Juniper (learn.codeinstitute.net)')
    )
)
LIMIT {page},{per_page}
"""

UNENROLL_QUERY = """
SELECT Email, Full_Name, Programme_ID
FROM Contacts
WHERE ((
        (LMS_Access_Status = 'To be removed') AND (Reason_for_Unenrollment is not null)
    )
    AND (
        (Programme_ID is not null) AND (LMS_Version = 'Juniper (learn.codeinstitute.net)')
    )
)
LIMIT {page},{per_page}
"""

ENROLL_SPECIALISATION_QUERY = """
SELECT Email, Full_Name, Programme_ID, Specialisation_programme_id, Specialization_Enrollment_Date, Specialisation_Change_Requested_Within_7_Days
FROM Contacts
WHERE (Specialisation_Enrollment_Status = 'Approved') AND (Specialisation_programme_id is not null)
LIMIT {page},{per_page}
"""

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
