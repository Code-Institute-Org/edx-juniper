
import os
import tempfile
import shutil
import tarfile
import time
import json
from datetime import datetime
from datetime import timedelta

from logging import getLogger


import boto3
from botocore.exceptions import ClientError

from celery import task
from celery_utils.logged_task import LoggedTask

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey

from xmodule.contentstore.django import contentstore
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.xml_exporter import export_course_to_xml
from xmodule.modulestore.xml_importer import import_course_from_xml
from xmodule.modulestore import ModuleStoreEnum

log = getLogger(__name__)


@task(base=LoggedTask)
def export_to_s3(course_id, timestamp):
    try:
        log.info("Exporting to S3: %s %s", course_id, timestamp)
        try:
            course_key = CourseKey.from_string(course_id)
        except InvalidKeyError:
            raise CommandError(u"Invalid course_key: '%s'." % course_id)

        if not modulestore().get_course(course_key):
            raise CommandError(u"Course with %s key not found." % course_id)

        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, "course")
        os.makedirs(output_path, exist_ok=True)

        log.info("Exporting course %s to %s", course_key, output_path)

        root_dir = os.path.dirname(output_path)
        course_dir = os.path.splitext(os.path.basename(output_path))[0]

        log.info("Export: %s %s %s", course_key, root_dir, course_dir)
        export_course_to_xml(modulestore(), contentstore(), course_key, root_dir, course_dir)

        tarfile_filename = "%s_%s.tar.gz" % (course_id, timestamp)
        tarfile_path = os.path.join(temp_dir, tarfile_filename)

        log.info("Creating tarfile: %s", tarfile_path)
        with tarfile.open(tarfile_path, "w:gz") as tar:
            tar.add(output_path, arcname="%s_%s" % (course_id, timestamp))

        # send to S3
        client = boto3.client(
            's3',
            aws_access_key_id=settings.MODULE_EXPORTIMPORT_S3_ACCESS_KEY,
            aws_secret_access_key=settings.MODULE_EXPORTIMPORT_S3_SECRET_KEY
        )
        object_name = os.path.join(settings.MODULE_EXPORTIMPORT_S3_FOLDER, tarfile_filename)

        log.info("Uploading file from %s to %s", tarfile_filename, object_name)
        client.upload_file(tarfile_path, settings.MODULE_EXPORTIMPORT_S3_BUCKET, object_name)

        shutil.rmtree(temp_dir)
        log.info("Finished export task")
    except Exception as e:
        log.exception("Unknown exception exporting module: %s %s",
                      course_id, timestamp)
        raise


def s3_file_exists(client, object_name):
    bucket_name = settings.MODULE_EXPORTIMPORT_S3_BUCKET
    log.debug("Check S3 file exists: %s %s", bucket_name, object_name)
    try:
        client.get_object(Bucket=bucket_name, Key=object_name)
        return True
    except ClientError as ex:
        if ex.response['Error']['Code'] == 'NoSuchKey':
            return False
        else:
            raise


def write_results_to_s3(client, course_id, timestamp, result):
    log.debug("Writing result %s %s %s", course_id, timestamp, result)

    result_filename = "%s_%s.json" % (course_id, timestamp)
    result_key = os.path.join(settings.MODULE_EXPORTIMPORT_S3_FOLDER, result_filename)
    client.put_object(
        Body=json.dumps(result, indent=4),
        Bucket=settings.MODULE_EXPORTIMPORT_S3_BUCKET,
        Key=result_key)


@task(base=LoggedTask)
def import_from_s3(course_id, timestamp):
    log.info("Importing from S3: %s %s", course_id, timestamp)

    # copy from S3
    client = boto3.client(
        's3',
        aws_access_key_id=settings.MODULE_EXPORTIMPORT_S3_ACCESS_KEY,
        aws_secret_access_key=settings.MODULE_EXPORTIMPORT_S3_SECRET_KEY
    )

    try:
        # extract
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, "course")
        os.makedirs(output_path, exist_ok=True)

        tarfile_filename = "%s_%s.tar.gz" % (course_id, timestamp)

        tarfile_path = os.path.join(temp_dir, tarfile_filename)
        object_name = os.path.join(settings.MODULE_EXPORTIMPORT_S3_FOLDER, tarfile_filename)

        log.info("Downloading tarfile: %s", tarfile_path)

        # wait for file to exist (waiting on export from source to complete)
        retry_until = datetime.now() + timedelta(seconds=30)
        while not s3_file_exists(client, object_name) and datetime.now() < retry_until:
            time.sleep(3)

        log.info("Attempting download file: from %s to ", object_name, tarfile_path)
        client.download_file(settings.MODULE_EXPORTIMPORT_S3_BUCKET, object_name, tarfile_path)

        log.info("Extracting tar: %s", tarfile_path)
        with tarfile.open(tarfile_path, "r:gz") as tar:
            tar.extractall(output_path)

        # import module
        log.info("Import course: %s")
        import_course_from_xml(
            modulestore(),
            ModuleStoreEnum.UserID.mgmt_command,
            output_path,
            source_dirs=["%s_%s" % (course_id, timestamp)],
            load_error_modules=False,
            static_content_store=contentstore(),
            verbose=True,
            do_import_static=True,
            target_id=CourseKey.from_string(course_id),
            create_if_not_present=True,
        )

        shutil.rmtree(temp_dir)

        write_results_to_s3(client, course_id, timestamp, {
            "status": "success",
            "lms_base": settings.LMS_BASE})

        log.info("Finished import task")
    except Exception as e:
        log.exception("Unknown exception exporting module: %s %s",
                      course_id, timestamp)
        write_results_to_s3(client, course_id, timestamp, {
            "status": "failed",
            "error": str(e),
            "lms_base": settings.LMS_BASE})
        raise
