import shutil
import json

from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from xmodule.modulestore.django import modulestore

from logging import getLogger

from celery import task
from celery_utils.logged_task import LoggedTask
from django.core.management.base import BaseCommand, CommandError

from lms.djangoapps.certificates.models import CertificateGenerationCourseSetting

log = getLogger(__name__)


@task(base=LoggedTask)
def configure_certificate(course_id=None, self_generation_enabled=None):
    log.info("Configuring Certificate for course %s - self_generation_enabled: %s",
             course_id, self_generation_enabled)

    try:
        course_key = CourseKey.from_string(course_id)
    except InvalidKeyError:
        raise CommandError(u"Invalid course_key: '%s'." % course_id)

    if not modulestore().get_course(course_key):
        raise CommandError(u"Course with %s key not found." % course_id)

    course_setting = CertificateGenerationCourseSetting.objects.get(course_key=course_key)
    course_setting.self_generation_enabled = self_generation_enabled
    course_setting.save()

    log.info("Configured Certificate for course %s - self_generation_enabled: %s",
             course_id, self_generation_enabled)
