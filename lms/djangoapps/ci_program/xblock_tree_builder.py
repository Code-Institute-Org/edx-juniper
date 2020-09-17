
class XBlockTreeBuilder(object):
    def __init__(self, courses, user):
        self.courses = courses
        self.user = user

    def create_program_course_tree(self):
        ''' Return Program tree (Course->Section->Unit)

            Given a list of courses, each contains a list of xblocks
            Each xblock list is unordered, but has one root block of type
            'course'
            Each xblock contains a list of block_ids in fields.children which
            refer to other xblocks in the same list
         '''

        root_courses = {}
        for course in self.courses:
            # There should always be a single root level 'course' block or the
            # data is corrupt
            root_course = next(
                c for c in course['blocks'] if c['block_type'] == 'course')
            children = root_course.get('fields', {}).get('children', [])
            sections = self.collect_sections(course, children)

            root_course['sections'] = sections
            root_courses[course['course_id']] = root_course
        return root_courses

    def is_xblock_visible_to_user(self, xblock):
        return self.user.is_staff or not xblock.get('fields', {}).get(
            'visible_to_staff_only')

    def xblock_is_type(self, xblock, block_type, block_id):
        return (xblock['block_type'] == block_type and
                xblock['block_id'] == block_id)

    def collect_units(self, course, section_children):
        units = []
        for unit_block_type, unit_block_id in section_children:
            for unit in course['blocks']:
                if self.xblock_is_type(unit, unit_block_type, unit_block_id):
                    if self.is_xblock_visible_to_user(unit):
                        units.append(unit)
        return units

    def collect_sections(self, course, children):
        sections = []
        for block_type, block_id in children:
            for section in course['blocks']:
                if self.xblock_is_type(section, block_type, block_id):
                    section['units'] = []
                    if self.is_xblock_visible_to_user(section):
                        sections.append(section)
                        section['units'] = self.collect_units(
                            course,
                            section.get('fields', {}).get('children', []))
        return sections
