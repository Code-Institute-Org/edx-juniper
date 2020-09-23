
from django.test import TestCase
from freezegun import freeze_time
from .utils import get_student_deadlines_from_zoho_data
from .models import Program
from django.contrib.auth.models import User
from django.core import mail


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
        self.assertTrue('Username: student@codeinstitute.net' in email.body)
        program.save()
