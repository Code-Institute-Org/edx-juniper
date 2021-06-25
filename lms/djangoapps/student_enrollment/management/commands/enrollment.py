
from django.core.management.base import BaseCommand
from django.conf import settings

import logging
log = logging.getLogger(__name__)

from student_enrollment.tasks import enrollment


"""
Students starting the Full Stack Developer course should initially not be
enrolled into the Careers module. It should be made available after the submission
of the Interactive Frontend Development. See "Enroll student in careers module"
Zap.

This collection is used to store any courses that should be excluded from the
initial student onboarding/enrollment process like the Careers module.
"""


class Command(BaseCommand):
    help = 'Enroll students in their relevant programs'

    def add_arguments(self, parser):
        parser.add_argument('--queue', type=str,
                            default=settings.DEFAULT_LMS_QUEUE)
        parser.add_argument('--dryrun', action='store_true')

    def handle(self, queue, dryrun, **kwargs):
        """
        The main handler for the program enrollment management command.
        This will retrieve all of the users from the Zoho CRM API and
        will enroll all of the students that have a status of
        `Enroll`.

        If a student doesn't exist in the system, then we will first register them
        and then enroll them in the relevant programme (specified by Programme_ID)
        """
        log.info("Running task enrollment on queue %s", queue)

        result = enrollment.apply_async(args=[dryrun], queue=queue)
        log.info("Result: %s" % result)
