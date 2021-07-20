
from celery import task
from celery_utils.logged_task import LoggedTask

from learning_success.export_all_activity_records import export_all_activity_records as perform_activity_export  # noqa
from learning_success.export_coding_challenge_data import (
    CodeChallengeExporter)
from learning_success.export_all_breadcrumbs import BreadcrumbExporter


@task(base=LoggedTask)
def export_all_activity_records(source_platform, pathway, programme_ids,
                                dryrun=False):
    """ POST the collected data to the api endpoint from the settings
        Arguments:
            source_platform: Platform import as, i.e. 'juniper' or 'ginkgo'
            programme_ids: Programme ids of programme to use 'disd'

    The table should have one entry per day per platform and programme
    per student.

    In order to be able to easily re-run the extract any given day
    without any further intervention we are deleting any existing
    entry first.

    With the use of one transaction for deletion and insertion we can
    make sure that one does not happen without the other as to not
    lose any information.
    """
    perform_activity_export(source_platform, pathway, programme_ids, dryrun)


@task(base=LoggedTask)
def export_coding_challenge_data(program_code, dryrun=False, dbname=None):
    ''' Post the results of challenge submissions submitted in the last day
        for a given coding challenge program

        Arguments:
            program_code: 'disd' etc
            dbname: mongo db name - defaults to 'challenges' is not specified
    '''
    CodeChallengeExporter().export(program_code, dryrun, dbname)


@task(base=LoggedTask)
def export_all_breadcrumbs(programme_id):
    ''' Extract LMS breadcrumbs into a relational database table
        Arguments:
            programme_id: 'disd' etc
    '''
    BreadcrumbExporter().export(programme_id)
