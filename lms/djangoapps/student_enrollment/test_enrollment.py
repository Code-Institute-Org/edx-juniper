from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from unittest.mock import patch
from datetime import date
import responses


from ci_program.models import Program
from student_enrollment.enrollment import Enrollment, SpecialisationEnrollment


class EnrollmentTestCase(TestCase):

    def setUp(self):
        self.today = date.today().isoformat()
        self.user = User.objects.create(
            username="fred",
            email="fred@fred.com"
        )

        self.common_curriculum = Program.objects.create(
            name="Common Curriculum",
            program_code="disdcc",
            specialization_for=""
        )

        self.sample_content = Program.objects.create(
            name="Sample Content",
            program_code="spsc",
            specialization_for=""
        )

        self.disd = Program.objects.create(
            name="Diploma in Software Development",
            program_code="disd",
            specialization_for=""
        )

        self.specialisation = Program.objects.create(
            name="Advanced Frontend",
            program_code="spadvfe",
            specialization_for="disdcc"
        )

        self.changed_specialisation = Program.objects.create(
            name="Predictive Analytics",
            program_code="sppredan",
            specialization_for="disdcc"
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
            responses.POST, settings.ZAPIER_SPECIALISATION_ENROLLMENT_URL,
            json={}, status=200
        )
        responses.add(
            responses.POST, settings.ZAPIER_ENROLLMENT_EXCEPTION_URL,
            json={}, status=200
        )

    @responses.activate
    def test_enrollment_disdcc_and_sample_content(self):

        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "fred fredriksson",
                        "Email": self.user.email,
                        "Programme_ID": "disdcc",
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # check that enrolled programmelist is empty initially
        self.assertEqual(list(self.user.program_set.all()), [])

        # run enrollment task
        Enrollment(dryrun=False).enroll()

        # verify that both CC and SPSC have been enrolled
        self.assertTrue(self.common_curriculum in list(self.user.program_set.all()))
        self.assertTrue(self.sample_content in list(self.user.program_set.all()))

        # verify that no specialisation, or another program (DISD), has been enrolled
        self.assertFalse(self.specialisation in list(self.user.program_set.all()))
        self.assertFalse(self.disd in list(self.user.program_set.all()))

    @responses.activate
    def test_enrollment_disd_and_no_sample_content(self):

        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "fred fredriksson",
                        "Email": self.user.email,
                        "Programme_ID": "disd",
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # check that enrolled programmelist is empty initially
        self.assertEqual(list(self.user.program_set.all()), [])

        # run enrollment task
        Enrollment(dryrun=False).enroll()

        # verify that DISD has been enrolled, buth SPSC hasn't
        self.assertTrue(self.disd in list(self.user.program_set.all()))
        self.assertFalse(self.sample_content in list(self.user.program_set.all()))

        # verify that no specialisation, or another program (CC), has been enrolled
        self.assertFalse(self.common_curriculum in list(self.user.program_set.all()))
        self.assertFalse(self.specialisation in list(self.user.program_set.all()))

    @responses.activate
    def test_enrollment_non_existent_program(self):
        # set student non-existent Programme_ID
        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "fred fredriksson",
                        "Email": self.user.email,
                        "Programme_ID": "dddd",
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # check that enrolled programmelist is empty initially
        self.assertEqual(list(self.user.program_set.all()), [])

        # verify that running Enrollment will raise an error message
        with self.assertLogs('student_enrollment.enrollment', level="INFO") as cm:
            Enrollment(dryrun=False).enroll()

        self.assertTrue(
            any("Could not find program: dddd" in msg for msg in cm.output)
        )

        # verify that no program has been enrolled
        self.assertEqual(list(self.user.program_set.all()), [])

    @responses.activate
    def test_specialisation_enrollment(self):
        self.assertEqual(list(self.user.program_set.all()), [])

        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "fred fredriksson",
                        "Email": self.user.email,
                        "Programme_ID": "disdcc",
                        "Specialisation_programme_id": "spadvfe",
                        "Specialization_Enrollment_Date": self.today,
                        "Specialisation_Change_Requested_Within_7_Days": False
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # enroll student into CC and SPSC first
        Enrollment(dryrun=False).enroll()

        # then, enroll into selected specialisation
        SpecialisationEnrollment(dryrun=False).enroll()

        # verify that CC program is unenrolled
        self.assertFalse(self.common_curriculum in list(self.user.program_set.all()))
        # verify that SPCC is still enrolled
        self.assertTrue(self.sample_content in list(self.user.program_set.all()))
        # verify that the specialisation is enrolled
        self.assertTrue(self.specialisation in list(self.user.program_set.all()))

    @responses.activate
    def test_specialisation_enrollment_date_in_the_future(self):
        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "fred fredriksson",
                        "Email": self.user.email,
                        "Lead_Status": "Enroll",
                        "Programme_ID": "disdcc",
                        "Specialisation_programme_id": "spadvfe",
                        "Specialization_Enrollment_Date": "2100-01-01",
                        "Specialisation_Change_Requested_Within_7_Days": False,
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # enroll student into CC and SPSC first
        Enrollment(dryrun=False).enroll()

        # then, enroll into selected specialisation
        SpecialisationEnrollment(dryrun=False).enroll()

        # verify that CC is still enrolled, as well as SPSC
        self.assertTrue(self.common_curriculum in list(self.user.program_set.all()))
        self.assertTrue(self.sample_content in list(self.user.program_set.all()))
        # verify that specialisation hasn't been enrolled
        self.assertFalse(self.specialisation in list(self.user.program_set.all()))

    @responses.activate
    def test_specialisation_enrollment_date_in_the_past(self):
        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "fred fredriksson",
                        "Email": self.user.email,
                        "Lead_Status": "Enroll",
                        "Programme_ID": "disdcc",
                        "Specialisation_programme_id": "spadvfe",
                        "Specialization_Enrollment_Date": "1900-01-01",
                        "Specialisation_Change_Requested_Within_7_Days": False,
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # enroll student into CC and SPSC first
        Enrollment(dryrun=False).enroll()

        # then, enroll into selected specialisation
        SpecialisationEnrollment(dryrun=False).enroll()

        # verify that CC program is unenrolled
        self.assertFalse(self.common_curriculum in list(self.user.program_set.all()))
        # verify that SPCC is still enrolled
        self.assertTrue(self.sample_content in list(self.user.program_set.all()))
        # verify that the specialisation is enrolled
        self.assertTrue(self.specialisation in list(self.user.program_set.all()))

    @responses.activate
    def test_specialisation_enrollment_non_existent_specialisation(self):
        # set student non-existent Specialisation_programme_id
        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "fred fredriksson",
                        "Email": self.user.email,
                        "Lead_Status": "Enroll",
                        "Programme_ID": "disdcc",
                        "Specialisation_programme_id": "xxxxxxx",
                        "Specialization_Enrollment_Date": self.today,
                        "Specialisation_Change_Requested_Within_7_Days": False,
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # enroll student into CC and SPSC first
        Enrollment(dryrun=False).enroll()

        # verify that running SpecialisationEnrollment will raise an error message
        with self.assertLogs('student_enrollment.enrollment', level="INFO") as cm:
            SpecialisationEnrollment(dryrun=False).enroll()

        self.assertTrue(
            any("Could not find specialisation: xxxxxxx" in msg for msg in cm.output)
        )

        # verify that CC is still enrolled, as well as SPSC
        self.assertTrue(self.common_curriculum in list(self.user.program_set.all()))
        self.assertTrue(self.sample_content in list(self.user.program_set.all()))

    @responses.activate
    def test_changed_specialisation_enrollment_crm_correct(self):
        self.assertEqual(list(self.user.program_set.all()), [])

        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "fred fredriksson",
                        "Email": self.user.email,
                        "Programme_ID": "spadvfe",
                        "Specialisation_programme_id": "sppredan",
                        "Specialisation_Change_Requested_Within_7_Days": True,
                        "Specialization_Enrollment_Date": self.today
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # enroll student into SPADVFE and SPSC first
        self.specialisation.enroll_student_in_program(self.user.email)
        self.sample_content.enroll_student_in_program(self.user.email)

        self.assertTrue(self.sample_content in list(self.user.program_set.all()))
        self.assertTrue(self.specialisation in list(self.user.program_set.all()))

        # then, run enrollment to enroll into new specialisation
        SpecialisationEnrollment(dryrun=False).enroll()

        # verify that previous specialisation is unenrolled
        self.assertFalse(self.specialisation in list(self.user.program_set.all()))
        # verify that SPCC is still enrolled
        self.assertTrue(self.sample_content in list(self.user.program_set.all()))
        # verify that the new specialisation is enrolled
        self.assertTrue(self.changed_specialisation in list(self.user.program_set.all()))


    @responses.activate
    def test_changed_specialisation_enrollment_crm_programme_id_has_disdcc(self):
        self.assertEqual(list(self.user.program_set.all()), [])

        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "fred fredriksson",
                        "Email": self.user.email,
                        "Programme_ID": "disdcc",
                        "Specialisation_programme_id": "sppredan",
                        "Specialisation_Change_Requested_Within_7_Days": True,
                        "Specialization_Enrollment_Date": self.today
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # enroll student into SPADVFE and SPSC first
        self.specialisation.enroll_student_in_program(self.user.email)
        self.sample_content.enroll_student_in_program(self.user.email)

        self.assertTrue(self.sample_content in list(self.user.program_set.all()))
        self.assertTrue(self.specialisation in list(self.user.program_set.all()))

        # then, run enrollment to enroll into new specialisation
        SpecialisationEnrollment(dryrun=False).enroll()

        # verify that previous specialisation is unenrolled
        self.assertFalse(self.specialisation in list(self.user.program_set.all()))
        # verify that SPCC is still enrolled
        self.assertTrue(self.sample_content in list(self.user.program_set.all()))
        # verify that the new specialisation is enrolled
        self.assertTrue(self.changed_specialisation in list(self.user.program_set.all()))