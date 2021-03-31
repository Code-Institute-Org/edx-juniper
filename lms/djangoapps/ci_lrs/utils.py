import json
import logging
import requests

from celery import task
from celery.utils.log import get_task_logger
from celery_utils.logged_task import LoggedTask
from django.conf import settings
from django.conf import settings
from django.utils import timezone

ENDPOINT = settings.LRS_ENDPOINT
API_KEY = settings.LRS_API_KEY
HEADERS = {'x-api-key': API_KEY}

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
        logger.info("Attempting to store LRS record")
        res = requests.post(ENDPOINT, data=json.dumps(data), headers=HEADERS,
                            timeout=1)
        return res.status_code == 200
    except TimeoutError:
        logger.exception("LRS Timeout")
        return False
