import json
import logging
import pymongo
import requests

from django.http import JsonResponse
from django.conf import settings


def _smoke_test_lrs():
        lrs_client = settings.LRS_MONGO_CLIENT
        lrs_db = settings.LRS_MONGO_DB
        lrs_client[lrs_db].command("ping")


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

    access_token = refresh_resp.json()['access_token']

    # query ZOHO COQL DB
    auth_headers = {"Authorization": "Zoho-oauthtoken " + access_token}
    query = """ SELECT First_Name FROM Contacts WHERE Last_Name = 'Test' """

    coql_response = requests.post(
        coql_endpoint,
        headers=auth_headers,
        json={"select_query": query}
    )

    if not coql_response.status_code or coql_response.status_code != 200:
        raise Exception("Invalid COQL endpoint or invalid test query")


SMOKE_TEST = {
    "lrs": _smoke_test_lrs,
    "zoho": _smoke_test_zoho,
}


def run_smoke_tests(request):
    status = None
    results = dict()
    success = False

    for name, test in SMOKE_TEST.items():
        try:
            test()
            results[name] = {"success": True}
        except Exception as e:
            logging.exception("Smoke Test %s failed", name)
            results[name] = {"success": False}
            success = False

    if success:
        status = 200
    else:
        status = 400

    return JsonResponse(results, status=status)
