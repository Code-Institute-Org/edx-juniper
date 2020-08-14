from django.db import models
from django.conf import settings
from django_extensions.db.models import TimeStampedModel
from django.contrib.auth.models import User
from student.models import CourseEnrollmentAllowed
from lms.djangoapps.instructor.enrollment import enroll_email, unenroll_email
from student_enrollment.utils import create_email_connection
from student_enrollment.utils import construct_email
from student_enrollment.enrollment_types import ENROLLMENT_TEMPLATE_PARTS
from ci_program.models import Program
from ci_program.api import get_courses_from_program, get_program_by_program_code


class ProgramAccessStatus(models.Model):
    """
    Store a student's access to a program. This will allow us to
    determine (mostly at the time of login), whether or not a student
    can access the LMS.
    `user` references the user in question
    `program_access` is a boolean that indicates whether or the user
        can gain access to the LMS
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    program_access = models.BooleanField()

    class Meta:
        app_label = 'student_enrollment'

    def __str_(self):
        return "Program is accessible for {}: {}".format(
            self.user, self.program_access)
    
    def set_access_level(self, user, allowed_access):
        access = self(user=user, program_access=allowed_access)
        access.save()


ENROLLMENT_TYPES = (
    (0, "ENROLLMENT_TYPE__ENROLLMENT"),
    (1, "ENROLLMENT_TYPE__UNENROLLMENT"),
    (2, "ENROLLMENT_TYPE__REENROLLMENT"),
    (3, "ENROLLMENT_TYPE__UPGRADE")
)


class StudentEnrollment(TimeStampedModel):

    class Meta:
        app_label = 'student_enrollment'

    student = models.ForeignKey(User, on_delete=models.CASCADE)
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    is_active = models.BooleanField()

    def email_template_location_and_subject(self, enrollment_type):
        """
        Each program has it's own ecosystem and branding. As such, each
        program will have it's very own branded email. In addition to this,
        different emails can be sent for different types of enrollment.

        A program's enrollment emails should be located in their own directory
        in the theme's code base. Using the `program_code_friendly_name` we can
        target the necessary directory and the enrollment_type specfic email
        and the relevant subject
        """

        # Use the enrollment type to determine which email should be sent -
        # i.e. enrollment, unenrollment & reenrollment, along with the
        # accompany subject
        template_parts = ENROLLMENT_TEMPLATE_PARTS.get(enrollment_type)
        if not template_parts:
            raise Exception("Invalid enrollment_type provided: " + enrollment_type)

        # Get the name of the directory where the program's emails are
        # stored
        template_dir_name = self.program_code_friendly_name

        # Now use the above information to generate the path the email
        # template
        template_location = 'emails/{0}/{1}'.format(
            template_dir_name, template_parts["template_file"])

        subject = template_parts["subject_template"].format(self.name)
        return template_location, subject
    
    def send_email(self, enrollment_type, password):
        """
        Send the enrollment email to the student.

        `student` is an instance of the user object
        `program_name` is the name of the program that the student is
            being enrolled in
        `password` is the password that has been generated. Sometimes
            this will be externally, or the student may already be
            aware of their password, in which case the value will be
            None

        Returns True if the email was successfully sent, otherwise
            return False
        """

        # Set the values that will be used for sending the email
        to_address = self.student.email
        from_address = settings.DEFAULT_FROM_EMAIL
        student_password = password

        template_location, subject = self.email_template_location_and_subject(
            enrollment_type)

        # Construct the email using the information provided
        email_content = construct_email(to_address, from_address,
                                       template_location,
                                       student_password=password,
                                       program_name=self.name)

        # Create a new email connection
        email_connection = create_email_connection()

        # Send the email. `send_mail` will return the amount of emails
        # that were sent successfully. We'll use this number to determine
        # whether of not the email status is to be set as `True` or `False`
        email_sent = send_mail(subject, email_content,
                               from_address, [to_address],
                               fail_silently=False,
                               html_message=email_content,
                               connection=email_connection)

        if not email_sent:
            log.warn("Failed to send email to %s" % to_address)
            return False

        log.info("Email successfully sent to %s" % to_address)
        return True
    
    def enroll(self):
        """
        Enroll a student in a program.

        This works by getting all of the courses in a program and enrolling
        the student in each course in the program. Then add the student to
        the `enrolled_students` table.

        `student` is the user instance that we which to enroll in the program

        Returns True if the student was successfully enrolled in all of the courses,
            otherwise return False
        """
        program = get_program_by_program_code(program_code)
        for course in get_courses_from_program(program.program_code):
            enroll_email(course.id, self.student.email, auto_enroll=True)
            cea, _ = CourseEnrollmentAllowed.objects.get_or_create(
                course_id=course.id, email=self.student.email)
            cea.auto_enroll = True
            cea.save()

    def unenroll(self):
        """
        Unenroll a student from a program.

        This works by getting all of the courses in a program and unenrolling
        the student from each course in the program. Then remove the student to
        the `enrolled_students` table.

        `student` is the user instance that we which to enroll in the program

        Returns True if the student was successfully unenrolled from all of the courses,
            otherwise, return False
        """
        self.is_active = False
        self.save()


class EnrollmentStatusHistory(models.Model):
    """
    Store a historical record of everytime the system attempted
    to register and enroll a student in a course.

    `student` is a reference to the student
    `program` is a reference to the program
    `registered` is a boolean value used to indicate whether or not the
        registration was successful
    `enrollment_type` is a choice field used to determine if the student
        was enrolled, unenrolled or re-enrolled
    `enrolled` is a boolean value used to indicate whether or not the
        enrollment was successful
    `email_sent` is a boolean value used to indicate whether or not the
        email was successfully sent to the student
    `enrollment_attempt` is the time at which the attempt occurred
    """
    
    class Meta:
        app_label = 'student_enrollment'

    student = models.ForeignKey(User, on_delete=models.CASCADE)
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    registered = models.BooleanField(null=False, blank=False)
    enrollment_type = models.IntegerField(choices=ENROLLMENT_TYPES)
    enrolled = models.BooleanField(null=False, blank=False)
    email_sent = models.BooleanField(null=False, blank=False)
    enrollment_attempt = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.registered and self.enrolled and self.email_sent:
            return "{} process for {} was successfully completed at {}".format(
                self.get_enrollment_type_display(), self.student,
                self.enrollment_attempt)
        else:
            return "{} process for {} was unsuccessful".format(
                self.enrollment_type, self.student) 
