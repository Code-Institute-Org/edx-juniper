from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from learning_success.tasks import export_all_activity_records

import logging
log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Extract student data from the open-edX server for use in Strackr'

    def add_arguments(self, parser):
        parser.add_argument('source_platform', type=str)
        parser.add_argument('pathway', type=str)
        parser.add_argument('programme_ids', type=str, nargs='+')
        parser.add_argument('--queue', type=str,
                            default=settings.DEFAULT_LMS_QUEUE)
        parser.add_argument('--dryrun', action='store_true')

    def handle(self, source_platform, pathway, programme_ids, queue, dryrun,
               **kwargs):
        """ POST the collected data to the api endpoint from the settings
            Arguments:
                source_platform: Platform import as, i.e. 'juniper' or 'ginkgo'
                programme_ids: Programme ids of programme to use 'disd'

        Example command:
        docker-compose exec ci-lms python3 manage.py lms export_all_activity_records juniper fullstack disd diwad

        The table should have one entry per day per platform and programme
        per student.

        In order to be able to easily re-run the extract any given day
        without any further intervention we are deleting any existing
        entry first.

        With the use of one transaction for deletion and insertion we can
        make sure that one does not happen without the other as to not
        lose any information.
        """

        log.info("Running task export_all_activity_records on queue %s", queue)

        result = export_all_activity_records.apply_async(
            args=[source_platform, pathway, programme_ids, dryrun],
            queue=queue)
        log.info("Result: %s" % result)
