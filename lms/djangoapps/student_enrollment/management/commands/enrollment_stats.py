"""
NOTE: WIP NOT FULLY TESTED!!!

A command that will notify the marketing team of the enrollment stats for the
5DCC of the 5DCC on a weekly basis.

This command will run every Monday morning at 09:00. It will send an email to
Ciara containing the following information -

    `number_of_students_enrolled`
    `number_of_students_logged_in`
    `total_percentage`
"""
from django.core.management.base import BaseCommand

from learning_success.tasks import enrollment_stats

import logging
log = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Generate the enrollment stats for the 5DCC and email them to marketing'


    def handle(self, *args, **options):
        # 5DCC only has one module associated with it so we only care
        # about a single item for the `get_courses_locators_for_program`
        log.info("Running task enrollment_stats...")

        result = enrollment_stats.apply()
        log.info("Result: %s" % result)
