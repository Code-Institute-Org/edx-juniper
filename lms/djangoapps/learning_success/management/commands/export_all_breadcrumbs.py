from django.core.management.base import BaseCommand, CommandError

from learning_success.tasks import export_all_breadcrumbs

import logging
log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Extract LMS breadcrumbs into a relational database table'

    def add_arguments(self, parser):
        parser.add_argument('programme_id', type=str)

    def handle(self, programme_id):
        log.info("Running task export_all_breadcrumbs...")

        result = export_all_breadcrumbs.apply(args=[programme_id])
        log.info("Result: %s" % result)
