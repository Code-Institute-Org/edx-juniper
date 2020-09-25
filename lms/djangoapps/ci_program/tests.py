
from django.urls import reverse
from django.test import TestCase, override_settings
from freezegun import freeze_time
from .utils import get_student_deadlines_from_zoho_data
from .models import Program
from django.contrib.auth.models import User
from django.core import mail
import responses


class ProjectDeadlinesUnitTest(TestCase):
    """ Testing creating the project deadlines data from the ZOHO api data """
    def setUp(self):
        self.max_diff = None

    @freeze_time("2020-10-01 13:00")
    def test_parse(self):
        self.api_data = {
            'Interactive_submission_deadline': '2020-10-01',
            'Interactive_latest_submission': None,
            'User_Centric_submission_deadline': '2020-09-01',
            'User_Centric_latest_submission': '{}',
            'Data_Centric_submission_deadline': '2020-11-01',
            'Data_Centric_latest_submission': None,
        }
        result = get_student_deadlines_from_zoho_data(self.api_data)

        self.assertEqual([
            {'name': 'Milestone Project 1',
             'submission_deadline': '2020-09-01',
             'latest_submission': '{}',
             'overdue': False,
             'next_project': False},

            {'name': 'Milestone Project 2',
             'submission_deadline': '2020-10-01',
             'latest_submission': None,
             'overdue': True,
             'next_project': False},

            {'name': 'Milestone Project 3',
             'submission_deadline': '2020-11-01',
             'latest_submission': None,
             'overdue': False,
             'next_project': True},
        ], result)

    @freeze_time("2020-08-01 13:00")
    def test_next_project(self):
        self.api_data = {
            'Interactive_submission_deadline': '2020-10-01',
            'Interactive_latest_submission': '{}',
            'User_Centric_submission_deadline': '2020-09-01',
            'User_Centric_latest_submission': '{}',
            'Data_Centric_submission_deadline': '2020-11-01',
            'Data_Centric_latest_submission': None,
        }
        result = get_student_deadlines_from_zoho_data(self.api_data)

        self.assertEqual([
            {'name': 'Milestone Project 1',
             'submission_deadline': '2020-09-01',
             'latest_submission': '{}',
             'overdue': False,
             'next_project': False},

            {'name': 'Milestone Project 2',
             'submission_deadline': '2020-10-01',
             'latest_submission': '{}',
             'overdue': False,
             'next_project': False},

            {'name': 'Milestone Project 3',
             'submission_deadline': '2020-11-01',
             'latest_submission': None,
             'overdue': False,
             'next_project': True},
        ], result)

    def test_program_email_template(self):
        program = Program(program_code_friendly_name='nonexistant')
        program.enrollment_type = 0

        template_location, subject = program.email_template_location
        self.assertEqual('LMS', subject)
        self.assertEqual('emails/default/enrollment_email.html', template_location)

    def test_send_email(self):
        program = Program(program_code_friendly_name='default')
        student = User(username='student', email='student@codeinstitute.net')

        self.assertEqual(0, len(mail.outbox))
        program.send_email(student, 0, 'newpassword')
        self.assertEqual(1, len(mail.outbox))

        email = mail.outbox[0]
        self.assertIn('Username: student@codeinstitute.net', email.body)

    @responses.activate
    @override_settings(ZOHO_CLIENT_ID='TEST_API_KEY',
                       ZOHO_STUDENTS_ENDPOINT='http://api.zoho.test',
                       ZOHO_REFRESH_ENDPOINT='http://auth.zoho.test')
    def test_show_programs_blank_zoho_user(self):
        student = User.objects.create_user(username='student',
                                           password="password",
                                           email='student@codeinstitute.net')
        # This is one way of writing tests for APIs.
        # Since the API is relatively simple, the test setup is not too
        # complex. Integration tests would be used to ensure the API is
        # correctly accessed when run in a live environment.
        responses.add(
            'POST',
            ('http://auth.zoho.test/?grant_type=refresh_token&'
             'client_id=TEST_API_KEY'),
            json={"access_token": "TOKEN"})

        responses.add(
            'GET',
            'http://api.zoho.test/search',
            status=404)

        Program.objects.create(
            name='test_program', marketing_slug='test_program')

        # gotta use this exact middleware to avoid an error with the other edx
        # authentication backends
        self.client.force_login(student,
                                'bridgekeeper.backends.RulePermissionBackend')
        response = self.client.get(
                reverse('show_programs',
                        kwargs={'program_name': 'test_program'}))

        self.assertEqual(200, response.status_code)
