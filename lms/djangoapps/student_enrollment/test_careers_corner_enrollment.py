import responses
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase

from ci_program.models import Program
from student_enrollment.enrollment import Enrollment
from student_enrollment.enroll_students_in_careers_module import CareersCornerEnrollment


class CareersCornerEnrollmentTestCase(TestCase):

    def setUp(self):
        self.user_1 = User.objects.create(
            username="fred",
            email="fred@fred.com"
        )

        self.user_2 = User.objects.create(
            username="bob",
            email="bob@bob.com"
        )

        self.careers_corner = Program.objects.create(
            name="Careers Corner",
            program_code="careerscorner",
        )

        self.l3_bootcamp = Program.objects.create(
            name="L3 Bootcamp",
            program_code="l3bootcamp",
        )

        self.l3_disd = Program.objects.create(
            name="L3 Diploma in Software Development",
            program_code="l3disd"
        )

        responses.add(
            responses.POST, settings.ZOHO_REFRESH_ENDPOINT,
            json={"access_token": "12345"}, status=200
        )
        responses.add(
            responses.POST, settings.ZAPIER_ENROLLMENT_URL,
            json={}, status=200
        )
        responses.add(
            responses.POST, settings.ZAPIER_ENROLLMENT_EXCEPTION_URL,
            json={}, status=200
        )

    @responses.activate
    def test_corner_enrollment_single_student(self):

        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "fred fredriksson",
                        "Email": self.user_1.email,
                        "Programme_ID": "l3disd",
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # check that enrolled programme list is empty initially
        self.assertEqual(list(self.user_1.program_set.all()), [])

        # enrol student in L3DISD and verify enrolment
        self.l3_disd.enroll_student_in_program(self.user_1.email)
        self.assertTrue(self.l3_disd in list(self.user_1.program_set.all()))
        self.assertEqual(len(list(self.user_1.program_set.all())), 1)

        # run Careers Corner enrolment
        with self.assertLogs('ci_program.models', level="INFO") as cm:
            CareersCornerEnrollment(dryrun=False).enroll()

        # check log message for successful enrolment
        log_message = "fred@fred.com was enrolled in Careers Corner"
        self.assertTrue(
            any(log_message in msg for msg in cm.output)
        )

        # verify that CAREERSCORNER has been enrolled
        self.assertTrue(self.careers_corner in list(self.user_1.program_set.all()))
        self.assertEqual(len(list(self.user_1.program_set.all())), 2)

    @responses.activate
    def test_corner_enrollment_two_eligible_students(self):

        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "fred fredriksson",
                        "Email": self.user_1.email,
                        "Programme_ID": "l3disd",
                    },
                    {
                        "Full_Name": "bob bobbins",
                        "Email": self.user_2.email,
                        "Programme_ID": "l3bootcamp",
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # check that respective enrolled programme lists are empty initially
        self.assertEqual(list(self.user_1.program_set.all()), [])
        self.assertEqual(list(self.user_2.program_set.all()), [])

        # enrol student 1 in L3DISD and verify enrolment
        self.l3_disd.enroll_student_in_program(self.user_1.email)
        self.assertTrue(self.l3_disd in list(self.user_1.program_set.all()))
        self.assertEqual(len(list(self.user_1.program_set.all())), 1)

        # enrol student 2 in L3BOOTCAMP and verify enrolment
        self.l3_bootcamp.enroll_student_in_program(self.user_2.email)
        self.assertTrue(self.l3_bootcamp in list(self.user_2.program_set.all()))
        self.assertEqual(len(list(self.user_2.program_set.all())), 1)

        # run Careers Corner enrolment
        with self.assertLogs('ci_program.models', level="INFO") as cm:
            CareersCornerEnrollment(dryrun=False).enroll()

        # check log message for successful enrolment of first student
        first_log_message = "fred@fred.com was enrolled in Careers Corner"
        self.assertTrue(
            any(first_log_message in msg for msg in cm.output)
        )

        # check log message for successful enrolment of second student
        second_log_message = "bob@bob.com was enrolled in Careers Corner"
        self.assertTrue(
            any(second_log_message in msg for msg in cm.output)
        )

        # verify that CAREERSCORNER has been enrolled for the first student
        self.assertTrue(self.careers_corner in list(self.user_1.program_set.all()))
        self.assertEqual(len(list(self.user_1.program_set.all())), 2)

        # verify that CAREERSCORNER has been enrolled for the second student
        self.assertTrue(self.careers_corner in list(self.user_2.program_set.all()))
        self.assertEqual(len(list(self.user_2.program_set.all())), 2)

    @responses.activate
    def test_corner_enrollment_two_eligible_students_one_already_enrolled(self):

        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "fred fredriksson",
                        "Email": self.user_1.email,
                        "Programme_ID": "l3disd",
                    },
                    {
                        "Full_Name": "bob bobbins",
                        "Email": self.user_2.email,
                        "Programme_ID": "l3bootcamp",
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # check that respective enrolled programme lists are empty initially
        self.assertEqual(list(self.user_1.program_set.all()), [])
        self.assertEqual(list(self.user_2.program_set.all()), [])

        # enrol student 1 in L3DISD and verify enrolment
        self.l3_disd.enroll_student_in_program(self.user_1.email)
        self.assertTrue(self.l3_disd in list(self.user_1.program_set.all()))
        self.assertEqual(len(list(self.user_1.program_set.all())), 1)

        # enrol student 2 in L3BOOTCAMP and CAREERSCORNER and verify enrolment
        self.l3_bootcamp.enroll_student_in_program(self.user_2.email)
        self.careers_corner.enroll_student_in_program(self.user_2.email)
        self.assertTrue(self.l3_bootcamp in list(self.user_2.program_set.all()))
        self.assertTrue(self.careers_corner in list(self.user_2.program_set.all()))
        self.assertEqual(len(list(self.user_2.program_set.all())), 2)

        # run Careers Corner enrolment
        with self.assertLogs('ci_program.models', level="INFO") as cm:
            CareersCornerEnrollment(dryrun=False).enroll()

        # check log message for successful enrolment of first student
        first_log_message = "fred@fred.com was enrolled in Careers Corner"
        self.assertTrue(
            any(first_log_message in msg for msg in cm.output)
        )

        # check that NO enrolment log message was raised for second student
        # (because already enrolled, so enrolment was skipped)
        second_log_message = "bob@bob.com was enrolled in Careers Corner"
        self.assertFalse(
            any(second_log_message in msg for msg in cm.output)
        )

        # verify that CAREERSCORNER has been enrolled for the first student
        self.assertTrue(self.careers_corner in list(self.user_1.program_set.all()))
        self.assertEqual(len(list(self.user_1.program_set.all())), 2)

        # verify that both L3BOOTCAMP and CAREERSCORNER are still there for the second student
        self.assertTrue(self.l3_bootcamp in list(self.user_2.program_set.all()))
        self.assertTrue(self.careers_corner in list(self.user_2.program_set.all()))
        self.assertEqual(len(list(self.user_2.program_set.all())), 2)

    @responses.activate
    def test_corner_enrollment_two_students_one_not_eligible(self):

        # simulate Zoho response for only one (the first) student,
        # meaning that the second one has been filtered out by the
        # COQL query (Programme ID not eligible or/and Is_Active = false))
        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "fred fredriksson",
                        "Email": self.user_1.email,
                        "Programme_ID": "l3disd",
                    }
                ],
                "info": {"more_records": False}
            },
            status=200)

        # check that respective enrolled programme lists are empty initially
        self.assertEqual(list(self.user_1.program_set.all()), [])
        self.assertEqual(list(self.user_2.program_set.all()), [])

        # enrol student 1 in L3DISD and verify enrolment
        self.l3_disd.enroll_student_in_program(self.user_1.email)
        self.assertTrue(self.l3_disd in list(self.user_1.program_set.all()))
        self.assertEqual(len(list(self.user_1.program_set.all())), 1)

        # enrol student 2 in L3DISD verify enrolment
        self.l3_disd.enroll_student_in_program(self.user_2.email)
        self.assertTrue(self.l3_disd in list(self.user_2.program_set.all()))
        self.assertEqual(len(list(self.user_2.program_set.all())), 1)

        # run Careers Corner enrolment
        with self.assertLogs('ci_program.models', level="INFO") as cm:
            CareersCornerEnrollment(dryrun=False).enroll()

        # check log message for successful enrolment of first student
        first_log_message = "fred@fred.com was enrolled in Careers Corner"
        self.assertTrue(
            any(first_log_message in msg for msg in cm.output)
        )

        # check that NO enrolment log message was raised for second student
        # (because enrolment didn't run for them - not eligible)
        second_log_message = "bob@bob.com was enrolled in Careers Corner"
        self.assertFalse(
            any(second_log_message in msg for msg in cm.output)
        )

        # verify that CAREERSCORNER has been enrolled for first student
        self.assertTrue(self.careers_corner in list(self.user_1.program_set.all()))
        self.assertEqual(len(list(self.user_1.program_set.all())), 2)

        # verify that both CAREERSCORNER has NOT been enrolled for the second student
        self.assertFalse(self.careers_corner in list(self.user_2.program_set.all()))
        self.assertEqual(len(list(self.user_2.program_set.all())), 1)

    @responses.activate
    def test_corner_enrollment_nonexistent_email(self):

        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "john smith",
                        "Email": "john@smith.com",
                        "Programme_ID": "l3disd",
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # run Careers Corner enrolment
        with self.assertLogs('student_enrollment.enroll_students_in_careers_module', level="INFO") as cm:
            CareersCornerEnrollment(dryrun=False).enroll()

        # check error message is raised
        error_message = "** User john@smith.com does not exist in the LMS **"
        self.assertTrue(
            any(error_message in msg for msg in cm.output)
        )
