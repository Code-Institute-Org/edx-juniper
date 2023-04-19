import random
from unittest.mock import patch, MagicMock

from django.conf import settings
from django.utils import timezone
from django.test import TestCase, override_settings
from pymongo.errors import ConnectionFailure, DuplicateKeyError, NetworkTimeout, OperationFailure, ServerSelectionTimeoutError

from ci_lrs.utils import write_lrs_record_to_mongo


class TestLRSTasks(TestCase):
    def setUp(self):
        self.mongodb = settings.LRS_INTEGRATIONS_MONGO_DB[settings.LRS_INTEGRATIONS_MONGO_COLLECTION]
        self.mongodb.delete_many({})

    def test_write_lrs_record_to_mongo(self):
        context = {
            'activity_time': timezone.now().isoformat(),
            'actor': 1,
            'verb': 'play_video',
            'activity_object': 'myopenedx.com/urlToPage',
            'extra_data': '{\"position\": 1}',
        }
 
        write_lrs_record_to_mongo(context)
        lrs_record = self.mongodb.find_one()
        self.assertEquals(lrs_record, context)

    def test_write_lrs_record_to_mongo_backoff(self):
        context = {
            'activity_time': timezone.now().isoformat(),
            'actor': 1,
            'verb': 'play_video',
            'activity_object': 'myopenedx.com/urlToPage',
            'extra_data': '{\"position\": 1}',
        }
 
        mock_mongo = {}
        mock_mongo['fail'] = MagicMock()
        mock_mongo['fail'].insert_one = MagicMock()
        mock_mongo['fail'].insert_one.side_effect = [
                ConnectionFailure("Error"), DuplicateKeyError("Error"), NetworkTimeout("Error"),
                OperationFailure("Error"), ServerSelectionTimeoutError("Error"), True]

        with override_settings(LRS_INTEGRATIONS_MONGO_DB=mock_mongo, LRS_INTEGRATIONS_MONGO_COLLECTION='fail'):
            self.assertEquals(write_lrs_record_to_mongo(context), 5)

