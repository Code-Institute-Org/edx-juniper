# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ci_program', '0003_auto_20180704_1629'),
        ('student_enrollment', '0003_auto_20180601_0942'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentEnrollment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('is_active', models.BooleanField()),
                ('program', models.ForeignKey(to='ci_program.Program')),
                ('student', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-modified', '-created'),
                'abstract': False,
                'get_latest_by': 'modified',
            },
        ),
        migrations.AlterField(
            model_name='enrollmentstatushistory',
            name='enrollment_type',
            field=models.IntegerField(choices=[(0, b'ENROLLMENT_TYPE__ENROLLMENT'), (1, b'ENROLLMENT_TYPE__UNENROLLMENT'), (2, b'ENROLLMENT_TYPE__REENROLLMENT'), (3, b'ENROLLMENT_TYPE__UPGRADE')]),
        ),
    ]
