from logging import getLogger

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.conf import settings
from ci_program.models import Program
from student_enrollment.utils import post_to_zapier
from student_enrollment.zoho import (
    get_students_to_be_unenrolled,
    update_student_record
)

log = getLogger(__name__)


class Unenrollment:
    ''' Unenroll students from their relevant programs
    '''
    def __init__(self, dryrun=False):
        self.dryrun = dryrun

    def unenroll(self):
        """
        The main handler for the program enrollment management command.
        This will retrieve all of the users from the Zoho CRM API and
        will unenroll all of the students that have a status of
        `Unenroll`.

        Steps are as follows:
        1. Get all students to be unenrolled from the CRM
        2. For each student, check the following:
            - a registered user account
            - the programme id in their CRM profile maps to a valid program on the LMS
            - they are enrolled in said program
        3. If student passes all the above checks:
            - Deactivate course enrollments (by setting is active to False) for all
            courses in the given program
            - Update the CRM profile by setting the LMS Access field to removed
        4. If the student does not pass all the checks in point 2, trigger a zap which
        emails the SC team with a description of the issue encountered
        """
        self.students = get_students_to_be_unenrolled()

        for student in self.students:
            if self.dryrun:
                log.info("** dryrun attempting unenrollment of student: %s",
                         student.get('Email'))
                continue

            # Retrieve the user by searching for the given email
            try:
                user = User.objects.get(email=student['Email'])
            except ObjectDoesNotExist as does_not_exist_exception:
                log.exception(str(does_not_exist_exception))
                post_to_zapier(
                    settings.ZAPIER_ENROLLMENT_EXCEPTION_URL,
                    {
                        'email': student['Email'],
                        'crm_field': 'Email',
                        'unexpected_value': student['Email'],
                        'attempted_action': 'unenroll',
                        'message': 'Email on Student\'s CRM profile not found on LMS'
                    }
                )
                continue

            # Retrieve the program by searching for the given programme_id
            program_to_unenroll_from = student['Programme_ID']

            try:
                program = Program.objects.get(program_code=program_to_unenroll_from)
            except ObjectDoesNotExist as does_not_exist_exception:
                log.exception(str(does_not_exist_exception))
                post_to_zapier(
                    settings.ZAPIER_ENROLLMENT_EXCEPTION_URL,
                    {
                        'email': student['Email'],
                        'crm_field': 'Programme_ID',
                        'unexpected_value': student['Programme_ID'],
                        'attempted_action': 'unenroll',
                        'message': 'Programme ID does not exist on LMS'
                    }
                )
                continue

            # Check if student is enrolled in the program
            # If not, the student has likely been unenrolled manually
            try:
                user.program_set.get(program_code=program_to_unenroll_from)
            except ObjectDoesNotExist as does_not_exist_exception:
                log.exception(str(does_not_exist_exception))
                # Student is already unenrolled, so update the CRM accordingly
                update_student_record(settings.ZAPIER_UNENROLLMENT_URL, user.email)
                continue

            # To unenroll student, deactivate student's course enrollments
            # for all modules on the given program
            enrollments = user.courseenrollment_set.filter(
                course_id__in=program.get_courses(),
                is_active=True
            )
            enrollments.update(is_active=False)

            # update the student record on the CRM
            update_student_record(settings.ZAPIER_UNENROLLMENT_URL, user.email)
