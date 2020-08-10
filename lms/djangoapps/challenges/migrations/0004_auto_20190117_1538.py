# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('challenges', '0003_auto_20190110_1552'),
    ]

    operations = [
        migrations.AlterField(
            model_name='challenge',
            name='block_locator',
            field=models.CharField(max_length=120),
        ),
    ]
