from ci_program.api import get_program_by_program_code
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from opaque_keys.edx.locator import CourseLocator
from xmodule.modulestore.django import modulestore
import pandas as pd
from sqlalchemy import create_engine, types

from collections import Counter, defaultdict
from datetime import datetime, timedelta
import json

import requests

LMS_TABLE = 'lms_breadcrumbs_v3'

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

BREADCRUMB_INDEX_URL = settings.LMS_SYLLABUS

# Keys are representing the internal edx terminology
# and the values are our CI terminology (also based on edx)
BLOCK_TYPES = {
    'course': 'module',
    'chapter': 'section',
    'sequential': 'lesson',
    'vertical': 'unit',
}

PROGRAM_CODE = 'FS'  # Our Full-Stack program


def get_safely(breadcrumbs, index):
    try:
        return breadcrumbs[index]
    except IndexError as e:
        return None


def harvest_course_tree(tree, output_list, prefix=()):
    """Recursively harvest the breadcrumbs for each component in a tree

    Populates output_dict
    """
    block_breadcrumbs = prefix + (tree.display_name,)

    block = {}
    block['block_id'] = tree.location.block_id
    block['block_name'] = tree.display_name
    block['block_type'] = BLOCK_TYPES.get(tree.category) or 'component'
    block['module'] = get_safely(block_breadcrumbs, 0)
    block['section'] = get_safely(block_breadcrumbs, 1)
    block['lesson'] = get_safely(block_breadcrumbs, 2)
    block['unit'] = get_safely(block_breadcrumbs, 3)
    block['breadcrumbs'] = ' - '.join(block_breadcrumbs)
    block['lms_category'] = tree.category

    output_list.append(block)

    children = tree.get_children()
    for subtree in children:
        harvest_course_tree(subtree, output_list, prefix=block_breadcrumbs)
    

def harvest_program(program):
    """Harvest the breadcrumbs from all components in the program

    Returns a list of dictionaries containing xblock meta data
    """
    all_blocks = []
    for course_locator in program.get_course_locators():
        course = modulestore().get_course(course_locator)
        harvest_course_tree(course, all_blocks)
    return all_blocks


def get_breadcrumb_index(URL):
    """Retrieve the course syllabus from Google Sheet with the ordering

    Returns a Dataframe to join to the rest of the breadcumbs
    """
    breadcrumb_index = requests.get(URL).json()
    df_breadcrumb_idx = pd.DataFrame(breadcrumb_index['LESSONS'])
    df_breadcrumb_idx = df_breadcrumb_idx.T
    df_breadcrumb_idx = df_breadcrumb_idx.reset_index()
    df_breadcrumb_idx.rename(columns={'index':'order_index'}, inplace=True)
    # TODO: remove following line, once the [beta] suffix is removed in the LMS
    df_breadcrumb_idx['module'] = df_breadcrumb_idx['module'].replace(
        'Careers', 'Careers [Beta]')
    df_breadcrumb_idx = df_breadcrumb_idx.reset_index()
    return df_breadcrumb_idx[['module','lesson','order_index','time_fraction']]


class Command(BaseCommand):
    help = 'Extract student data from the open-edX server for use in Strackr'

    def handle(self, *args, **options):

        program = get_program_by_program_code(PROGRAM_CODE)
        all_components = harvest_program(program)        
        df = pd.DataFrame(all_components)
        
        # Need to get lesson order from syllabus for ordering the modules
        # And course fractions
        df_breadcrumb_idx = get_breadcrumb_index(BREADCRUMB_INDEX_URL)
        df = df.merge(df_breadcrumb_idx, on=['module', 'lesson'], how='left')
        
        engine = create_engine(CONNECTION_STRING, echo=False)
        df.to_sql(name=LMS_TABLE, 
                  con=engine, 
                  if_exists='replace', 
                  dtype={'order_index': types.INT})
