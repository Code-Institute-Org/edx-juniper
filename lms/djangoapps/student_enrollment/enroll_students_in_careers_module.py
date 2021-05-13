from logging import getLogger

from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.conf import settings
from ci_program.models import Program
from student_enrollment.utils import post_to_zapier
from student_enrollment.zoho import (
    get_students_to_be_enrolled_in_careers_module
)

log = getLogger(__name__)

CAREERS_COURSE_ID = 'course-v1:code_institute+cc_101+2018_T1'
"""
Students on the Full Stack Developer course are enrolled in the Careers module
following submission of their Interactive milestone project. Students eligible to
be enrolled will have a status of 'Enroll' for the 'Access to Careers Module' field
on their CRM profile.
"""


class StudentCareerEnrollment:
    ''' Enroll students in the careers module
    '''

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

            try:
                # check student is a registered user
                user = User.objects.get(email=student['Email'])
            except ObjectDoesNotExist as does_not_exist_exception:
                log.exception(str(does_not_exist_exception))
                post_to_zapier(settings.ZAPIER_ENROLLMENT_EXCEPTION_URL,
                                {
                                    'email': student['Email'],
                                    'crm_field': 'Email',
                                    'unexpected_value': 'student['Email']',
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
