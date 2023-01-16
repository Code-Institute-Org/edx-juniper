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

        # NOTE: sample/support programmes moved to the top of the setup
        # as they need to be created before their referencing in main programmes
        
        self.sample_content = Program.objects.create(
            name="Sample Content",
            program_code="spsc",
        )

        # sample content for diwadexp
        self.diwad_sample_content = Program.objects.create(
            name="Sample Content Diwad",
            program_code="diwadspsc",
        )

        self.diwad_learning_supports = Program.objects.create(
            name="Diploma in Web App Development Learning Supports 1",
            program_code="diwadls",
            # intentional whitespaces and single quotes for testing!
            support_program_sources="   ' Eligible College 1', Eligible College 2  "
        )

        self.diwad_second_learning_supports = Program.objects.create(
            name="Diploma in Web App Development Learning Supports 2",
            program_code="diwadls2",
            # intentional whitespaces, double quotes and newline for testing!
            support_program_sources="Eligible College 3  , \r\n\"Eligible College 1 \""
        )

        # eligible colleges different than for diwadls and diwadls2
        self.diwad_different_learning_supports = Program.objects.create(
            name="Diploma in Web App Development Learning Supports 3",
            program_code="diwadls3",
            # intentional whitespaces for testing!
            support_program_sources="  Eligible College 3   "
        )

        # eligible colleges empty - unrestricted learning support
        self.diwad_open_learning_supports = Program.objects.create(
            name="Diploma in Web App Development Open Learning Supports",
            program_code="diwadlsopen",
            # sources empty => no enrolment restrictions
            support_program_sources=""
        )

        self.common_curriculum = Program.objects.create(
            name="Common Curriculum",
            program_code="disdcc"
        )
        self.common_curriculum.sample_content.set([self.sample_content])

        self.disd = Program.objects.create(
            name="Diploma in Software Development",
            program_code="disd"
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

        self.diwad_old = Program.objects.create(
            name="Diploma in Web Application Development",
            program_code="diwad"
        )

        self.diwad_new = Program.objects.create(
            name="Diploma in Web App Development",
            program_code="diwad220407",
        )
        self.diwad_new.support_programs.set([self.diwad_learning_supports])

        self.diwad221005 = Program.objects.create(
            name="L5 Diploma in Web App Development",
            program_code="diwad221005",
        )
        self.diwad221005.support_programs.set([
            self.diwad_learning_supports,
            self.diwad_second_learning_supports,
            self.diwad_different_learning_supports
        ])

        # programme with multiple learning supports and a sample content programme
        self.diwad_exp = Program.objects.create(
            name="Test Diploma in Web App Development",
            program_code="diwadexp"
        )
        self.diwad_exp.support_programs.set([
            self.diwad_learning_supports,
            self.diwad_second_learning_supports,
            self.diwad_different_learning_supports,
            self.diwad_open_learning_supports
        ])
        self.diwad_exp.sample_content.set([self.diwad_sample_content])

        # programme with single (open) learning support and a sample content programme
        self.diwad_exp_2 = Program.objects.create(
            name="Test Diploma in Web App Development 2",
            program_code="diwadexp2",
        )
        self.diwad_exp_2.support_programs.set([self.diwad_open_learning_supports])
        self.diwad_exp_2.sample_content.set([self.diwad_sample_content])

        # programme with single (open) learning support and TWO sample content programmes
        self.multiple_ls_exp = Program.objects.create(
            name="Test Diploma in Web App Development 2",
            program_code="multiplexp",
        )
        self.diwad_exp_2.support_programs.set([self.diwad_open_learning_supports])
        self.diwad_exp_2.sample_content.set([self.diwad_sample_content, self.sample_content])

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
                        "Programme_ID": "disdcc"
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # check that enrolled programme list is empty initially
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
                        "Programme_ID": "disd"
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # check that enrolled programme list is empty initially
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
                        "Programme_ID": "dddd"
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # check that enrolled programme list is empty initially
        self.assertEqual(list(self.user.program_set.all()), [])

        # verify that running Enrollment will raise an error message
        with self.assertLogs('student_enrollment.enrollment', level="INFO") as cm:
            Enrollment(dryrun=False).enroll()

        self.assertTrue(
            any("Could not find program: dddd" in msg for msg in cm.output)
        )

        # verify that no program has been enrolled
        self.assertEqual(list(self.user.program_set.all()), [])

    # specialisation enrolment tests

    @responses.activate
    def test_specialisation_enrollment(self):

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

        # check that enrolled programme list is empty initially
        self.assertEqual(list(self.user.program_set.all()), [])

        # enroll student into CC and SPSC first
        Enrollment(dryrun=False).enroll()

        # then, enroll into selected specialisation
        SpecialisationEnrollment(dryrun=False).enroll()

        # verify that CC program is unenrolled
        self.assertFalse(self.common_curriculum in list(self.user.program_set.all()))
        # verify that SPSC is still enrolled
        self.assertTrue(self.sample_content in list(self.user.program_set.all()))
        # verify that the specialisation is enrolled
        self.assertTrue(self.specialisation in list(self.user.program_set.all()))

    @responses.activate
    def test_specialisation_enrollment_date_in_the_future(self):
        # check that enrolled programme list is empty initially
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
                        "Specialization_Enrollment_Date": "2100-01-01",
                        "Specialisation_Change_Requested_Within_7_Days": False
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # enroll student into CC and SPSC first
        Enrollment(dryrun=False).enroll()

        # then, try to enroll into selected specialisation
        SpecialisationEnrollment(dryrun=False).enroll()

        # verify that CC is still enrolled, as well as SPSC
        self.assertTrue(self.common_curriculum in list(self.user.program_set.all()))
        self.assertTrue(self.sample_content in list(self.user.program_set.all()))
        # verify that specialisation hasn't been enrolled
        self.assertFalse(self.specialisation in list(self.user.program_set.all()))

    @responses.activate
    def test_specialisation_enrollment_date_in_the_past(self):
        # check that enrolled programme list is empty initially
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
                        "Specialization_Enrollment_Date": "1900-01-01",
                        "Specialisation_Change_Requested_Within_7_Days": False
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # enroll student into CC and SPSC first
        Enrollment(dryrun=False).enroll()

        # then, try to enroll into selected specialisation
        SpecialisationEnrollment(dryrun=False).enroll()

        # verify that CC program is unenrolled
        self.assertFalse(self.common_curriculum in list(self.user.program_set.all()))
        # verify that SPSC is still enrolled
        self.assertTrue(self.sample_content in list(self.user.program_set.all()))
        # verify that the specialisation is enrolled
        self.assertTrue(self.specialisation in list(self.user.program_set.all()))

    @responses.activate
    def test_specialisation_enrollment_non_existent_specialisation(self):
        # check that enrolled programme list is empty initially
        self.assertEqual(list(self.user.program_set.all()), [])

        # set student non-existent Specialisation_programme_id (xxxxxxx)
        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "fred fredriksson",
                        "Email": self.user.email,
                        "Programme_ID": "disdcc",
                        "Specialisation_programme_id": "xxxxxxx",
                        "Specialization_Enrollment_Date": self.today,
                        "Specialisation_Change_Requested_Within_7_Days": False
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
        # check that enrolled programme list is empty initially
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
        # verify that SPSC is still enrolled
        self.assertTrue(self.sample_content in list(self.user.program_set.all()))
        # verify that the new specialisation is enrolled
        self.assertTrue(self.changed_specialisation in list(self.user.program_set.all()))

    @responses.activate
    def test_changed_specialisation_enrollment_crm_programme_id_has_disdcc(self):
        # check that enrolled programme list is empty initially
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
        # verify that SPSC is still enrolled
        self.assertTrue(self.sample_content in list(self.user.program_set.all()))
        # verify that the new specialisation is enrolled
        self.assertTrue(self.changed_specialisation in list(self.user.program_set.all()))

    @responses.activate
    def test_changed_specialisation_enrollment_if_same_specialisation(self):
        # check that enrolled programme list is empty initially
        self.assertEqual(list(self.user.program_set.all()), [])

        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "fred fredriksson",
                        "Email": self.user.email,
                        "Programme_ID": "spadvfe",
                        "Specialisation_programme_id": "spadvfe",
                        "Specialisation_Change_Requested_Within_7_Days": True,
                        "Specialization_Enrollment_Date": self.today
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # enroll student into SPADVFE and SPSC
        self.specialisation.enroll_student_in_program(self.user.email)
        self.sample_content.enroll_student_in_program(self.user.email)

        self.assertTrue(self.sample_content in list(self.user.program_set.all()))
        self.assertTrue(self.specialisation in list(self.user.program_set.all()))

        # verify that running SpecialisationEnrollment raises an error message
        # as we are attempting to re-enroll the same specialisation
        with self.assertLogs('student_enrollment.enrollment', level="INFO") as cm:
            SpecialisationEnrollment(dryrun=False).enroll()

        error_text = "**Student fred@fred.com already enrolled in this specialization: spadvfe**"

        self.assertTrue(any(error_text in msg for msg in cm.output))

        # verify that previous specialisation is still enrolled
        self.assertTrue(self.specialisation in list(self.user.program_set.all()))
        # verify that SPSC is still enrolled
        self.assertTrue(self.sample_content in list(self.user.program_set.all()))

    @responses.activate
    def test_changed_specialisation_enrollment_if_same_specialisation_and_crm_programme_id_has_disdcc(self):
        # check that enrolled programme list is empty initially
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
                        "Specialisation_Change_Requested_Within_7_Days": True,
                        "Specialization_Enrollment_Date": self.today
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # enroll student into SPADVFE and SPSC
        self.specialisation.enroll_student_in_program(self.user.email)
        self.sample_content.enroll_student_in_program(self.user.email)

        self.assertTrue(self.sample_content in list(self.user.program_set.all()))
        self.assertTrue(self.specialisation in list(self.user.program_set.all()))

        # verify that running SpecialisationEnrollment raises an error message
        # as we are attempting to re-enroll the same specialisation
        with self.assertLogs('student_enrollment.enrollment', level="INFO") as cm:
            SpecialisationEnrollment(dryrun=False).enroll()

        error_text = "**Student fred@fred.com already enrolled in this specialization: spadvfe**"

        self.assertTrue(any(error_text in msg for msg in cm.output))

        # verify that previous specialisation is still enrolled
        self.assertTrue(self.specialisation in list(self.user.program_set.all()))
        # verify that SPSC is still enrolled
        self.assertTrue(self.sample_content in list(self.user.program_set.all()))

    # Learning supports enrolment tests (and combined with sample content)

    @responses.activate
    def test_enrollment_and_single_learning_support_eligible(self):

        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "fred fredriksson",
                        "Email": self.user.email,
                        "Programme_ID": "diwad220407",  # has only DIWADLS
                        # intentional whitespace and single quotes for testing!
                        "Student_Source": "'Eligible College 1 '"  # eligible for DIWADLS
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # check that enrolled programme list is empty initially
        self.assertEqual(list(self.user.program_set.all()), [])

        # run enrollment task
        Enrollment(dryrun=False).enroll()

        # verify that both DIWAD220407 and DIWADLS have been enrolled
        self.assertTrue(self.diwad_new in list(self.user.program_set.all()))
        self.assertTrue(self.diwad_learning_supports in list(self.user.program_set.all()))

        # verify that no other learning supports have been enrolled
        self.assertFalse(self.diwad_second_learning_supports in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_different_learning_supports in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_open_learning_supports in list(self.user.program_set.all()))

        # verify that no specialisation, or another program (DISD or DIWAD), has been enrolled
        self.assertFalse(self.diwad_old in list(self.user.program_set.all()))
        self.assertFalse(self.specialisation in list(self.user.program_set.all()))
        self.assertFalse(self.disd in list(self.user.program_set.all()))

    @responses.activate
    def test_enrollment_and_single_learning_support_with_student_source_empty(self):
        # create student with empty CRM Student_Source
        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "fred fredriksson",
                        "Email": self.user.email,
                        "Programme_ID": "diwad220407",  # has DIWADLS learning support, which is source-restricted
                        "Student_Source": None
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # check that enrolled programme list is empty initially
        self.assertEqual(list(self.user.program_set.all()), [])

        # run enrollment task
        Enrollment(dryrun=False).enroll()

        # verify that DIWAD220407 has been enrolled, but DIWADLS has not (because source-restricted and Student Source is empty)
        self.assertTrue(self.diwad_new in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_learning_supports in list(self.user.program_set.all()))

        # verify that no other learning supports have been enrolled
        self.assertFalse(self.diwad_second_learning_supports in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_different_learning_supports in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_open_learning_supports in list(self.user.program_set.all()))

        # verify that no specialisation, or another program (DISD or DIWAD), has been enrolled
        self.assertFalse(self.diwad_old in list(self.user.program_set.all()))
        self.assertFalse(self.specialisation in list(self.user.program_set.all()))
        self.assertFalse(self.disd in list(self.user.program_set.all()))

    @responses.activate
    def test_enrollment_and_single_learning_support_not_eligible(self):

        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "fred fredriksson",
                        "Email": self.user.email,
                        "Programme_ID": "diwad220407",  # has only DIWADLS
                        "Student_Source": "Ineligible College 1"  # not eligible for DIWADLS
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # check that enrolled programme list is empty initially
        self.assertEqual(list(self.user.program_set.all()), [])

        # run enrollment task
        Enrollment(dryrun=False).enroll()

        # verify that DIWAD220407 has been enrolled, but DIWADLS has not, nor has DIWADLSOPEN
        self.assertTrue(self.diwad_new in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_learning_supports in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_open_learning_supports in list(self.user.program_set.all()))

        # verify that no specialisation, nor another program (DISD or DIWAD), has been enrolled
        self.assertFalse(self.specialisation in list(self.user.program_set.all()))
        self.assertFalse(self.disd in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_old in list(self.user.program_set.all()))

    @responses.activate
    def test_enrollment_program_without_supports_although_source_eligible(self):

        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "fred fredriksson",
                        "Email": self.user.email,
                        "Programme_ID": "diwad",  # program does not have learning supports
                        "Student_Source": "Eligible College 1"  # eligible for several LS, but no LS is defined for with this program
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # check that enrolled programme list is empty initially
        self.assertEqual(list(self.user.program_set.all()), [])

        # run enrollment task
        Enrollment(dryrun=False).enroll()

        # verify that "old" DIWAD has been enrolled, but DIWADLS has not, nor has DIWADLSOPEN
        self.assertTrue(self.diwad_old in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_learning_supports in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_open_learning_supports in list(self.user.program_set.all()))

        # verify that no specialisation, nor another program (DISD or DIWAD220407), has been enrolled
        self.assertFalse(self.specialisation in list(self.user.program_set.all()))
        self.assertFalse(self.disd in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_new in list(self.user.program_set.all()))

    @responses.activate
    def test_enrollment_program_with_multiple_supports_some_eligible(self):
        # set user whose student source is eligible for 2 out of 3 available supports
        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "fred fredriksson",
                        "Email": self.user.email,
                        "Programme_ID": "diwad221005",  # has DIWADLS, DIWADLS2, and DIWADLS3
                        "Student_Source": "Eligible College 1"  # eligible for DIWADLS and DIWADLS2, but not DIWADLS3
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # check that enrolled programme list is empty initially
        self.assertEqual(list(self.user.program_set.all()), [])

        # run enrollment task
        Enrollment(dryrun=False).enroll()

        # verify that DIWAD221005 has been enrolled
        self.assertTrue(self.diwad221005 in list(self.user.program_set.all()))

        # verify that DIWADLS and DIWADLS2 have been enrolled, but DIWADLS3 has not (source not eligible)
        self.assertTrue(self.diwad_learning_supports in list(self.user.program_set.all()))
        self.assertTrue(self.diwad_second_learning_supports in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_different_learning_supports in list(self.user.program_set.all()))

        # verify that no specialisation, nor another program (DISD or DIWAD), has been enrolled
        self.assertFalse(self.specialisation in list(self.user.program_set.all()))
        self.assertFalse(self.disd in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_old in list(self.user.program_set.all()))

    @responses.activate
    def test_enrollment_program_with_multiple_supports_some_eligible_one_unrestricted(self):
        # set user whose student source is eligible for 2 out of 3 restricted supports
        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "fred fredriksson",
                        "Email": self.user.email,
                        "Programme_ID": "diwadexp",  # has 4 supports (3 restricted + DIWADLSOPEN)
                        "Student_Source": "Eligible College 1"  # eligible for DIWADLS and DIWADLS2, but not DIWADLS3
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # check that enrolled programme list is empty initially
        self.assertEqual(list(self.user.program_set.all()), [])

        # run enrollment task
        Enrollment(dryrun=False).enroll()

        # verify that DIWADEXP has been enrolled
        self.assertTrue(self.diwad_exp in list(self.user.program_set.all()))

        # verify that DIWADLS, DIWADLS2, and DIWADLSOPEN have been enrolled, but DIWADLS3 has not (source not eligible)
        self.assertTrue(self.diwad_learning_supports in list(self.user.program_set.all()))
        self.assertTrue(self.diwad_second_learning_supports in list(self.user.program_set.all()))
        self.assertTrue(self.diwad_open_learning_supports in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_different_learning_supports in list(self.user.program_set.all()))

        # verify that no specialisation, nor another program (DISD or DIWAD), has been enrolled
        self.assertFalse(self.specialisation in list(self.user.program_set.all()))
        self.assertFalse(self.disd in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_old in list(self.user.program_set.all()))

    @responses.activate
    def test_enrollment_program_with_multiple_supports_and_student_source_empty(self):
        # set user whose CRM Student_Source is empty
        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "fred fredriksson",
                        "Email": self.user.email,
                        "Programme_ID": "diwadexp",  # has 4 supports (3 restricted + DIWADLSOPEN)
                        "Student_Source": None
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # check that enrolled programme list is empty initially
        self.assertEqual(list(self.user.program_set.all()), [])

        # run enrollment task
        Enrollment(dryrun=False).enroll()

        # verify that DIWADEXP has been enrolled
        self.assertTrue(self.diwad_exp in list(self.user.program_set.all()))

        # verify that DIWADLSOPEN has been enrolled, but DIWADLS, DIWADLS2, and DIWADLS3 have not (because student source is empty)
        self.assertTrue(self.diwad_open_learning_supports in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_learning_supports in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_second_learning_supports in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_different_learning_supports in list(self.user.program_set.all()))

        # verify that no specialisation, nor another program (DISD or DIWAD), has been enrolled
        self.assertFalse(self.specialisation in list(self.user.program_set.all()))
        self.assertFalse(self.disd in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_old in list(self.user.program_set.all()))

    @responses.activate
    def test_enrollment_in_program_with_multiple_supports_and_sample_content(self):
        # set user whose student source is eligible for 2 out of 3 available supports
        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "fred fredriksson",
                        "Email": self.user.email,
                        "Programme_ID": "diwadexp",  # has 4 supports (3 restricted + DIWADLSOPEN)
                        # intentional whitespace and double quotes for testing!
                        "Student_Source": " \"Eligible College 3 \""  # eligible for DIWADLS2 and DIWADLS3, but not DIWADLS1
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # check that enrolled programme list is empty initially
        self.assertEqual(list(self.user.program_set.all()), [])

        # run enrollment task
        Enrollment(dryrun=False).enroll()

        # verify that DIWADEXP has been enrolled
        self.assertTrue(self.diwad_exp in list(self.user.program_set.all()))

        # verify that DIWADLS2, DIWADLS3 and DIWADLSOPEN have been enrolled, but DIWADLS1 has not
        self.assertTrue(self.diwad_second_learning_supports in list(self.user.program_set.all()))
        self.assertTrue(self.diwad_different_learning_supports in list(self.user.program_set.all()))
        self.assertTrue(self.diwad_open_learning_supports in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_learning_supports in list(self.user.program_set.all()))

        # verify that DIWADSPSC (sample content) has been enrolled
        self.assertTrue(self.diwad_sample_content in list(self.user.program_set.all()))

        # verify that the sample content for another program (SPSC) has not been enrolled
        self.assertFalse(self.sample_content in list(self.user.program_set.all()))

        # verify that no specialisation, nor another program (DISD or DIWAD), has been enrolled
        self.assertFalse(self.specialisation in list(self.user.program_set.all()))
        self.assertFalse(self.disd in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_old in list(self.user.program_set.all()))

    @responses.activate
    def test_enrollment_in_program_with_single_unrestricted_support_and_sample_content(self):
        # set user whose student source is eligible for 2 out of 3 restricted supports
        responses.add(
            responses.POST, settings.ZOHO_COQL_ENDPOINT,
            json={
                "data": [
                    {
                        "Full_Name": "fred fredriksson",
                        "Email": self.user.email,
                        "Programme_ID": "diwadexp2",  # has DIWADLSOPEN (learning support) and DIWADSPSC (sample content)
                        # intentional whitespace and double quotes for testing!
                        "Student_Source": " \"Eligible College 1 \""
                    },
                ],
                "info": {"more_records": False}
            },
            status=200)

        # check that enrolled programme list is empty initially
        self.assertEqual(list(self.user.program_set.all()), [])

        # run enrollment task
        Enrollment(dryrun=False).enroll()

        # verify that DIWADEXP2 has been enrolled
        self.assertTrue(self.diwad_exp_2 in list(self.user.program_set.all()))

        # verify that only DIWADLSOPEN support has been enrolled
        self.assertTrue(self.diwad_open_learning_supports in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_learning_supports in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_second_learning_supports in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_different_learning_supports in list(self.user.program_set.all()))

        # verify that DIWADSPSC (sample content) has been enrolled
        self.assertTrue(self.diwad_sample_content in list(self.user.program_set.all()))

        # verify that the sample content for another program (SPSC) has not been enrolled
        self.assertFalse(self.sample_content in list(self.user.program_set.all()))

        # verify that no specialisation, nor another program (DISD or DIWAD), has been enrolled
        self.assertFalse(self.specialisation in list(self.user.program_set.all()))
        self.assertFalse(self.disd in list(self.user.program_set.all()))
        self.assertFalse(self.diwad_old in list(self.user.program_set.all()))
