from django.core.management.base import BaseCommand
from django.conf import settings

from learning_success.tasks import export_coding_challenge_data

import logging
log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '''
        Post the results of challenge submissions submitted in the last
        day for a given coding challenge program
    '''

    def add_arguments(self, parser):
        parser.add_argument('program_code', type=str)
        parser.add_argument('--dbname', type=str, default='challenges')
        parser.add_argument('--queue', type=str,
                            default=settings.DEFAULT_LMS_QUEUE)

    def handle(self, program_code, dbname, queue, **kwargs):
        log.info("Running task export_coding_challenge_data on queue %s",
                 queue)

        result = export_coding_challenge_data.apply_async(
            args=[program_code], kwargs={'dbname': dbname}, queue=queue)
        log.info("Result: %s" % result)
