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

            # Get the sample content programme, if any
            sample_content = None
            if program.sample_content:
                try:
                    sample_content = Program.objects.get(program_code__iexact=program.sample_content)
                except ObjectDoesNotExist:
                    log.exception("**Could not find sample content program: %s**", program.sample_content)

            # Get the learning supports programme(s), if any
            learning_supports = []
            if program.support_programs:
                support_program_codes_list = list(map(lambda x: x.strip(" \'\"\r\n"),
                                                  program.support_programs.split(",")))

                for prog_code in support_program_codes_list:
                    try:
                        support = Program.objects.get(program_code__iexact=prog_code)
                        learning_supports.append(support)
                    except ObjectDoesNotExist:
                        log.exception("**Could not find support program: %s**", prog_code)
                        continue

            # Enroll the student in the program
            program_enrollment_status = program.enroll_student_in_program(
                user.email,
                exclude_courses=EXCLUDED_FROM_ONBOARDING
            )

            # If main programme enrollment successful, enroll the
            # student into auxiliary programme(s) if any
            if program_enrollment_status:
                if sample_content is not None:
                    sample_content.enroll_student_in_program(user.email)
                if learning_supports:
                    student_source = student["Student_Source"].strip(" \"\'") if student.get("Student_Source") else None
                    for prog in learning_supports:
                        # if eligible sources list is empty, treat all students as eligible and enrol
                        if not prog.support_program_sources:
                            prog.enroll_student_in_program(user.email)
                        # otherwise check student source against eligible sources before enrolling
                        else:
                            eligible_sources = list(map(lambda x: x.strip(" \'\"\r\n"),
                                                    prog.support_program_sources.split(",")))
                            if student_source in eligible_sources:
                                prog.enroll_student_in_program(user.email)

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
                        'message': ('Student is already enrolled into this specialisation')
                    }
                )
                # continue in order to prevent reenrollment
                continue

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
                error_flag = False
                for program in user.program_set.all():
                    if program.specialization_for:
                        # if already enrolled into same specialisation,
                        # trigger exception email and stop further process
                        if program == specialization:
                            error_flag = True
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
                            break
                        # otherwise, set current specialisation as current program (to unenroll)
                        else:
                            current_program = program.program_code
                # continue to prevent reenrollment
                if error_flag:
                    continue

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
