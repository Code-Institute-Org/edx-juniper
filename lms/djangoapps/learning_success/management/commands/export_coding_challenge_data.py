from django.core.management.base import BaseCommand

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

    def handle(self, program_code, **kwargs):
        log.info("Running task export_coding_challenge_data...")

        result = export_coding_challenge_data.apply(args=[program_code], kwargs=kwargs)
        log.info("Result: %s" % result)
