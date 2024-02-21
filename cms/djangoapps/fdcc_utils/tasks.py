from datetime import date, timedelta
import logging
import os
import six

from celery.task import task
from celery_utils.logged_task import LoggedTask
from django.contrib.auth.models import User
from django.core.management.base import CommandError

from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from xmodule.modulestore.django import modulestore
from contentstore.views.certificates import CertificateManager, _get_course_and_check_access
from contentstore.views.item import _get_xblock, _save_xblock
from fdcc_utils.utils import get_sections
from lms.djangoapps.certificates.api import set_cert_generation_enabled

log = logging.getLogger(__name__)


@task(base=LoggedTask)
def configure_fdcc_certificate(course_id=None, cert_is_active=None, self_generation_enabled=None):
    log.info(u"Configuring Certificate for course %s - cert_is_active: %s - self_generation_enabled: %s",
             course_id, cert_is_active, self_generation_enabled)

    if not cert_is_active and self_generation_enabled is True:
        raise CommandError(("Enabling certificate self generation without activating the certificate "
                            "will not make the certificate available to students."))

    try:
        course_key = CourseKey.from_string(course_id)
    except InvalidKeyError:
        raise CommandError(u"Invalid course_key: '%s'." % course_id)

    store = modulestore()
    if not store.get_course(course_key):
        raise CommandError(u"Course with %s key not found." % course_id)

    # De-/activate Certificate
    fdcc_admin = User.objects.get(username=os.getenv('FDCC_ADMIN_USERNAME'))
    course = _get_course_and_check_access(course_key, fdcc_admin)
    certificates = CertificateManager.get_certificates(course)
    if not certificates:
        raise CommandError(u"No certificates found for course: '%s' ." % course_id)

    for certificate in certificates:
        certificate['is_active'] = cert_is_active is True
        break

    store.update_item(course, fdcc_admin.id)
    is_active, certificates = CertificateManager.is_activated(course)
    if not is_active and cert_is_active is True:
        raise CommandError(u"There was an error activating the certificate for course '%s'." % course_id)

    cert_event_type = 'activated' if cert_is_active else 'deactivated'
    CertificateManager.track_event(cert_event_type, {'course_id': six.text_type(course.id)})

    # Dis-/enable certificate self generation
    set_cert_generation_enabled(course_key, self_generation_enabled)

    log.info(u"Configured Certificate for course %s - cert_is_active: %s - self_generation_enabled: %s",
             course_id, cert_is_active, self_generation_enabled)


@task(base=LoggedTask)
def schedule_fdcc_module(course_id=None, only_visible=None):
    log.info(u"Configuring schedule for course %s (only visible: %s)", course_id, only_visible)
    start_date = date.today()
    # If not run on a Monday, make start_date to be the Monday of the current week
    if date.today().weekday() != 0:
        start_date = start_date - timedelta(days=start_date.weekday())

    fdcc_admin = User.objects.get(username=os.getenv('FDCC_ADMIN_USERNAME'))
    sections = get_sections(course_id, (only_visible is True))
    for i, section_xblock in enumerate(sections):
        day_increment = min(i, 4)  # Max 4 days which brings it to Friday
        start_time = (start_date + timedelta(days=day_increment)).strftime('%Y-%m-%d') + 'T05:00:00Z'
        log.info(u"Setting start time for section '%s' to %s", section_xblock.display_name, start_time)
        _save_xblock(fdcc_admin, section_xblock, metadata={'start': start_time})
        for lesson in section_xblock.children:
            lesson_xblock = _get_xblock(lesson, fdcc_admin)
            log.info(u"Setting start time for lesson '%s' to %s", lesson_xblock.display_name, start_time)
            _save_xblock(fdcc_admin, lesson_xblock, metadata={'start': start_time})

    log.info(u"Configured schedule for course %s (only visible: %s)", course_id, only_visible)
