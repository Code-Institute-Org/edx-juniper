from opaque_keys.edx.keys import CourseKey
from xmodule.modulestore.django import modulestore


def get_children(parent):
    if not hasattr(parent, 'children'):
       return []
    else:
        return parent.children


def get_course(course_id):
    course_key = CourseKey.from_string(course_id)
    store = modulestore()
    return store.get_course(course_key, depth=2)


def get_sections(course, only_visible=True):
    store = modulestore()
    children = [store.get_item(child_usage_key) for child_usage_key in get_children(course)]
    if only_visible:
        return [c for c in children if not c.visible_to_staff_only and not c.hide_from_toc]

    return children

