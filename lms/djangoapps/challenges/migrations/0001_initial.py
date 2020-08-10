# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import openedx.core.djangoapps.xmodule_django.models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Challenge',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=120)),
                ('block_locator', openedx.core.djangoapps.xmodule_django.models.LocationKeyField(max_length=120)),
            ],
        ),
        migrations.CreateModel(
            name='ChallengeSubmission',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('time_challenge_started', models.DateTimeField()),
                ('time_challenge_submitted', models.DateTimeField()),
                ('passed', models.BooleanField()),
                ('challenge', models.ForeignKey(to='challenges.Challenge')),
                ('student', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
