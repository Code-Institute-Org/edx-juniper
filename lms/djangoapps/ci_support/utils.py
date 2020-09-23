import logging
import requests

from django.conf import settings

ZOHO_CLIENT_ID = settings.ZOHO_CLIENT_ID
ZOHO_CLIENT_SECRET = settings.ZOHO_CLIENT_SECRET
ZOHO_REFRESH_TOKEN = settings.ZOHO_REFRESH_TOKEN
ZOHO_REFRESH_ENDPOINT = settings.ZOHO_REFRESH_ENDPOINT
ZOHO_STUDENTS_ENDPOINT = settings.ZOHO_STUDENTS_ENDPOINT
ZOHO_MENTORS_ENDPOINT = settings.ZOHO_MENTORS_ENDPOINT

ZAPIER_STUDENT_CARE_EMAIL_ENDPOINT = settings.ZAPIER_STUDENT_CARE_EMAIL_ENDPOINT

logger = logging.getLogger(__name__)


def get_student_record_from_zoho(email):
    """Fetch from Zoho all data for a student
    API documentation for this endpoint:
    https://www.zoho.com/crm/help/api/getsearchrecordsbypdc.html
    """
    if not settings.ZOHO_CLIENT_ID:
        logger.warning("ZOHO_CLIENT_ID is not set.")
        return {}

    params = {'email': email}
    student_resp = requests.get(
        ZOHO_STUDENTS_ENDPOINT + '/search',
        headers=get_auth_headers(),
        params=params)
    if student_resp.status_code != 200:
        return None
    return student_resp.json()['data'][0]


def get_a_students_mentor(email):
    """Fetch from Zoho all data for a student
    API documentation for this endpoint:
    https://www.zoho.com/crm/help/api/getsearchrecordsbypdc.html
    """
    params = {'email': email}
    student_resp = requests.get(
        ZOHO_STUDENTS_ENDPOINT + '/search',
        headers=get_auth_headers(),
        params=params)
    if student_resp.status_code != 200:
        return None
    return student_resp.json()['data'][0]['Assigned_Mentor']


def get_mentor_details(student_email):
    
    mentor = {
        "name": None,
        "email": None,
        "calendly": None,
    }
    
    student_record = get_student_record_from_zoho(student_email)
    assigned_mentor = student_record.get('Assigned_Mentor')
    
    if assigned_mentor:
        mentor_resp = requests.get(
            ZOHO_MENTORS_ENDPOINT + assigned_mentor['id'],
            headers=get_auth_headers())
        if mentor_resp.status_code == 200:
            mentor_dict = mentor_resp.json()['data'][0]
            mentor["name"] = mentor_dict["Name"]
            mentor["email"] = mentor_dict["Email"]
            mentor["calendly"] = mentor_dict["Calendar_URL"]
    return mentor


def get_access_token():
    refresh_resp = requests.post(ZOHO_REFRESH_ENDPOINT, params={
        "refresh_token": ZOHO_REFRESH_TOKEN,
        "client_id": ZOHO_CLIENT_ID,
        "client_secret": ZOHO_CLIENT_SECRET,
        "grant_type": "refresh_token"
    })
    return refresh_resp.json()['access_token']


def get_auth_headers():
    access_token = get_access_token()
    return {"Authorization": "Zoho-oauthtoken " + access_token}


def send_email_from_zapier(email_dict):
    return requests.post(
            ZAPIER_STUDENT_CARE_EMAIL_ENDPOINT,
            json=email_dict)
