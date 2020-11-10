from logging import getLogger

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.conf import settings
from ci_program.models import Program
from student_enrollment.utils import get_or_register_student
from student_enrollment.zoho import (
    get_students_to_be_unenrolled,
    update_student_record)

log = getLogger(__name__)

class Command(BaseCommand):
    help = 'Unenroll students from their relevant programs'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        """
        The main handler for the program enrollment management command.
        This will retrieve all of the users from the Zoho CRM API and
        will unenroll all of the students that have a status of
        `Unenroll`.
        """

        # The only possible enrollment type here is unenrollment so
        # we'll set the type as a constact
        ENROLLMENT_TYPE = 1

        zoho_students = get_students_to_be_unenrolled()

        for student in zoho_students:
            # Get the user
            try:
                user = User.objects.get(email=student['Email'])
            except ObjectDoesNotExist as does_not_exist_exception:
                log.exception(str(does_not_exist_exception))
                post_to_zapier(settings.ZAPIER_ENROLLMENT_EXCEPTION_URL,
                                {
                                    'email': student['Email'],
                                    'crm_field': 'Email',
                                    'unexpected_value': student['Email'],
                                    'attempted_action': 'unenroll',
                                    'message': 'Email on Student\'s CRM profile not found on LMS'
                                })
                continue
                        
            # Get the code for the course the student is enrolling in
            program_to_unenroll_from = student['Programme_ID']

            # Check to make sure that the student is enrolled in that program.
            # If they are not enrolled in that program then we can skip this
            # email and move onto the next user
            try:
                user.program_set.get(program_code=program_to_unenroll_from)
            except ObjectDoesNotExist as does_not_exist_exception:
                log.exception(str(does_not_exist_exception))
                # Student is already unenrolled, so update the CRM accordingly
                update_student_record(settings.ZAPIER_UNENROLLMENT_URL, user.email)
                continue

            try:
                # Get the Program that contains the Zoho program code
                program = Program.objects.get(
                    program_code=program_to_unenroll_from)
            except ObjectDoesNotExist as does_not_exist_exception:
                log.exception(str(does_not_exist_exception))
                post_to_zapier(settings.ZAPIER_ENROLLMENT_EXCEPTION_URL,
                                {
                                    'email': student['Email'],
                                    'crm_field': 'Programme_ID',
                                    'unexpected_value': student['Programme_ID'],
                                    'attempted_action': 'unenroll',
                                    'message': 'Programme ID does not exist on LMS'
                                })
                continue

            # Unenroll the student from the program
            program.unenroll_student_from_program(user)

            update_student_record(settings.ZAPIER_UNENROLLMENT_URL, user.email)
