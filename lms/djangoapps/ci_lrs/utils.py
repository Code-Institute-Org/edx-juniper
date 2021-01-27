import logging

from django.conf import settings
import MySQLdb

logger = logging.getLogger(__file__)


def store_lrs_record(actor, verb, activity_object, extra_data=None):
    """ Creates a connection to the MySQL database and inserts a new record """
    try:
        db_settings = settings.DATABASES['student_module_history']
        db = MySQLdb.connect(
            db_settings['HOST'],
            db_settings['USER'],
            db_settings['PASSWORD'],
            settings.LRS_DATABASE_NAME)

        insert_activity_query = """ INSERT INTO student_learning_activity (
            actor, verb, activity_object, extra_data) VALUES (
            '{actor}', '{verb}', '{activity_object}', '{extra_data}'
            );""".format(actor=actor,
                         verb=verb,
                         activity_object=activity_object,
                         extra_data=extra_data)
        cursor = db.cursor()
        statement = cursor.execute(insert_activity_query)
        db.commit()
        cursor.close()
        db.close()
    except (MySQLdb.Error, MySQLdb.Warning) as e:
        logger.exception(e)
    return
