"""
A convience API for handle common interactions with the Program model.

This is simply a set of functions that can be used elsewhere to abstract some
of the complexities in certain aspects of the codebase, but also to remove the
need to import the Program model elsewhere.

    `get_program_by_program_code` will retreive a specific program object
        based on the `program_code`

    `enroll_student_in_program` will enroll the provided `student` into the
        provided `program` (both the `program` and `student` are instances).
        Returns a True or False status to notify if the enrollment was
        successful

    `get_enrolled_students` returns the number of students enrolled in a given
        program

    `is_enrolled_in_program` will check to see if a student is enrolled in a
        given program

    `number_of_enrolled_students` will return the number of students enrolled
        in a given program

    `number_of_students_logged_into_access_program` will provide the total
        number of students in a program that have logged into the LMS

    `get_courses_locators_for_program` will return a list of the course
        locators containing the locator for module contained within that
        program

    `get_all_programs` will return a Queryset containing every program object
        stored in the `ci_program` model

    `student_has_logged_in` will check to see if a specific student has logged
        in
"""
from django.http.response import Http404
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from ci_program.models import Program


def get_all_programs():
    """
    Get collection of all of program codes from the `Program` model
    """
    return Program.objects.all()


def get_program_by_program_code(code):
    """
    Query the database for a specific program based on the program code

    `code` is the code that we use to identify the program

    Returns an instance of the program. Raises a 404 if the program
        doesn't exist
    """
    return get_object_or_404(Program, program_code=code)


def enroll_student_in_program(code, email):
    """
    Enroll a student in a program.

    `code` is the code of the program that we want to enroll the
        student in
    `email` is the email of the user that we wish to enroll
    Note that the student must already be registered to the platform

    Returns the status of the enrollment
    """
    program = get_program_by_program_code(code)
    student = get_object_or_404(User, email=email)
    enrollment_status = program.enroll_student_in_program(student)
    return enrollment_status


def get_enrolled_students(code):
    """
    Gets a list of the enrolled students enrolled in a given program

    `code` is the code of the program that we want to get the list
        of enrolled users from

    Returns a collection of all `user` objects
    """
    program = get_program_by_program_code(code)
    return program.enrolled_students.all()


def is_student_enrolled_in_program(code, email):
    """
    Check whether a given student is enrolled in a given program

    `code` is the course code used as an identifier for a program
    `email` is the email of the user that we want to check for

    Returns True or False based on whether or not a student is enrolled
        in the program
    """
    program = get_program_by_program_code(code)
    return program.enrolled_students.filter(email=email).exists()


def number_of_enrolled_students(code):
    """
    Get the number of students that are enrolled in a given program

    `code` is the code of the program that we're interested in

    Returns the total number of students enrolled
    """
    program = get_program_by_program_code(code)
    return program.enrolled_students.count()


def number_of_students_logged_into_access_program(code):
    """
    Get the number of students that have logged into the LMS to get
    access to their course content.

    `code` is the code of the program we are interested in.

    Returns the total number of students that have logged
        per-program
    """
    program = get_program_by_program_code(code)
    return program.enrolled_students.exclude(last_login__isnull=True).count()


def get_course_locators_for_program(code):
    """
    Get a list of CourseLocator objects for each module in a program

    `code` is the course code used as an identifier for a program

    Returns a list of CourseLocator objects
    """
    program = get_program_by_program_code(code)
    return program.get_course_locators()


def get_courses_from_program(code):
    """
    """
    program = get_program_by_program_code(code)
    return program.get_courses()
