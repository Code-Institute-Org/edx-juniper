# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('challenges', '0004_auto_20190117_1538'),
    ]

    operations = [
        migrations.AddField(
            model_name='challengesubmission',
            name='attempts',
            field=models.IntegerField(default=1),
        ),
        migrations.AlterField(
            model_name='challenge',
            name='level',
            field=models.CharField(max_length=50, choices=[(b'Required', b'Required'), (b'Bonus', b'Bonus'), (b'Optional', b'Optional')]),
        ),
        migrations.AlterUniqueTogether(
            name='challengesubmission',
            unique_together=set([('student', 'challenge')]),
        ),
    ]
