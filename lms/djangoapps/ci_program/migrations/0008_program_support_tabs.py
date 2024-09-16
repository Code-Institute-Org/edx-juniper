# Generated by Django 2.2.14 on 2024-04-26 16:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ci_program', '0007_auto_20230613_1400'),
    ]

    operations = [
        migrations.AddField(
            model_name='program',
            name='support_tabs',
            field=models.CharField(blank=True, help_text='Comma-separated list of support tabs available for Program', max_length=255, null=True),
        ),
    ]