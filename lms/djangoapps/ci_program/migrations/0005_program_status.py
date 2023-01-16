# Generated by Django 2.2.14 on 2022-11-01 12:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ci_program', '0004_auto_20220714_1130'),
    ]

    operations = [
        migrations.AddField(
            model_name='program',
            name='status',
            field=models.CharField(choices=[('live', 'Live'), ('in_development', 'In Development'), ('end_of_sale', 'End of Sale'), ('end_of_life', 'End of Life')], default='in_development', max_length=16),
        ),
    ]