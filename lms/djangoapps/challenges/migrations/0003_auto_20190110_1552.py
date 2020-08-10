# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('challenges', '0002_auto_20190110_1540'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='tag',
            options={'ordering': ('sort_key',)},
        ),
        migrations.AddField(
            model_name='challenge',
            name='level',
            field=models.CharField(default=1, max_length=50, choices=[(1, b'Required'), (2, b'Optional'), (3, b'Bonus')]),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tag',
            name='sort_key',
            field=models.IntegerField(default=1),
            preserve_default=False,
        ),
    ]
