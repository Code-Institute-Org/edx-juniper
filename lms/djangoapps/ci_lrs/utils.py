import json
import logging
import requests

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__file__)

ENDPOINT = settings.LRS_ENDPOINT
API_KEY = settings.LRS_API_KEY
HEADERS = {'x-api-key': API_KEY}


def store_lrs_record(actor, activity_action, learning_block_id,
        extra_data=None):
    """ Sends an API call to store the student progress in an external DB """
    if isinstance(extra_data, dict) or isinstance(extra_data, list):
        extra_data = json.dumps(extra_data)

    data = {
        "activity_time": timezone.now().isoformat(),
        "actor": actor,
        "activity_action": activity_action,
        "learning_block_id": learning_block_id,
        "extra_data": extra_data,
    }
    logger.exception(data)
    res = requests.post(ENDPOINT, data=json.dumps(data), headers=HEADERS)
    logger.exception(res.content)
    return res.status_code == 200
