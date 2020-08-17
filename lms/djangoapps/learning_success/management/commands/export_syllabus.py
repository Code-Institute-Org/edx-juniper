"""Course outline extraction script, to be run from CMS
Example xblock_info:
{'actions': {'childAddable': True,
  'deletable': True,
  'draggable': True,
  'duplicable': True},
 'ancestor_has_staff_lock': False,
 'category': u'sequential',
 'child_info': {'category': 'vertical',
  'children': [{'actions': {'childAddable': True,
     'deletable': True,
     'draggable': True,
     'duplicable': True},
    'ancestor_has_staff_lock': False,
    'category': u'vertical',
    'course_graders': [u'Quiz'],
    'display_name': u'Welcome',
    'due': None,
    'due_date': u'',
    'edited_on': u'Feb 01, 2020 at 21:02 UTC',
    'explanatory_message': None,
    'format': None,
    'graded': False,
    'group_access': {},
    'has_changes': False,
    'has_children': True,
    'has_explicit_staff_lock': False,
    'has_partition_group_components': False,
    'id': u'block-v1:CodeInstitute+F101+2017_T1+type@vertical+block@af5543c095bb469e86778209cf8a3faf',
    'published': True,
    'published_on': u'Feb 01, 2020 at 21:02 UTC',
    'release_date': u'Jan 01, 2017 at 00:00 UTC',
    'released_to_students': True,
    'show_correctness': u'always',
    'staff_only_message': False,
    'start': '2017-01-01T00:00:00Z',
    'studio_url': u'/container/block-v1:CodeInstitute+F101+2017_T1+type@vertical+block@af5543c095bb469e86778209cf8a3faf',
    'user_partitions': [{'groups': [{'deleted': False,
        'id': 1,
        'name': u'Audit',
        'selected': False}],
      'id': 50,
      'name': u'Enrollment Track Groups',
      'scheme': 'enrollment_track'}],
    'visibility_state': 'live'}],
  'display_name': u'Unit'},
 'course_graders': [u'Quiz'],
 'display_name': u'Module Introduction',
 'due': None,
 'due_date': u'',
 'edited_on': u'Feb 01, 2020 at 21:02 UTC',
 'explanatory_message': None,
 'format': None,
 'graded': False,
 'group_access': {},
 'has_changes': False,
 'has_children': True,
 'has_explicit_staff_lock': False,
 'has_partition_group_components': False,
 'hide_after_due': False,
 'id': u'block-v1:CodeInstitute+F101+2017_T1+type@sequential+block@146f1d1ff57149438a481112879dee35',
 'published': True,
 'published_on': u'Jan 29, 2020 at 11:13 UTC',
 'release_date': u'Jan 01, 2017 at 00:00 UTC',
 'released_to_students': True,
 'show_correctness': u'always',
 'staff_only_message': False,
 'start': '2017-01-01T00:00:00Z',
 'studio_url': u'/course/course-v1:CodeInstitute+F101+2017_T1?show=block-v1%3ACo1112879dee35',F101%2B2017_T1%2Btype%40sequential%2Bblock%40146f1d1ff57149438a48 'user_partitions': [{'groups': [{'deleted': False,
     'id': 1,
     'name': u'Audit',
     'selected': False}],
   'id': 50,
   'name': u'Enrollment Track Groups',
   'scheme': 'enrollment_track'}],
 'visibility_state': 'live'}
 """
from ci_program.api import get_program_by_program_code
from cms.djangoapps.contentstore.views.item import create_xblock_info
from xmodule.modulestore.django import modulestore

import pandas as pd

FS = get_program_by_program_code('FS')
BLOCK_TYPE = {
    "0": "module",
    "1": "section",
    "2": "lesson",
    "3": "unit",
}

def get_course_structure(course_locator):
    course_module = modulestore().get_course(course_locator, depth=None)  # None means all

    include_children_predicate = lambda xblock: not xblock.category == 'vertical'
    return create_xblock_info(
        course_module, include_child_info=True, course_outline=False, is_concise=False,
        include_children_predicate=include_children_predicate) 


def print_tree(tree, level=0):
    print("{indentation} {name} ({visibility}, published: {published_on})".format(
        indentation=" "*level*4, name=tree['display_name'],
        visibility=(tree.get('visibility_state') or ''),
        published_on=(tree.get('published_on') or ''),
        ))
    if 'child_info' not in tree:
        return
    for child in tree['child_info']['children']:
        print_tree(child, level+1)


def extract_syllabus_tree(tree, output, level=0):
    print("{indentation} {name} ({visibility}, published: {published_on})".format(
        indentation=" "*level*4, name=tree['display_name'],
        visibility=(tree.get('visibility_state') or ''),
        published_on=(tree.get('published_on') or ''),
        ))
    module_name = ''
    if level == 0:
        module_name = tree.get('display_name') or ''
    output.append({
        "block_key": tree.get('id') or '',
        "block_id": tree.get('id').split('@')[2] or '',
        "indentation": level*4,
        "block_type": BLOCK_TYPE.get(str(level)),
        "name": tree.get('display_name') or '',
        "module_name": module_name, 
        "visibility": tree.get('visibility_state') or '',
        "published_on": tree.get('published_on') or '',
    })
    if 'child_info' not in tree:
        return
    for child in tree['child_info']['children']:
        extract_syllabus_tree(child, output, level+1)


class Command(BaseCommand):
    help = 'Deactivate existing enrollment and add a new course enrollment'

    def handle(self, *args, **options):
        syllabus_structure = []
        for course_locator in FS.get_course_locators():
            course_structure = get_course_structure(course_locator)
            extract_syllabus_tree(course_structure, syllabus_structure)
            #print_tree(course_structure)
        df = pd.DataFrame(syllabus_structure)
        df.to_csv("extracted_syllabus.csv", index=False)
