from datetime import datetime, timedelta
import json
import logging
import pymongo
import requests

from django.conf import settings
from django.core.management.base import BaseCommand

from ci_program.api import get_program_by_program_code

log = logging.getLogger(__name__)

HUBSPOT_CONTACTS_ENDPOINT = settings.HUBSPOT_CONTACTS_ENDPOINT
HUBSPOT_API_KEY = settings.HUBSPOT_API_KEY

CLIENT_ID = settings.LP_ZOHO_CLIENT_ID
CLIENT_SECRET = settings.LP_ZOHO_CLIENT_SECRET
REFRESH_TOKEN = settings.LP_ZOHO_REFRESH_TOKEN
REFRESH_ENDPOINT = settings.ZOHO_REFRESH_ENDPOINT
CHALLENGE_ENDPOINT = settings.LP_ZOHO_CHALLENGE_ENDPOINT

REFRESH_RETRIES = settings.ZOHO_REFRESH_RETRIES
REFRESH_SLEEP_SECS = settings.ZOHO_REFRESH_SLEEP_SECS

# Agreed list of names for coding challenges
# Can remove this dict when we associate challenges with programme
CODING_CHALLENGES = [
    "lesson_1_challenge_1",
    "lesson_1_challenge_2",
    "lesson_2_challenge_1",
    "lesson_2_challenge_2",
    "lesson_2_challenge_3",
    "lesson_2_challenge_4",
    "lesson_3_challenge_1",
    "lesson_3_challenge_2",
    "lesson_3_challenge_3",
    "lesson_4_challenge_1",
    "lesson_4_challenge_2",
    "lesson_4_challenge_3",
    "lesson_5_challenge_1",
    "lesson_5_challenge_2",
    "lesson_5_challenge_3"
]

class Command(BaseCommand):
    help = 'Post the results of challenge submissions submitted in the last day for a given coding challenge program'

    def add_arguments(self, parser):
        parser.add_argument('program_code', type=str)
        parser.add_argument('--dbname', type=str, default='challenges')

    def handle(self, program_code, **kwargs):
        self.db = settings.MONGO_CLIENT[kwargs['dbname']]
        self.collection = self.db["challenges"]
        self.program_code = program_code
        self.students = self.get_students()
        self.challenges = self.get_challenges()

        self.export_challenges_submitted()

    def get_students(self):
        """Get students enrolled in a particular program
        Return dict in following format {id: email}
        """
        program = get_program_by_program_code(self.program_code)
        enrolled_students = program.enrolled_students.all()
        return {student.id: student.email for student in enrolled_students}

    def get_challenges(self):
        """Return dict of challenges in following format {id: name}"""
        challenges_query = self.collection.find({"name": {"$in": CODING_CHALLENGES}})
        challenges = {challenge.get("_id"): challenge.get("name") for challenge in challenges_query}
        return challenges

    def get_submissions(self, challenges, students, submitted_since):
        """Get submissions for challenges submitted by enrolled students
        within a particular time frame e.g. submitted_since_yesterday
        """
        submissions_since_yday = self.db.submissions.find(
            {
                "submitted": {"$gte": submitted_since},
                "challenge_id": {"$in": list(challenges.keys())},
                "user_id": {"$in": list(students.keys())}
            }
        ).sort("submitted", pymongo.DESCENDING)
        return submissions_since_yday


    def get_results_for_all_students(self):
        """Get results from challenge submissions for all students
        enrolled in a given program.

        The sequence of events are as follows:
        1. Get all students enrolled in program
        2. Get ids for all challenges in coding challenge program
        3. Get all submissions for coding challenges,
        submitted by an enrolled student in the last 25 hours.
        Allowing an additional hour to account for any submissions that occur while script is running.
        4. Submissions are returned sorted by submission date, latest submission first.
        We only require the result of the latest submission of a particular challenge
        i.e. first submission found in results (which is sorted by latest submission first)
        Previous submissions are skipped
        5. Format for HubSpot
        results = [
            "student@email.com" : {
                "lesson_1_challenge_1" : "Pass"
            }
        ]
        """

        one_day_ago = datetime.today() - timedelta(days=1)
        submissions_since_yday = self.get_submissions(
            self.challenges, self.students, one_day_ago)

        results = {}
        for submission in submissions_since_yday:
            email = self.students[submission.get("user_id")]
            if email not in results:
                results.setdefault(email, {})

            challenge = self.challenges[submission.get("challenge_id")]
            result = 'Pass' if submission.get("passed") else 'Fail'

            if challenge not in results[email]:
                results[email][challenge] = result

        return results


    def post_to_hubspot(self, endpoint, student, properties):
        """Post results of challenge submissions to the student profiles on HubSpot"""
        url = "%s/email/%s/profile?hapikey=%s" % (
            endpoint, student, HUBSPOT_API_KEY)
        headers = {
            "Content-Type": "application/json"
        }
        data = json.dumps({
            "properties": properties
        })
        response = requests.post(
            data=data, url=url, headers=headers)
        if response.status_code == 204:
            log.info("Challenge results recorded for: %s" % (student))
        else:
            log.info(
                "Attempt to send challenge results for %s to HubSpot " \
                "failed with following response %s: %s" % (
                    student, response.status_code, response.json))


    def get_access_token(self):
        """Retrieve a Zoho CRM access token.
        This may fail due to various network/throttling issues, so we will
        retry
        """
        for attempt in range(REFRESH_RETRIES):
            try:
                refresh_resp = requests.post(REFRESH_ENDPOINT, params={
                    "refresh_token": REFRESH_TOKEN,
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "grant_type": "refresh_token"
                })
                log.info("Successfully retrieved Zoho token")
                return refresh_resp.json()['access_token']
            except KeyError as e:
                log.info(
                    "ERROR: Getting Zoho token attempt %s out of %s " \
                    "failed with the exception: %s" % (attempt, REFRESH_RETRIES, e)
                )
                time.sleep(REFRESH_SLEEP_SECS)


    def get_auth_headers(self):
        """Return HTTP headers to authenticate against Zoho CRM."""
        access_token = self.get_access_token()
        return {"Authorization": "Zoho-oauthtoken " + access_token}


    def post_to_learningpeople(self, CHALLENGE_ENDPOINT, auth_headers, json, student):
        response = requests.post(
            CHALLENGE_ENDPOINT,
            headers=auth_headers,
            json=json
        )
        if response.status_code == 200:
            log.info("Challenge results recorded for: %s" % (student))
        else:
            log.info(
                "Attempt to send challenge results for %s to LP " \
                "failed with the following response %s: %s" % (
                    student, response.status_code, response.json))  


    def export_challenges_submitted(self):
        """Get results for all students and prepare those results in a format
        that can be posted to Zoho if student is on an Learning People program,
        else HubSpot profiles for all other students
        """
        results_for_all_students = self.get_results_for_all_students()
        if self.program_code == "LPCC":
            auth_headers_for_zoho = self.get_auth_headers()
            for student, results in results_for_all_students.items():
                json_for_zoho = {
                    "data": [{"Email": student}],
                    "duplicate_check_fields": ["Email"],
                }
                for challenge_name, result in results.items():
                    json_for_zoho["data"][0][challenge_name] = result

                self.post_to_learningpeople(
                    CHALLENGE_ENDPOINT,
                    auth_headers_for_zoho,
                    json_for_zoho,
                    student
                )
        else:
            for student, results in results_for_all_students.items():
                properties = [{
                    "property": "email",
                    "value": student
                }]
                for challenge_name, result in results.items():
                    properties.append({
                        "property": challenge_name,
                        "value": result
                    })
                self.post_to_hubspot(HUBSPOT_CONTACTS_ENDPOINT, student, properties)


