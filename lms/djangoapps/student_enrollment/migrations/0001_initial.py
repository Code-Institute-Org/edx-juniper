# Generated by Django 2.2.14 on 2020-08-10 11:49

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ci_program', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentEnrollment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('is_active', models.BooleanField()),
                ('program', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ci_program.Program')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ProgramAccessStatus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('program_access', models.BooleanField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='EnrollmentStatusHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('registered', models.BooleanField()),
                ('enrollment_type', models.IntegerField(choices=[(0, 'ENROLLMENT_TYPE__ENROLLMENT'), (1, 'ENROLLMENT_TYPE__UNENROLLMENT'), (2, 'ENROLLMENT_TYPE__REENROLLMENT'), (3, 'ENROLLMENT_TYPE__UPGRADE')])),
                ('enrolled', models.BooleanField()),
                ('email_sent', models.BooleanField()),
                ('enrollment_attempt', models.DateTimeField(auto_now_add=True)),
                ('program', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ci_program.Program')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
