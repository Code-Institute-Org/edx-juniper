""" Module handles any challenge or challenge tag related logic

Example data construct returned:
{
    'user@example.codeinstitute.net': {
        'cpl_06_20_required': '{"passed": 1, "num_attempts": 3, "attempted": 0, "unattempted": 0}',
        'student_skills': '{"Python": {"achieved": 1, "total": 1}}'
    }
}
"""
from copy import deepcopy
from collections import Counter, defaultdict
import json
import re

from django.conf import settings

from challenges.models import Challenge
from lms.djangoapps.learning_success.management.commands.export_all_breadcrumbs import get_safely  # noqa: E501

DEFAULT_CHALLENGE = {
    'passed': 0,
    'num_attempts': 0,
    'attempted': 0,
    'unattempted': 0
}
DEFAULT_SKILL = {
    'achieved': 0,
    'total': 0,
}
CHALLENGE_PATTERN = r"[\/]challenges[\/]([a-zA-Z0-9]*)[\"|']"


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


def extract_challenge_submissions():
    """ Queries the mongodb for all challenge submissions and aggregates the
    results in such a way that we get the most recent submission's passed
    status (T/F), number of attempts grouped by challenge and user

    Returns a dict with a tuple of (challenge_id, user_id) as key and
    the submission dict as value """
    MONGO_DB = settings.MONGO_CLIENT['challenges']
    mongo_submissions = MONGO_DB['submissions'].aggregate([
        { "$sort": {"submitted":-1, "challenge_id": 1, "user_id": 1} },
        { "$group": {
                "_id" : "$challenge_id",
                "submitted": {"$last": "$submitted" },
                "user_id": {"$first": "$user_id" },
                "passed": {"$first": "$passed" },
                "attempts": {"$sum": 1}
            }
        }
    ])
    return {(str(submission['_id']), submission['user_id']): submission
            for submission in mongo_submissions}


def get_all_published_blocks():
    """ Queries the mongo database for all published blocks and returns the
    results as a list of dicts"""
    query = [
        {
            "$project": {
                "root_definition_id": "$versions.published-branch",
                "course_id": {
                    "$concat": [
                        "$org",
                        "+",
                        "$course",
                        "+",
                        "$run"
                    ]
                }
            }
        },
        {
            "$lookup": {
                "from": "modulestore.structures",
                "localField": "root_definition_id",
                "foreignField": "_id",
                "as": "structures"
            }
        },
        {
            "$project": {
                "blocks": "$structures.blocks",
                "course_id": 1
            }
        },
        {
            "$unwind": "$blocks"
        },
        {
            "$project": {
                "blocks.block_id": 1,
                "blocks.block_type": 1,
                "blocks.definition": 1,
                "blocks.fields": 1,
                "course_id": 1,
            }
        },
        {
            "$unwind": "$blocks"
        },
        {
            "$lookup": {
                "from": "modulestore.definitions",
                "localField": "blocks.definition",
                "foreignField": "_id",
                "as": "definition_content",
            }
        },
        {
            "$group": {
                "_id": "$course_id",
                "course_id": {"$first": "$course_id"},
                "blocks": {
                    "$push": {
                        "block_id": "$blocks.block_id",
                        "block_type": "$blocks.block_type",
                        "fields": "$blocks.fields",
                        "definition_content": "$definition_content.fields.data"
                    }
                }
            }
        }
    ]
    db = settings.MONGO_DB['modulestore.active_versions']
    all_blocks = db.aggregate(query)
    return [block for block in all_blocks]


def extract_all_challenges_from_blocks(programme):
    """ Retrieves all blocks, filters out any that are not a problem or if
    the content does not include a challenge_id (extracted based on regex)

    Returns a dict with course code, challenge_id and combination between
    course identifier and level of challenge (e.g. required) """
    course_codes = [course_code.key
                    for course_code in programme.course_codes.all()]
    all_blocks = get_all_published_blocks()
    problems = {}

    for course in all_blocks:
        if course.get('course_id') not in course_codes:
            continue

        for block in course.get('blocks'):
            if block.get('block_type') != 'problem':
                continue

            definition_content = block.get('definition_content')
            content = definition_content[0] if definition_content else ''
            matches = re.findall(CHALLENGE_PATTERN, content) if content else []
            challenge_id = matches[0] if matches else None

            if not challenge_id:
                continue

            course_id = course.get('course_id')
            module = course_id.split('+')[1].lower()
            # We only have required challenges at the moment
            module_level = "_".join((module, 'required')).lower()
            problems[challenge_id] = module_level

    return problems


def aggregate_challenge_results_per_student(enrolled_students,
                                            programme_challenges,
                                            all_submissions):
    """ Iterates through all students and challenges for a specific programme
    and increments the data points we track

    unattempted = incremented if no submission found
    attempted = incremented if a challenge submission found, but not passed
    passed = incremented if a challenge submission found and passed
    num_attempts = incremented if a challege is attempted or passed

    Returns the a dict with the results for all students in a programme """
    default_challenges = {
        module_level: deepcopy(DEFAULT_CHALLENGE)
        for module_level in
        set(programme_challenges.values())
    }
    challenge_results = {}

    for student_id, student_email in enrolled_students.items():
        student_challenges = deepcopy(default_challenges)

        for challenge_id, module_level in programme_challenges.items():
            submission = all_submissions.get((challenge_id,  student_id))

            if not submission:
                student_challenges[module_level]['unattempted'] += 1
            else:
                student_challenges[module_level][
                    'num_attempts'] += submission['attempts']
                if submission.get('passed'):
                    student_challenges[module_level]['passed'] += 1
                else:
                    student_challenges[module_level]['attempted'] += 1

        challenge_results[student_email] = {
            module_level: json.dumps(challenge_data)
            for module_level, challenge_data in student_challenges.items()
        }

        # TODO: Add skill tag calculation back in (currently not used in AMOS)
        challenge_results[student_email]['student_skills'] = json.dumps(
            DEFAULT_SKILL)

    return challenge_results


def extract_challenges_for_programme_from_mongodb(programme):
    """ Extract aggregated challenge data for all enrolled students in a
    specified programme

    Challenges are based on the currently published challenges in the CMS

    Returns the a dict with the results for all students in a programme """
    enrolled_students = {student.id: student.email
                         for student in programme.enrolled_students.all()}
    programme_challenges = extract_all_challenges_from_blocks(programme)
    all_submissions = extract_challenge_submissions()

    return aggregate_challenge_results_per_student(
        enrolled_students, programme_challenges, all_submissions)
