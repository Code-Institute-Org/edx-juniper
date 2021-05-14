"""
A command that will notify zapier of any students that haven't logged in
to get access to the 5DCC yet.

This will be run every Tuesday morning at 09:30, giving the students a
24-hour period to log in before being notified.

This will simply get the locator for the 5DCC run that is currently
associated with the 5DCC program and will iterate over all of the
students that are enrolled in that run of the 5DCC and their email
address will be sent to Zapier, where HubSpot will take over the handling
of sending the emails to the students.
"""
from django.core.management.base import BaseCommand

import logging
log = logging.getLogger(__name__)

from student_enrollment.tasks import reminder


class Command(BaseCommand):
    help = "Send a reminder to students that have yet to log in"

    def handle(self, *args, **kwargs):
        """
        Send a reminder to each student that has yet to log in the
        platform.

        The 5DCC will trigger a zap to notify the student's that they
        yet logged in and that they should do so.

        TODO: Implement this same functionality for FS
        """
        log.info("Running task reminder...")

        result = reminder.apply()
        log.info("Result: %s" % result)
