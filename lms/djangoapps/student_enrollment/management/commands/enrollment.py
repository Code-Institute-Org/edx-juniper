
from django.core.management.base import BaseCommand

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

    def handle(self):
        """
        The main handler for the program enrollment management command.
        This will retrieve all of the users from the Zoho CRM API and
        will enroll all of the students that have a status of
        `Enroll`.

        If a student doesn't exist in the system, then we will first register them
        and then enroll them in the relevant programme (specified by Programme_ID)
        """
        log.info("Running task enrollment...")

        result = enrollment.apply()
        log.info("Result: %s" % result)
