import random
from unittest.mock import patch, MagicMock

from django.conf import settings
from django.utils import timezone
from django.test import TestCase, override_settings

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError, NetworkTimeout, OperationFailure, ServerSelectionTimeoutError

from ci_lrs.utils import write_lrs_record_to_mongo


class TestLRSTasks(TestCase):
    def setUp(self):
        self.mongodb = MongoClient('mongodb://mongodb:27017')['test_db']
        self.mongodb['student_activity'].delete_many({})

    def test_write_lrs_record_to_mongo(self):
        context = {
            'activity_time': timezone.now().isoformat(),
            'actor': 1,
            'verb': 'play_video',
            'activity_object': 'myopenedx.com/urlToPage',
            'extra_data': '{\"position\": 1}',
        }
        with override_settings(LRS_MONGO_DB=self.mongodb):
            write_lrs_record_to_mongo(context)
        lrs_record = self.mongodb['student_activity'].find_one()
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
        mock_mongo['student_activity'] = MagicMock()
        mock_mongo['student_activity'].insert_one = MagicMock()
        mock_mongo['student_activity'].insert_one.side_effect = [
                ConnectionFailure("Error"), DuplicateKeyError("Error"), NetworkTimeout("Error"),
                OperationFailure("Error"), ServerSelectionTimeoutError("Error"), True]

        with override_settings(LRS_MONGO_DB=mock_mongo):
            self.assertEquals(write_lrs_record_to_mongo(context), 5)

