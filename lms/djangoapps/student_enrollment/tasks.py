
from celery import task
from celery_utils.logged_task import LoggedTask

from student_enrollment.enrollment import Enrollment
from student_enrollment.unenrollment import Unenrollment
from student_enrollment.enroll_students_in_careers_module import (
    StudentCareerEnrollment)
from student_enrollment.enrollment_stats import (
    EnrollmentStats)
from student_enrollment.reminder import Reminder


@task(base=LoggedTask)
def enrollment():
    ''' Enroll students in their relevant programs
    '''
    Enrollment().enroll()


@task(base=LoggedTask)
def unenrollment():
    ''' Unenroll students from their relevant programs
    '''
    Unenrollment().unenroll()


@task(base=LoggedTask)
def enroll_students_in_careers_module():
    ''' Enroll students in the careers module
    '''
    StudentCareerEnrollment().enroll_in_careers()


@task(base=LoggedTask)
def enrollment_stats():
    ''' Generate the enrollment stats for the 5DCC and email them to marketing
    '''
    EnrollmentStats().generate()


@task(base=LoggedTask)
def reminder():
    ''' Generate the enrollment stats for the 5DCC and email them to marketing
    '''
    Reminder().send_reminder()
