from logging import getLogger

from django.core.management.base import BaseCommand
log = getLogger(__name__)

from learning_success.tasks import enroll_students_in_careers_module

"""
Students on the Full Stack Developer course are enrolled in the Careers module
following submission of their Interactive milestone project. Students eligible to
be enrolled will have a status of 'Enroll' for the 'Access to Careers Module' field
on their CRM profile.
"""


class Command(BaseCommand):
    help = 'Enroll students in the careers module'

    def add_arguments(self, parser):
        parser.add_argument('--queue', type=str,
                            default=settings.DEFAULT_LMS_QUEUE)
        parser.add_argument('--dryrun', action='store_true')

    def handle(self, queue, dryrun, *args, **kwargs):
        """
        This will retrieve all of the users from the Zoho CRM API and
        with an 'Access to Careers Module' status of 'Enroll' and
        will enroll the student in the Careers module.
        """

        log.info("Running task enroll_students_in_careers_module...")

        result = enroll_students_in_careers_module.apply_async(args=[dryrun],
                                                               queue=queue)
        log.info("Result: %s" % result)
