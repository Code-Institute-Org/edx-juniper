import json
import logging
import pymongo
import requests

from django.http import JsonResponse
from django.conf import settings

from .djangoapps.student_enrollment.zoho import get_auth_headers, get_access_token


def run_smoke_tests():
    response = JsonResponse({
        "lrs": _smoke_test_lrs(),
        "zoho": _smoke_test_zoho(),
        "hubspot": _smoke_test_hubspot(),
        "zapier": _smoke_test_zapier(),
        "redis": _smoke_test_redis(),
        "sentry": _smoke_test_sentry(),
        "elasticsearch": _smoke_test_elasticsearch()
    })

    return response


def _smoke_test_lrs():
    lrs_db = settings.LRS_MONGO_DB
    try:
        lrs_client = settings.LRS_MONGO_CLIENT
        try:
            lrs_client[lrs_db].command("ping")
            return {"success": True}
        except Exception as e:
            logging.exception("Unable to ping database")
            return {"success": False}
    except pymongo.errors.OperationFailure:
        logging.exception('MongoDB Connection error.')
        return {"success": False}


def _smoke_test_zoho():
    client_id = settings.ZOHO_CLIENT_ID
    refresh_token = settings.ZOHO_REFRESH_TOKEN
    client_secret = settings.ZOHO_CLIENT_SECRET
    refresh_endpoint = settings.ZOHO_REFRESH_ENDPOINT
    coql_endpoint = settings.ZOHO_COQL_ENDPOINT

    # get refresh token
    refresh_resp = requests.post(refresh_endpoint, params={
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token"
    })

    try:
        access_token = refresh_resp.json()['access_token']
    except requests.exceptions.JSONDecodeError:
        logging.error("ZOHO: invalid token refresh endpoint")
        return {"success": False}
    except KeyError:
        logging.error("ZOHO: invalid API credentials")
        return {"success": False}

    # query ZOHO COQL DB
    auth_headers = {"Authorization": "Zoho-oauthtoken " + access_token}
    query = """ SELECT First_Name FROM Contacts WHERE Last_Name = 'Test' """

    coql_response = requests.post(
        coql_endpoint,
        headers=auth_headers,
        json={"select_query": query}
    )

    if not coql_response.status_code or coql_response.status_code != 200:
        logging.error("Invalid COQL endpoint or invalid test query")
        return {"success": False}
    else:
        return {"success": True}


def _smoke_test_hubspot():
    pass


def _smoke_test_zapier():
    pass


def _smoke_test_redis():
    pass


def _smoke_test_sentry():
    pass


def _smoke_test_elasticsearch():
    pass


_