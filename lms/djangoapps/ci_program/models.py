import json
import os
from logging import getLogger
from uuid import uuid4
from django.db import models
from django_extensions.db.models import TimeStampedModel
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from opaque_keys.edx.locator import CourseLocator

from ci_program.xblock_tree_builder import XBlockTreeBuilder
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from student.models import CourseEnrollmentAllowed
from lms.djangoapps.instructor.enrollment import enroll_email, unenroll_email
from lms.djangoapps.student_enrollment.utils import create_email_connection
from lms.djangoapps.student_enrollment.utils import construct_email

log = getLogger(__name__)


class Program(TimeStampedModel):
    """
    Representation of a Program.
    """

    STATUS_CHOICES = [
        ('live', 'Live'),
        ('in_development', 'In Development'),
        ('end_of_sale', 'End of Sale'),
        ('end_of_life', 'End of Life'),
    ]

    class Meta:
        app_label = 'ci_program'

    uuid = models.UUIDField(
        blank=True,
        default=uuid4,
        editable=False,
        unique=True,
    )

    name = models.CharField(
        help_text=_('The user-facing display name for this Program.'),
        max_length=255,
        unique=True,
    )

    subtitle = models.CharField(
        help_text=_('A brief, descriptive subtitle for the Program.'),
        max_length=255,
        blank=True,
    )

    marketing_slug = models.CharField(
        help_text=_('Slug used to generate links to the marketing site'),
        blank=True,
        max_length=255
    )

    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default='in_development'
    )

    length_of_program = models.CharField(max_length=25, null=True, blank=True)
    effort = models.CharField(max_length=25, null=True, blank=True)
    full_description = models.TextField(null=True, blank=True)
    image = models.URLField(null=True, blank=True)
    video = models.URLField(null=True, blank=True)
    program_code = models.CharField(max_length=50, null=True, blank=True)
    
    specialization_for = models.CharField(max_length=50, null=True, blank=True)

    # enable multiple sample-content programmes for an individual main programme
    sample_content = models.ManyToManyField("self", blank=True, symmetrical=False, related_name="sampled_main_programs")
    # NOTE: to be removed following refactor
    sample_content_for = models.CharField(max_length=50, null=True, blank=True)

    # enable multiple support programmes for an individual main programme
    support_programs = models.ManyToManyField("self", blank=True, symmetrical=False, related_name="supported_main_programs")
    # NOTE: to be removed following refactor
    support_program_for = models.CharField(max_length=50, null=True, blank=True)
    
    support_program_sources = models.TextField(
        help_text=_('Comma-separated list of student sources (colleges) eligible for the support Program'),
        null=True,
        blank=True
    )

    enrolled_students = models.ManyToManyField(
        User, blank=True)
    # This is used for getting the path to the enrollment email files
    program_code_friendly_name = models.CharField(max_length=50, null=True,
                                                  blank=True)

    @staticmethod
    def lookup_programs_by_course(course):
        course_id = course.id.html_id()
        course_key = course_id.split(':')[1]
        course_codes = ProgramCourseCode.objects.filter(
            course_code__key=course_key)
        return [code.program for code in course_codes]

    @property
    def number_of_modules(self):
        """
        Get the length of a program - i.e. the number of modules
        """
        return len(self.get_courses())

    @property
    def email_template_location(self):
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
        if self.enrollment_type == 0:
            subject = "You have been enrolled in your Code Institute {}"\
                      " program".format(self.name)
            template_type_name = "enrollment_email.html"
        elif self.enrollment_type == 1:
            subject = "Code Institute Unenrollment"
            template_type_name = "unenrollment_email.html"
        elif self.enrollment_type == 2:
            subject = "You have been re-enrolled!"
            template_type_name = "reenrollment_email.html"
        elif self.enrollment_type == 3:
            subject = "You have been enrolled in your Code Institute {} "\
                      "program".format(self.name)
            template_type_name = "upgrade_enrollment_email.html"

        # Get the name of the directory where the program's emails are
        # stored
        template_dir_name = self.program_code_friendly_name

        # Now use the above information to generate the path the email
        # template
        template_location = 'emails/{0}/{1}'.format(
            template_dir_name, template_type_name)
        if os.path.exists(os.path.join("lms/templates", template_location)):
            return template_location, subject
        else:
            log.exception("No email template found for %s/%s, using default",
                          template_dir_name, template_type_name)
            return 'emails/default/{0}'.format(template_type_name), "LMS"

    def __str__(self):
        return "<%s: %s>" % (self.name, self.program_code)

    def get_program_descriptor(self, request):
        """
        The program descriptor will return all of necessary courseware
        info for a given program. The information contained in the descriptor
        should include -

          - Name
          - Subtitle
          - Full description
          - Image
          - Video
          - Length
          - Effort
          - Number of modules
          - Modules
            - Name
            - Short Description
            - Key
            - Image
        """

        # Gather the basic information about the program
        activity_log = request.user.studentmodule_set.filter(
            course_id__in=self.get_course_locators())
        activity_log = activity_log.order_by('-modified')

        module_tree = self._read_module_tree_from_mongo(request.user)

        latest_course_key = self._get_latest_course_key(activity_log)
        latest_block_id = self._get_or_infer_block_id(
            activity_log, latest_course_key, module_tree)

        completed_block_ids = [
            ac.module_state_key.block_id for ac in activity_log]
        self._add_progress_info_to_module_tree(
            completed_block_ids, latest_block_id, module_tree)
        completed_percent = self._calculate_percent_completed(
            completed_block_ids, module_tree)

        modules = self._extract_ordered_modules(module_tree, request)

        program_descriptor = {
            "name": self.name,
            "subtitle": self.subtitle,
            "full_description": self.full_description,
            "image": self.image,
            "video": self.video,
            "length": self.length_of_program,
            "effort": self.effort,
            "number_of_modules": len(modules),
            "latest_block_id": latest_block_id,
            "latest_course_key": latest_course_key,
            "completed_percent": completed_percent,
            'modules': modules,
        }

        return program_descriptor

    def _add_progress_info_to_module_tree(
            self, completed_block_ids, latest_block_id, module_tree):
        ''' Adds the 'resume_block' field to each of the sections, True if
            it was the last section viewed
        '''
        for course_id, module in module_tree.items():
            for section in module['sections']:
                section['resume_block'] = False
                section['complete'] = section['block_id'] in completed_block_ids
                for unit in section['units']:
                    # The structure of the block id eludes me. sometimes it
                    # refers to the section, and sometimes
                    # the unit
                    if (unit['block_id'] == latest_block_id or
                            section['block_id'] == latest_block_id):
                        section['resume_block'] = True
                    unit['complete'] = unit['block_id'] in completed_block_ids

    def _calculate_percent_completed(self, completed_block_ids, module_tree):
        unit_block_ids = []
        for module in module_tree.values():
            for section in module['sections']:
                for unit in section['units']:
                    unit_block_ids.append(unit['block_id'])
        total_completed_modules = set(unit_block_ids).intersection(
            completed_block_ids)
        if unit_block_ids:
            completed_percent = int(
                100 * len(total_completed_modules) / len(unit_block_ids))
        else:
            completed_percent = 0
        return completed_percent

    def _extract_ordered_modules(self, module_tree, request):
        ''' Extract the modules from the module tree in the correct order
        '''
        enrolled_courses = request.user.courseenrollment_set.filter(
            is_active=True)
        enrolled_keys = set(enrolled_courses.values_list(
            'course_id', flat=True))
        enrolled_keys = {str(key).split(':')[1] for key in enrolled_keys}
        modules = []
        for course in self.get_courses():
            course_id = course.id.html_id().split(':')[1]
            if course_id in enrolled_keys:
                module_xblock = module_tree[course_id]
                module_xblock['course_id'] = course_id
                module_xblock['course_key'] = course.id
                modules.append(module_xblock)
        return modules

    def _get_latest_course_key(self, activity_log):
        if activity_log:
            return activity_log[0].module_state_key.course_key
        else:
            return None

    def _get_or_infer_block_id(
            self, activity_log, course_key, module_tree):
        ''' Resolves the xblock id if the activity log type is "course", and
            otherwise return the latest xblock id.

            The activity log will sometimes refer to the first section in a
            module as type "course" with the "state" containing json containing
            "position" field. Otherwise it refers to the xblock of either the
            section or the unit directly.
        '''
        if not activity_log:
            return None
        block_id = activity_log[0].module_state_key.block_id
        if block_id == 'course' and course_key:
            latest_course_id = course_key.html_id().split(':')[1]
            course_xblock = module_tree[latest_course_id]
            children = course_xblock.get('fields', {}).get('children')
            if children:
                activity_state = json.loads(activity_log[0].state)
                section_block = children[activity_state.get('position', 1) - 1]
                block_id = section_block[1] if section_block else None
        return block_id

    def _read_module_tree_from_mongo(self, user):
        if self.course_codes.exists():
            aggregate_query = self._create_aggregate_query()
            courses = self._aggregate_courses(aggregate_query)
            return XBlockTreeBuilder(courses, user).create_program_course_tree()
        else:
            return {}

    def _aggregate_courses(self, aggregate_query):
        return list(settings.MONGO_DB['modulestore.active_versions'].aggregate(
            aggregate_query))

    def _create_aggregate_query(self):
        course_locators = [code.code_sections() for code in
                           self.course_codes.all()]

        query = [
            {"$match": {
                "$or": [
                    {"org": org, "course": course, "run": run} for (
                        org, course, run) in course_locators]}
            },
        ]
        query.extend([
            {"$project": {"root_definition_id": "$versions.published-branch",
                          "course_id": {
                              "$concat": [
                                  "$org", "+", "$course", "+", "$run"]}}},
            {"$lookup": {
                "from": "modulestore.structures",
                "localField": "root_definition_id",
                "foreignField": "_id",
                "as": "structures",
            }},
            {"$project": {"blocks": "$structures.blocks",
                          "course_id": 1,
                         }},
            {"$unwind": "$blocks"},
        ])
        query.extend([
            {"$project": {"blocks.block_id": 1,
                          "blocks.block_type": 1,
                          "blocks.fields.display_name": 1,
                          "blocks.fields.children": 1,
                          "blocks.fields.visible_to_staff_only": 1,
                          "course_id": 1,
                          }},
        ])
        return query

    def get_course_locators(self):
        """
        Get the list of locators for each of the modules in a program

        CodeInstitute+HF101+2017_T1
        """
        list_of_locators = []

        for course_code in self.course_codes.all():
            course_identifiers = course_code.key.split('+')
            list_of_locators.append(CourseLocator(
                course_identifiers[0],
                course_identifiers[1],
                course_identifiers[2]
            ))

        return list_of_locators

    def get_courses(self):
        """
        Get the list of courses in the program instance based on their
        course codes.

        `self` is the specific program instance

        Returns the list of children courses
        """

        list_of_courses = []

        for course_code in self.course_codes.all().order_by('programcoursecode'):
            org, code, run = course_code.code_sections()
            list_of_courses.append(
                CourseOverview.objects.get(id=CourseLocator(org, code, run)))

        return list_of_courses

    def send_email(self, student, enrollment_type, password):
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
        student_password = password
        to_address = student.email
        from_address = 'learning@codeinstitute.net'
        if self.program_code == 'SBAACC':
            from_address = 'springboard@codeinstitute.net'

        self.enrollment_type = enrollment_type

        if self.name == "Five Day Coding Challenge":
            module_url = "https://courses.codeinstitute.net/courses/{}/course/".format(
                self.course_codes.first().key)
        else:
            module_url = None


        # Get the email location & subject
        template_location, subject = self.email_template_location

        # Construct the email using the information provided
        email_content = construct_email(to_address, from_address,
                                       template_location,
                                       student_password=password,
                                       program_name=self.name,
                                       module_url=module_url)

        # Create a new email connection
        email_connection = create_email_connection()

        # Send the email. `send_mail` will return the amount of emails
        # that were sent successfully. We'll use this number to determine
        # whether of not the email status is to be set as `True` or `False`
        number_of_mails_sent = send_mail(subject, email_content,
                                            from_address, [to_address],
                                            fail_silently=False,
                                            html_message=email_content,
                                            connection=email_connection)

        email_successfully_sent = None
        log_message = ""

        if number_of_mails_sent == 1:
            email_successfully_sent = True
            log_message = "Email successfully sent to %s" % to_address
        else:
            email_successfully_sent = False
            log_message = "Failed to send email to %s" % to_address

        log.info(log_message)

        return email_successfully_sent

    def enroll_student_in_program(self, student_email, exclude_courses=[]):
        """
        Enroll a student in a program.

        This works by getting all of the courses in a program and enrolling
        the student in each course in the program. Then add the student to
        the `enrolled_students` table.

        `student` is the user instance that we which to enroll in the program

        `exclude_courses` is a collection of course codes (formatted as a string)
        which can be used to exclude specific courses from the auto-enrollment
        process

        Returns True if the student was successfully enrolled in all of the courses,
            otherwise return False
        """
        for course in self.get_courses():
            if str(course.id) in exclude_courses:
                continue

            enroll_email(course.id, student_email, auto_enroll=True)
            cea, _ = CourseEnrollmentAllowed.objects.get_or_create(
                course_id=course.id, email=student_email)
            cea.auto_enroll = True
            cea.save()

        student_to_be_enrolled = User.objects.get(email=student_email)

        self.enrolled_students.add(student_to_be_enrolled)

        student_successfully_enrolled = None
        log_message = ""

        if self.enrolled_students.filter(email=student_email).exists():
            student_successfully_enrolled = True
            log_message = "%s was enrolled in %s" % (
                student_email, self.name)
        else:
            student_successfully_enrolled = False
            log_message = "Failed to enroll %s in %s" % (
                student_email, self.name)

        log.info(log_message)
        return student_successfully_enrolled

    def unenroll_student_from_program(self, student):
        """
        Unenroll a student from a program.

        This works by getting all of the courses in a program and unenrolling
        the student from each course in the program. Then remove the student to
        the `enrolled_students` table.

        `student` is the user instance that we which to enroll in the program

        Returns cea (CourseEnrollmentAllowed) as False if the student was
        successfully unenrolled from all of the courses, otherwise, return True
        """
        for course in self.get_courses():
            unenroll_email(course.id, student.email)

        self.enrolled_students.remove(User.objects.get(email=student.email))
        enrolled_courses = student.courseenrollment_set.all()
        cea = CourseEnrollmentAllowed.objects.filter(email=student.email).delete()

        if cea is None:
            log_message = "%s was successfully unenrolled from %s" % (
                student.email, self.name)
            log.info(log_message)
            return False
        else:
            log_message = "Attempt to unenroll %s from %s was unsuccessful" % (
                student.email, self.name)
            log.info(log_message)
            return True


    def enroll_student_in_a_specific_module(self, student_email, course):
        """
        Enroll a student in a specific module, given the course_id
        e.g. Careers module: 'course-v1:code_institute+cc_101+2018_T1'
        """
        enroll_email(course.id, student_email, auto_enroll=True)
        cea, _ = CourseEnrollmentAllowed.objects.get_or_create(
            course_id=course.id, email=student_email)
        cea.auto_enroll = True
        cea.save()

        student_to_be_enrolled = User.objects.get(email=student_email)

        self.enrolled_students.add(student_to_be_enrolled)

        student_successfully_enrolled = None
        log_message = ""

        if self.enrolled_students.filter(email=student_email).exists():
            student_successfully_enrolled = True
        else:
            student_successfully_enrolled = False
            log_message = "Failed to enroll %s in module %s of the %s program" % (
                student_email, course.course_id, self.name)

        log.info(log_message)
        return student_successfully_enrolled


class CourseCode(models.Model):
    """
    Store the key and a display names for each course that belongs to a program
    """

    class Meta:
        app_label = 'ci_program'

    key = models.CharField(
        help_text="The 'course' part of course_keys associated with this course code, "
                  "for example 'DemoX' in 'edX/DemoX/Demo_Course'.",
        max_length=128
    )
    display_name = models.CharField(
        help_text=_('The display name of this course code.'),
        max_length=128,
    )
    programs = models.ManyToManyField(
        Program, related_name='course_codes', through='ProgramCourseCode')

    def code_sections(self):
        return self.key.split('+')

    def __str__(self):
        return "<%s: %s>" % (self.key, self.display_name)


class ProgramCourseCode(TimeStampedModel):
    """
    Represents the many-to-many association of a course code with a program.
    """
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    course_code = models.ForeignKey(CourseCode, on_delete=models.CASCADE)
    position = models.IntegerField()

    class Meta(object):  # pylint: disable=missing-docstring
        ordering = ['position']
        app_label = 'ci_program'

    def __str__(self):
        return "<%s: %s>" % (self.program.name, self.course_code.key)
