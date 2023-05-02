import json
import requests
import time

from celery import task
from celery.utils.log import get_task_logger
from celery_utils.logged_task import LoggedTask
from django.conf import settings
from pymongo.errors import PyMongoError

logger = get_task_logger(__name__)


@task(bind=True, base=LoggedTask)
def attempt_to_store_lrs_record(self, data):
    """ Sends an API call to store the student progress in an external DB

        context = {
            'activity_time': timezone.now().isoformat(),
            'actor': 1 # (request.user.id),
            'verb': 'play_video', # (this is the edx event_type)
            'activity_object': 'myopenedx.com/urlToPage' # (url to page)
            'extra_data': '{\"position\": 1}' # (any extra data of the event)
        }

    """
    try:
        data['activity_time'] = data['activity_time'].isoformat()
        res = requests.post(settings.LRS_ENDPOINT, data=json.dumps(data),
                            headers={'x-api-key': settings.LRS_API_KEY},
                            timeout=settings.LRS_TIMEOUT)
        return res.status_code == 200
    except TimeoutError:
        logger.exception("LRS Timeout")
        return False

@task(bind=True, base=LoggedTask)
def write_lrs_record_to_mongo(self, data):
    """ Writes LRS data directly to DB
    Retries on exception with incremental backoff

        context = {
            'activity_time': timezone.now().isoformat(),
            'actor': 1 # (request.user.id),
            'verb': 'play_video', # (this is the edx event_type)
            'activity_object': 'myopenedx.com/urlToPage' # (url to page)
            'extra_data': '{\"position\": 1}' # (any extra data of the event)
        }
    """
    increment = 0
    backoff_intervals = [1, 2, 5, 10, 30, 60, 300]

    while True:
        try:
            # Store info in database
            data['environment'] = settings.SITE_NAME
            settings.LRS_MONGO_DB[settings.LRS_STUDENT_ACTIVITY_COLLECTION].insert_one(data)
            return increment
        except PyMongoError:
            logger.exception("LRS Mongo Error")
            backoff_seconds = backoff_intervals[increment]
            if backoff_seconds < 300:
                increment += 1
            time.sleep(backoff_seconds)

