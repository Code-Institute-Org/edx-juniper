from logging import getLogger

from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.conf import settings
from ci_program.models import Program
from student_enrollment.utils import (
    get_or_register_student, post_to_zapier
)
from student_enrollment.zoho import (
    get_students_to_be_enrolled
)
from student_enrollment.models import EnrollmentStatusHistory
from student_enrollment.models import ProgramAccessStatus

log = getLogger(__name__)


"""
Students starting the Full Stack Developer course should initially not be
enrolled into the Careers module. It should be made available after the submission
of the Interactive Frontend Development. See "Enroll student in careers module"
Zap.

This collection is used to store any courses that should be excluded from the
initial student onboarding/enrollment process like the Careers module.
"""
EXCLUDED_FROM_ONBOARDING = ['course-v1:code_institute+cc_101+2018_T1']


class Command(BaseCommand):
    help = 'Enroll students in their relevant programs'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        """
        The main handler for the program enrollment management command.
        This will retrieve all of the users from the Zoho CRM API and
        will enroll all of the students that have a status of
        `Enroll`.

        If a student doesn't exist in the system, then we will first register them
        and then enroll them in the relevant programme (specified by programme_id)
        """
        zoho_students = get_students_to_be_enrolled()

        for student in zoho_students:
            if not student['Email']:
                continue

            # Get the user, the user's password, and their enrollment type
            user, password, enrollment_type = get_or_register_student(
                student['Email'], student['Email'])

            # Get the code for the course the student is enrolling in
            # This will always be disd, based on current coql query
            program_to_enroll_in = student['Programme_Id']

            try:
                # Get the Program that contains the Zoho program code
                program = Program.objects.get(
                    program_code=program_to_enroll_in)
            except ObjectDoesNotExist as does_not_exist_exception:
                log.exception(str(does_not_exist_exception))
                post_to_zapier(settings.ZAPIER_ENROLLMENT_EXCEPTION_URL,
                                {
                                    'email': student['Email'],
                                    'crm_field': 'Programme_Id',
                                    'unexpected_value': student['Programme_Id'],
                                    'attempted_action': 'enroll',
                                    'message': 'Programme ID does not exist on LMS'
                                })
                continue

            # Enroll the student in the program
            program_enrollment_status = program.enroll_student_in_program(
                user.email,
                exclude_courses=EXCLUDED_FROM_ONBOARDING)

            # Send the email
            email_sent_status = program.send_email(
                user, enrollment_type, password)

            # Set the students access level (i.e. determine whether or
            # not a student is allowed to access to the LMS.
            # Deprecated...
            access, created = ProgramAccessStatus.objects.get_or_create(
                user=user, program_access=True)

            if not created:
                access.allowed_access = True
                access.save()

            # Used to update the status from 'Enroll' to 'Online'
            # in the CRM
            post_to_zapier(settings.ZAPIER_ENROLLMENT_URL,
                            {'email': user.email})

            enrollment_status = EnrollmentStatusHistory(
                student=user,
                program=program,
                registered=bool(user),
                enrollment_type=enrollment_type,
                enrolled=bool(program_enrollment_status),
                email_sent=email_sent_status)
            enrollment_status.save()
