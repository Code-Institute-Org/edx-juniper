
from django.core.management.base import BaseCommand
from django.conf import settings

import logging
log = logging.getLogger(__name__)

from student_enrollment.tasks import unenrollment


class Command(BaseCommand):
    help = 'Unenroll students from their relevant programs'

    def add_arguments(self, parser):
        parser.add_argument('--queue', type=str,
                            default=settings.DEFAULT_LMS_QUEUE)
        parser.add_argument('--dryrun', action='store_true')

    def handle(self, queue, dryrun, **kwargs):
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
        log.info("Running task unenrollment on queue %s", queue)

        result = unenrollment.apply_async(args=[dryrun], queue=queue)
        log.info("Result: %s" % result)
