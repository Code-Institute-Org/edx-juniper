from logging import getLogger
from datetime import date
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.conf import settings
from ci_program.models import Program
from student_enrollment.utils import (
    get_or_register_student,
    post_to_zapier
)
from student_enrollment.zoho import (
    get_students_to_be_enrolled,
    get_students_to_be_enrolled_into_specialisation
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
today = date.today().isoformat()


class Enrollment:
    ''' Enroll students in their relevant programs
    '''
    def __init__(self, dryrun=False):
        self.dryrun = dryrun

    def enroll(self):
        """
        The main handler for the program enrollment management command.
        This will retrieve all of the users from the Zoho CRM API and
        will enroll all of the students that have a status of
        `Enroll`.

        If a student doesn't exist in the system, then we will first register them
        and then enroll them in the relevant programme (specified by Programme_ID)
        """
        zoho_students = get_students_to_be_enrolled()

        for student in zoho_students:
            if not student['Email']:
                continue
            if self.dryrun:
                log.info("** dryrun attempting enrollment of student: %s",
                         student['Email'])
                continue

            # Get the user, the user's password, and their enrollment type
            user, password, enrollment_type = get_or_register_student(
                student['Email'], student['Email'])

            # Get the code for the course the student is enrolling in
            program_to_enroll_in = student['Programme_ID']
            spec_sample_content = None

            if program_to_enroll_in == "disdcc":
                spec_sample_content = Program.objects.get(program_code="spsc")

            try:
                # Get the Program that contains the Zoho program code
                program = Program.objects.get(
                    program_code=program_to_enroll_in)
            except ObjectDoesNotExist as does_not_exist_exception:
                log.exception("**Could not find program: %s**", program_to_enroll_in)
                post_to_zapier(
                    settings.ZAPIER_ENROLLMENT_EXCEPTION_URL,
                    {
                        'email': student['Email'],
                        'crm_field': 'Programme_ID',
                        'unexpected_value': student['Programme_ID'],
                        'attempted_action': 'enroll',
                        'message': 'Programme ID does not exist on LMS'
                    }
                )
                continue

            # Enroll the student in the program
            program_enrollment_status = program.enroll_student_in_program(
                user.email,
                exclude_courses=EXCLUDED_FROM_ONBOARDING
            )

            # If DISDCC enrollment successful, enroll the student into
            # specialisation sample content module
            if spec_sample_content and program_enrollment_status:
                spec_sample_content.enroll_student_in_program(user.email)

            # Send the email
            email_sent_status = program.send_email(
                user, enrollment_type, password
            )

            # Set the students access level (i.e. determine whether or
            # not a student is allowed to access to the LMS.
            # Deprecated...
            access, created = ProgramAccessStatus.objects.get_or_create(
                user=user, program_access=True
            )

            if not created:
                access.allowed_access = True
                access.save()

            # Used to update the status from 'Enroll' to 'Online'
            # in the CRM
            post_to_zapier(
                settings.ZAPIER_ENROLLMENT_URL,
                {'email': user.email}
            )

            enrollment_status = EnrollmentStatusHistory(
                student=user,
                program=program,
                registered=bool(user),
                enrollment_type=enrollment_type,
                enrolled=bool(program_enrollment_status),
                email_sent=email_sent_status
            )
            enrollment_status.save()


class SpecialisationEnrollment:
    '''
    Enroll students in their relevant specialisation; simultaneously
    unenroll them from the Common Curriculum programme
    '''
    def __init__(self, dryrun=False):
        self.dryrun = dryrun

    def enroll(self):
        """
        The main handler for the specialisation enrollment management command.
        This will retrieve all of the users from the Zoho CRM API and
        will enroll all of the students that have a specialisation enrollment
        status of `Approved`.
        """

        today = date.today().isoformat()
        zoho_students = get_students_to_be_enrolled_into_specialisation()

        if not zoho_students:
            log.info("** Specialisation enrollment run: no eligible students found. **")

        for student in zoho_students:
            if not student['Email']:
                continue
            if self.dryrun:
                log.info(
                    "** dryrun attempting enrollment of student: %s",
                    student['Email']
                )
                continue

            # only process students whose specialisation enrollment date
            # is populated and is today or in the past
            enrollment_date = student["Specialization_Enrollment_Date"]

            if enrollment_date is None:
                log.info(
                    "** Student %s has no specialisation enrollment date, skipping. **",
                    student["Email"]
                )
                continue
            if enrollment_date > today:
                log.info(
                    "** Student %s specialisation enrollment date is in the future, skipping. **",
                    student["Email"]
                )
                continue

            # check if the enrollment is a change of the originally
            # enrolled specialisation
            specialization_change = student["Specialisation_Change_Requested_Within_7_Days"]

            # Get the user, the user's password, and their enrollment type
            user, password, enrollment_type = get_or_register_student(
                student['Email'], student['Email'])

            # Get the code of the specialisation to be enrolled in, as well
            # as the current programme to be subsequently unenrolled from
            current_program = student["Programme_ID"]
            specialization_to_enroll = student['Specialisation_programme_id']

            # if new specialisation code matches the current specialisation,
            # trigger exception email and stop further process
            if current_program == specialization_to_enroll:
                log.exception(
                    "**Student %s already enrolled in this specialization: %s**",
                    student['Email'], specialization_to_enroll
                )
                post_to_zapier(
                    settings.ZAPIER_ENROLLMENT_EXCEPTION_URL,
                    {
                        'email': student['Email'],
                        'crm_field': 'Specialisation_programme_id',
                        'unexpected_value': student['Specialisation_programme_id'],
                        'attempted_action': 'enroll specialisation',
                        'message': ('Specialisation change field checked, but student'
                                    + 'is already enrolled into the same specialisation')
                    }
                )
                # return in order to prevent reenrollment
                return

            # otherwise continue with enrollment
            try:
                # Get the Program that contains the Zoho specialisation program code
                specialization = Program.objects.get(program_code=specialization_to_enroll)
            except ObjectDoesNotExist as does_not_exist_exception:
                log.exception("**Could not find specialisation: %s**", specialization_to_enroll)
                post_to_zapier(
                    settings.ZAPIER_ENROLLMENT_EXCEPTION_URL,
                    {
                        'email': student['Email'],
                        'crm_field': 'Specialisation_programme_id',
                        'unexpected_value': student['Specialisation_programme_id'],
                        'attempted_action': 'enroll specialisation',
                        'message': 'Specialisation programme ID does not exist on LMS'
                    }
                )
                continue

            # NOTE: this is a defensive feature in case:
            # a) Programme_ID still contains CC program code, or
            # b) the specialistion change checkbox was checked but
            #    the new specialisation code hasn't been updated
            #
            # If specialisation change, get the previous enrolled specialisation
            if specialization_change:
                for program in user.program_set.all():
                    if program.specialization_for:
                        # if already enrolled into same specialisation,
                        # trigger exception email and stop further process
                        if program == specialization:
                            log.exception(
                                "**Student %s already enrolled in this specialization: %s**",
                                student['Email'], specialization_to_enroll
                            )
                            post_to_zapier(
                                settings.ZAPIER_ENROLLMENT_EXCEPTION_URL,
                                {
                                    'email': student['Email'],
                                    'crm_field': 'Specialisation_programme_id',
                                    'unexpected_value': student['Specialisation_programme_id'],
                                    'attempted_action': 'enroll specialisation',
                                    'message': ('Specialisation change field checked, but student'
                                                + ' is already enrolled into the same specialisation')
                                }
                            )
                            # return in order to prevent reenrollment
                            return
                        # otherwise, set current specialisation as current program (to unenroll)
                        else:
                            current_program = program.program_code

            # Enroll the student in the (new) specialisation
            specialization_enrollment_status = specialization.enroll_student_in_program(
                user.email,
                exclude_courses=EXCLUDED_FROM_ONBOARDING
            )

            # if specialisation enrollment successful, unenroll the
            # student from the previous programme
            if specialization_enrollment_status:
                program_to_unenroll = Program.objects.get(
                    program_code=current_program
                )
                try:
                    program_to_unenroll.enrolled_students.remove(user)
                    log.info(
                        "student %s successfully removed from previous programme: %s",
                        student['Email'], program_to_unenroll.name
                    )
                except Exception as e:
                    log.info(
                        "** Unable to remove student %s from previous programme %s : %s**",
                        student['Email'], program_to_unenroll, e
                    )

                # send the enrollment email
                email_sent_status = specialization.send_email(
                    user, enrollment_type, password
                )

            # send Zap to update Specialisation Enrollment Status in CRM
            post_to_zapier(
                settings.ZAPIER_SPECIALISATION_ENROLLMENT_URL,
                {'email': user.email}
            )

            enrollment_status = EnrollmentStatusHistory(
                student=user,
                program=specialization,
                registered=bool(user),
                enrollment_type=enrollment_type,
                enrolled=bool(specialization_enrollment_status),
                email_sent=email_sent_status
            )
            enrollment_status.save()
