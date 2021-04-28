""" Module handles any challenge or challenge tag related logic """
from challenges.models import Challenge

from copy import deepcopy
from collections import Counter, defaultdict
import json

from lms.djangoapps.learning_success.management.commands.export_all_breadcrumbs import get_safely  # noqa: E501

DEFAULT_SKILL = {
    'achieved': 0,
    'total': 0,
}


def increment_student_skill_tags(student_skills, skill_tags):
    """ Increments the student's achieved skill tags based on the skill tags
    of the challenge

    Modifies dict inplace """
    for skill in skill_tags:
        student_skills[skill]['achieved'] += 1


def generate_default_skills(skill_tags):
    """ Generates the default skills and populates the totals

    Returns a dict with the totals for the challenge tags"""
    default_skills = {}
    for skills in skill_tags.values():
        for skill in skills:
            default_skills.setdefault(skill, deepcopy(DEFAULT_SKILL))
            default_skills[skill]['total'] += 1
    return default_skills


def index_challenge_to_module_and_level():
    """ Collects all Challeges in the LMS

    TODO: Consider limiting it only to get a speficied program

    Returns a dict of all challenges with its PK and category"""
    challenge_index = {}
    skill_tags = {}
    for challenge in Challenge.objects.all():
        module = challenge.block_locator.split('+')[1].lower()
        module_level = "_".join((module, challenge.level)).lower()
        challenge_index[challenge.pk] = module_level
        skill_tags[challenge.pk] = [tag.name for tag in challenge.tags.all()]
    return challenge_index, skill_tags


def single_student_challenge_history(student, challenge_counter,
                                     challenge_index, skill_tags,
                                     default_skills):
    """ Creates the challenge history for one student

    Returns a dict with with passed, attempted and unattempted counts """
    challenge_activities = {module: defaultdict(int) for module
                            in challenge_counter.keys()}
    student_skills = deepcopy(default_skills)

    for submission in student.challengesubmission_set.all():
        module = challenge_index[submission.challenge_id]
        challenge_tags = skill_tags[submission.challenge_id]
        if submission.passed:
            challenge_activities[module]['passed'] += 1
            increment_student_skill_tags(student_skills, challenge_tags)
        else:
            challenge_activities[module]['attempted'] += 1
        challenge_activities[module]['num_attempts'] += submission.attempts

    for module_level, total_challenges in challenge_counter.items():
        activities = challenge_activities[module_level]
        activities['unattempted'] = (
            total_challenges - activities['passed'] - activities['attempted'])
        activities.setdefault('num_attempts', 0)

    challenge_activities = {
        module: json.dumps(challenges)
        for module, challenges in challenge_activities.items()
    }
    challenge_activities['student_skills'] = json.dumps(student_skills)
    return challenge_activities


def extract_all_student_challenges(program):
    """ Calculates the historical challenge data for all students

    Returns a dict with email and challenge history for each student """
    challenge_index, skill_tags = index_challenge_to_module_and_level()
    default_skills = generate_default_skills(skill_tags)
    challenge_counter = Counter(challenge_index.values())
    students = program.enrolled_students.all()
    challenge_history = {
        student.email: single_student_challenge_history(
            student, challenge_counter, challenge_index, skill_tags,
            default_skills)
        for student in students.prefetch_related('challengesubmission_set')
    }
    return challenge_history
