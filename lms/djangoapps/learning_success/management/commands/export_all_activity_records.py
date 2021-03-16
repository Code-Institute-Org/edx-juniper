from ci_program.api import get_program_by_program_code
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from opaque_keys.edx.locator import CourseLocator
from xmodule.modulestore.django import modulestore
from lms.djangoapps.learning_success.management.commands.challenges_helper import extract_all_student_challenges
from lms.djangoapps.learning_success.management.commands.utils import get_students_programme_ids_and_lms_version
from ci_program.models import Program


from collections import Counter, defaultdict, OrderedDict
from datetime import datetime, timedelta
import json
import math
import pandas as pd
import pytz
import requests
from sqlalchemy import create_engine, types

KEYS = ['module','section','lesson']
utc=pytz.UTC

# Need to create an engine using sqlalchemy to be able to
# connect with pandas .to_sql
# Pandas natively only supports sqlite3
# '?charset=utf8' used to specify utf-8 encoding to avoid encoding errors
CONNECTION_STRING = 'mysql+mysqldb://%s:%s@%s:%s/%s%s' % (
    settings.RDS_DB_USER,
    settings.RDS_DB_PASS,
    settings.RDS_DB_ENDPOINT,
    settings.RDS_DB_PORT,
    settings.RDS_LMS_DB,
    '?charset=utf8')

LMS_ACTIVITY_TABLE = settings.LMS_ACTIVITY_TABLE
ROWS_PER_PACKET = 1000


def harvest_course_tree(tree, output_dict, prefix=()):
    """Recursively harvest the breadcrumbs for each component in a tree

    Populates output_dict
    """
    block_name = tree.display_name
    block_breadcrumbs = prefix + (tree.display_name,)
    block_id = tree.location.block_id

    output_dict[block_id] = block_breadcrumbs

    children = tree.get_children()
    for subtree in children:
        harvest_course_tree(subtree, output_dict, prefix=block_breadcrumbs)


def harvest_programme(programme):
    """Harvest the breadcrumbs from all components in the programme

    Returns a dictionary mapping block IDs to the matching breadcrumbs
    """
    all_blocks = {}
    for course_locator in programme.get_course_locators():
        course = modulestore().get_course(course_locator)
        harvest_course_tree(course, all_blocks)
    return all_blocks


def format_date(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def thirty_day_units(completion_timestamps):
    thirty_days_ago = timezone.now() - timedelta(days=30)
    return sum(date > thirty_days_ago for date in completion_timestamps)


def days_into_data(first_active, completion_timestamps):
    days_into_generator = (
        (date - first_active).days for date in completion_timestamps)
    return ','.join(map(str, sorted(days_into_generator)))


def format_module_field(module_name, suffix):
    # TODO: Rename module name once there is no student who can view it
    if 'Full Stack Frameworks' in module_name:
        return 'full_stack_frameworks_with_django' + suffix
    return module_name.lower().replace(' ', '_') + suffix


def completed_lessons_per_module(breadcrumb_dict):
    return Counter(format_module_field(breadcrumbs[0], '_lessons')
                   for breadcrumbs in breadcrumb_dict.keys())


def completed_units_per_module(breadcrumb_dict):
    return Counter(format_module_field(breadcrumbs[0], '_units')
                   for breadcrumbs in breadcrumb_dict.keys())


def lessons_days_into_per_module(first_active, breadcrumb_dict):
    # there's a bit of voodoo here, to split the breadcrumb_dict into separate
    # timestamp lists, one per module
    per_module_lessons_times = defaultdict(list)
    for tup, timestamp in breadcrumb_dict.items():
        module = tup[0]
        per_module_lessons_times[module].append(timestamp)
    return {format_module_field(module, '_days_into'):
            days_into_data(first_active, timestamps)
            for module, timestamps in per_module_lessons_times.items()}


def n_days_fractions(completed_fractions, days_ago=None):
    """Sum fractions completed for the n previous days

    Returns the sum of fractions as float
    """
    if days_ago is None:
        period_start = utc.localize(datetime.utcfromtimestamp(0))
    else:
        period_start = timezone.now() - timedelta(days=days_ago)
    return sum(
        item['lesson_fraction']
        for item in completed_fractions
        if item['time_completed'] > period_start)


def fractions_per_day(date_joined, completed_fractions):
        """Create a list of fractions completed for
        each day since the student started

        1) Create a dict where the keys are all the days in the student life
        2) Loop through all completed fractions for the student and
        calculate on which day in their lifecyle each fraction was completed
        3) Add each fraction to that day in their lifecyle

        Returns a comma separated string of fractions
        per day in the student lifecyle
        """
        days_since_joined = (timezone.now() - date_joined).days
        # Needs to be string, then cast to float for calculation
        # Then be converted back to string for join operation
        days = {str(day) : '0' for day in range(days_since_joined + 1)}
        for fraction in completed_fractions:
            days_in = str((fraction['time_completed'] - date_joined).days)
            days[days_in] = str(float(days[days_in])
                                + fraction['lesson_fraction'])
        return ','.join(OrderedDict(sorted(days.items())).values())


def fractions_per_module(fractions, completed_fractions, days_ago=14):
    """Separate and sum completed fractions into those in last n days
    and the rest

    Returns a dict with module and the completed sums
    """
    n_days_ago = timezone.now() - timedelta(days=days_ago)
    for module, fraction in completed_fractions.items():
        key = (
            format_module_field(module[0], '_fraction_within_%sd' % (days_ago))
            if fraction['time_completed'] > n_days_ago
            else format_module_field(module[0],
                                     '_fraction_before_%sd' % (days_ago)))

        if key in fractions:
            fractions[key] += fraction['lesson_fraction']
    return fractions


def create_fractions_dict(lessons, days_ago=14):
    """ Create data structure to store fractions for each module

    Returns dict with an entry for each module for fractions completed
    within the last n days and the rest
    """
    fractions = {format_module_field(
        lesson['module'],'_fraction_within_%sd' % (days_ago)) : 0
        for lesson in lessons.values()}
    fractions.update({format_module_field(
        lesson['module'],'_fraction_before_%sd' % (days_ago)) : 0
        for lesson in lessons.values()})
    return fractions


def get_fractions(lesson_fractions, completed_fractions, block_id, breadcrumbs,
                                                                modified_time):
    """Combine block fractions from API with the student's modified time
    of that block

    Returns result dict
    """
    lesson_fraction = 0
    module_fraction = 0
    cumulative_fraction = 0

    # Check if fractions for lesson exist, if not keep default 0
    if block_id in lesson_fractions:
        lesson = lesson_fractions[block_id]
        lesson_fraction = lesson['fractions']['lesson_fraction']
        module_fraction = lesson['fractions']['module_fraction']
        cumulative_fraction = lesson['fractions']['cumulative_fraction']

    completed_fractions[breadcrumbs] = {
        'time_completed' : modified_time,
        'lesson_fraction' : lesson_fraction,
        'module_fraction' : module_fraction,
        'cumulative_fraction' : cumulative_fraction}


def construct_student_data(student, programme, lesson_fractions,
        module_fractions, all_components, challenges):
    """ Returns a progress metadata dictionary for a single student

    Input is a pregenerated dictionary mapping block IDs in LMS to breadcrumbs,
    the lesson fractions, module fractions, the harvested programme tree and
    all student challenges
    """
    # A short name for the activities queryset
    student_activities = student.studentmodule_set.filter(
        course_id__in=programme.get_course_locators())

    student_challenges = challenges.get(student.email, {})

    # remember details of the first activity
    first_activity = student_activities.order_by('created').first()
    first_active = (
        first_activity.created if first_activity else student.date_joined)

    # We care about the lesson level (depth 3) and unit level (depth 4).
    # Dictionaries of breadcrumbs to timestamps of completion
    completed_lessons = {}
    completed_fractions = {}
    completed_units = {}
    all_fractions = create_fractions_dict(lesson_fractions)

    # Provide default values in cases where student hasn't started
    latest_unit_started = None
    latest_unit_breadcrumbs = (u'',) * 4
    for activity in student_activities.order_by('modified'):
        block_id = activity.module_state_key.block_id
        breadcrumbs = all_components.get(block_id)
        if breadcrumbs and len(breadcrumbs) == 3:  # lesson
            # for each lesson learned, store latest timestamp
            completed_lessons[breadcrumbs] = activity.modified

            # get timestamp and fractions for each breadcrumb
            get_fractions(lesson_fractions, completed_fractions, block_id,
                            breadcrumbs, activity.modified)

        if breadcrumbs and len(breadcrumbs) >= 4:  # unit or inner block
            unit_breadcrumbs = breadcrumbs[:4]
            # for each unit learned, store latest timestamp
            completed_units[unit_breadcrumbs] = activity.modified

            # remember details of the latest unit overall
            # we use 'created' (not 'modified') to ignore backward leaps
            # to old units; sadly, there's no way to ignore forward leaps
            latest_unit_started = activity.created
            latest_unit_breadcrumbs = unit_breadcrumbs


    completed_fractions_last14d = n_days_fractions(
            completed_fractions.values(), 14)
    student_dict = {
        'email': student.email,
        'date_joined': format_date(first_active),
        'last_login': format_date(student.last_login),
        'latest_unit_completion': format_date(latest_unit_started),
        'latest_module': str(latest_unit_breadcrumbs[0]),
        'latest_section': str(latest_unit_breadcrumbs[1]),
        'latest_lesson': str(latest_unit_breadcrumbs[2]),
        'latest_unit': str(latest_unit_breadcrumbs[3]),
        'units_in_30d': thirty_day_units(completed_units.values()),
        'days_into_data': days_into_data(
            first_active, completed_units.values()),
        'completed_fractions_14d' : completed_fractions_last14d,
        'completed_fractions_28d' : n_days_fractions(
            completed_fractions.values(), 28) - completed_fractions_last14d,
        'cumulative_completed_fractions' : n_days_fractions(
            completed_fractions.values()),
        'fractions_per_day': fractions_per_day(
            first_active, completed_fractions.values())
    }

    completed_fractions_per_module = fractions_per_module(all_fractions,
        completed_fractions)

    student_dict.update(completed_fractions_per_module)
    student_dict.update(completed_lessons_per_module(completed_lessons))
    student_dict.update(completed_units_per_module(completed_units))
    student_dict.update(
        lessons_days_into_per_module(first_active, completed_lessons))
    student_dict.update(student_challenges)

    return student_dict


def convert_student_data_to_dataframe(student_data, source_platform, pathway,
        zoho_data):
    """ Converts the student_data dict into a Dataframe which will be used
    to store and write the student data to the MySQL database 
    
    Another change is to store the student_data dict as JSON value into one
    of the DataFrame's column instead of converting the whole dict to a
    DataFrame in its entirety
    
    Returns the created DataFrame """
    crm_programme_ids = {student.get('Email'): student.get('Programme_ID')
                         for student in zoho_data}
    crm_lms_version = {
        student.get('Email'): format_lms_version(student.get('LMS_Version'))
            for student in zoho_data}
    formatted_student_data = [
        {'email': student_email,
         'partial_student_data': json.dumps(student, default=str)}
        for student_email, student in student_data.items()]

    df = pd.DataFrame(formatted_student_data)
    df['date'] = datetime.now()
    df['source_platform'] = source_platform
    df['pathway'] = pathway
    df['state'] = 'initial'
    df['current_programme'] = df['email'].map(crm_programme_ids)
    df['current_lms_version'] = df['email'].map(crm_lms_version)
    return df


def format_lms_version(lms_version):
    """ Converts the CRM LMS Version field to a more machine readable
    version """
    if lms_version == 'Upgrade to Juniper':
        return 'ginkgo'
    return lms_version.split(' ')[0].lower()


class Command(BaseCommand):
    help = 'Extract student data from the open-edX server for use in Strackr'

    def add_arguments(self, parser):
        parser.add_argument('source_platform', type=str)
        parser.add_argument('pathway', type=str)
        parser.add_argument('programme_ids', type=str, nargs='+')

    def handle(self, source_platform, pathway, programme_ids, **kwargs):
        """ POST the collected data to the api endpoint from the settings
            Arguments:
                source_platform: Platform import as, i.e. 'juniper' or 'ginkgo'
                programme_ids: Programme ids of programme to use 'disd'
            
        Example command: 
        docker-compose exec ci-lms python3 manage.py lms export_all_activity_records juniper fullstack disd diwad

        The table should have one entry per day per platform and programme
        per student.

        In order to be able to easily re-run the extract any given day
        without any further intervention we are deleting any existing
        entry first.

        With the use of one transaction for deletion and insertion we can
        make sure that one does not happen without the other as to not
        lose any information.
        """
        student_data = {}
        programme_components = {}
        programme_challenges = {}
        fullstack_programmes = Program.objects.filter(
            program_code__in=programme_ids)
        fullstack_programme_ids = {p.id for p in fullstack_programmes}

        breadcrumb_index_url = ('%s?format=amos_fractions' %
                                settings.BREADCRUMB_INDEX_URL)
        lesson_fractions = requests.get(breadcrumb_index_url).json()['LESSONS']
        module_fractions = {
            item['module'] : item['fractions']['module_fraction']
            for item in lesson_fractions.values()}

        for programme in fullstack_programmes:
            programme_components[programme.program_code] = harvest_programme(
                programme)
            programme_challenges[programme.program_code
                ] = extract_all_student_challenges(programme)

        fullstack_students = User.objects.filter(
            program__id__in=fullstack_programme_ids)

        for student in fullstack_students:
            student_data.setdefault(student.email, {})
            programmes = student.program_set.filter(
                id__in=fullstack_programme_ids)
            for programme in programmes:
                student_data[student.email][programme.program_code] = (
                    construct_student_data(
                        student, programme, lesson_fractions, module_fractions,
                        programme_components[programme.program_code],
                        programme_challenges[programme.program_code]))

        engine = create_engine(CONNECTION_STRING, echo=False)
        with engine.begin() as conn:
            conn.execute(
                ("DELETE FROM lms_records WHERE source_platform = %s "
                 "AND pathway = %s "
                 "AND DATE(date) = %s;"), (
                    source_platform, pathway,
                    datetime.now().strftime(r'%Y-%m-%d')))

            zoho_data = get_students_programme_ids_and_lms_version()
            df = convert_student_data_to_dataframe(student_data,
                                                   source_platform,
                                                   pathway,
                                                   zoho_data)
            df.to_sql(name=LMS_ACTIVITY_TABLE,
                      con=conn,
                      if_exists='append',
                      chunksize=1000,
                      index=False)
