from logging import getLogger

from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.conf import settings
from ci_program.models import Program
from student_enrollment.utils import post_to_zapier
from student_enrollment.zoho import (
    get_students_to_be_enrolled_in_careers_module,
    get_students_to_be_enrolled_in_careers_corner
)

log = getLogger(__name__)

CAREERS_COURSE_ID = 'course-v1:code_institute+cc_101+2018_T1'
CAREERS_CORNER_CODE = 'careerscorner'
"""
Students on the Full Stack Developer course are enrolled in the Careers module
following submission of their Interactive milestone project. Students eligible to
be enrolled will have a status of 'Enroll' for the 'Access to Careers Module' field
on their CRM profile.
"""


class StudentCareerEnrollment:
    ''' Enroll students in the careers module
    '''
    def __init__(self, dryrun=False):
        self.dryrun = dryrun

    def enroll_in_careers(self):
        """
        This will retrieve all of the users from the Zoho CRM API and
        with an 'Access to Careers Module' status of 'Enroll' and
        will enroll the student in the Careers module.
        """
        students = get_students_to_be_enrolled_in_careers_module()
        program = Program.objects.get(program_code='disd')

        for student in students:
            if not student['Email']:
                continue
            if self.dryrun:
                log.info("** dryrun careers enrollment of student: %s",
                         student['Email'])
                continue

            try:
                # check student is a registered user
                user = User.objects.get(email=student['Email'])
            except ObjectDoesNotExist as does_not_exist_exception:
                log.exception(str(does_not_exist_exception))
                post_to_zapier(settings.ZAPIER_ENROLLMENT_EXCEPTION_URL,
                                {
                                    'email': student['Email'],
                                    'crm_field': 'Email',
                                    'unexpected_value': student['Email'],
                                    'attempted_action': 'enroll in careers module',
                                    'message': 'Email on Student\'s CRM profile not found on LMS'
                                })
                continue

            for course in program.get_courses():
                if str(course.id) != CAREERS_COURSE_ID:
                    continue
                # Enroll the student in the careers module
                enroll_in_careers_module = program.enroll_student_in_a_specific_module(
                    user.email, course)
                # Trigger zap to update the CRM
                post_to_zapier(
                    settings.ZAPIER_CAREERS_MODULE_ENROLLMENT_URL, {"email": user.email})


class CareersCornerEnrollment:
    ''' Enroll students in the Careers Corner module (L3)
    '''
    def __init__(self, dryrun=False):
        self.dryrun = dryrun

    def enroll(self):
        """
        This will retrieve all of the users from the Zoho CRM API
        with an Is_Active status of true and
        a Programme ID that is one of the L3 program codes (see zoho.py),
        and will enroll the student in the Careers Corner programme.
        """
        students = get_students_to_be_enrolled_in_careers_corner()

        careers_corner_program = Program.objects.get(program_code=CAREERS_CORNER_CODE)

        for student in students:
            if not student['Email']:
                continue
            if self.dryrun:
                log.info("** dryrun careers enrollment of student: %s",
                         student['Email'])
                continue

            try:
                # check student is a registered user
                user = User.objects.get(email=student['Email'])
            except ObjectDoesNotExist:
                log.exception("** User %s does not exist in the LMS **", student['Email'])
                post_to_zapier(settings.ZAPIER_ENROLLMENT_EXCEPTION_URL,
                                {
                                    'email': student['Email'],
                                    'crm_field': 'Email',
                                    'unexpected_value': student['Email'],
                                    'attempted_action': 'enroll in Careers Corner',
                                    'message': 'Email on Student\'s CRM profile not found on LMS'
                                })
                continue

            # skip enrolment if student already enrolled in Careers Corner,
            # otherwise enrol
            if careers_corner_program not in user.program_set.all():
                careers_corner_program.enroll_student_in_program(user.email)
