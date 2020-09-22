
import unittest
from freezegun import freeze_time
from spike import get_student_deadlines_from_zoho_data


class ProjectDeadlinesUnitTest(unittest.TestCase):
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
