# Generated by Django 2.2.12 on 2020-05-21 10:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('edxval', '0002_add_error_description_field'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='TranscriptCredentials',
            unique_together=set(),
        ),
        migrations.DeleteModel(
            name='TranscriptCredentials',
        ),
    ]