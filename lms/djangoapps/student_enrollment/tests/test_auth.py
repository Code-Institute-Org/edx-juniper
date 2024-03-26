import base64

from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from datetime import datetime
from oauth2_provider.models import Application

from opaque_keys.edx.locator import BlockUsageLocator, CourseLocator

from openedx.core.djangoapps.oauth_dispatch.tests.factories import ApplicationFactory, AccessTokenFactory
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.oauth_dispatch.jwt import create_jwt_for_user

from ci_program.models import Program, CourseCode, ProgramCourseCode


# ENROLL_ENDPOINT = 'http://127.0.0.1:8000/enrollment/enroll/'
ENROLLMENT_ENDPOINT = '/enrollment/enroll/'
ACCESS_TOKEN_ENDPOINT = '/oauth2/access_token/'

course_overview_data = {
    '_location': BlockUsageLocator(CourseLocator('CodeInstitute', 'HE101', '2020', None, None), 'course', 'course'),
    'advertised_start': None,
    'announcement': None,
    'catalog_visibility': 'both',
    'cert_html_view_enabled': True,
    'cert_name_long': '',
    'cert_name_short': '',
    'certificate_available_date': None,
    'certificates_display_behavior': 'end',
    'certificates_show_before_end': False,
    'course_image_url': '/asset-v1:CodeInstitute+HE101+2020+type@asset+block@images_course_image.jpg',
    'course_video_url': None,
    'created': datetime.now(),
    'days_early_for_beta': None,
    'display_name': 'HTML Essentials',
    'display_number_with_default': 'HE101',
    'display_org_with_default': 'CodeInstitute',
    'effort': None,
    'eligible_for_financial_aid': True,
    'end': None,
    'end_date': None,
    'end_of_course_survey_url': None,
    'enrollment_domain': None,
    'enrollment_end': None,
    'enrollment_start': None,
    'has_any_active_web_certificate': False,
    'id': CourseLocator('CodeInstitute', 'HE101', '2020', None, None),
    'invitation_only': False,
    'language': 'en',
    'lowest_passing_grade': 0.5,
    'marketing_url': None,
    'max_student_enrollments_allowed': None,
    'mobile_available': False,
    'modified': datetime.now(),
    'org': 'CodeInstitute',
    'self_paced': False,
    'short_description': '',
    'social_sharing_url': None,
    'start': datetime.now(),
    'start_date': datetime.now(),
    'version': 11,
    'visible_to_staff_only': False
}


class AuthTestCase(TestCase):
    """
    - make a call to oauth endpoint to get user's JWT token
    - make a call to enrollment endpoint with AUTHHEADER including JWT
    - make a call to enrollment endpoint without AUTHHEADER
    """
    def setUp(self):
        self.enrollment_user = User.objects.create_superuser(username='enrollment_user', email='enrollment@codeinstitute.net', password='arglebargle')
        self.oauth_client = ApplicationFactory.create()
        self.access_token = AccessTokenFactory.create(user=self.enrollment_user, application=self.oauth_client).token
        self.course_overview = CourseOverview.objects.create(**course_overview_data)
        self.program = Program.objects.create(name='Enrollment Test', program_code='t1')
        self.course_code = CourseCode.objects.create(key='CodeInstitute+HE101+2020', display_name='HTML Essentials')
        self.program_course_code = ProgramCourseCode.objects.create(program=self.program, course_code=self.course_code, position=1)
        with override_settings(JWT_EXPIRATION=300, OAUTH_ID_TOKEN_EXPIRATION=300):
            self.expected_jwt = create_jwt_for_user(self.enrollment_user)

    @classmethod
    def tearDownClass(cls):
        pass

    def tearDown(self):
        self.enrollment_user.delete()
        self.oauth_client.delete()
        self.course_overview.delete()
        self.program.delete()
        self.course_code.delete()
        self.program_course_code.delete()
    
    def test_enrollment_with_token(self):
        email = "bob@bob.com"
        headers = {
            "HTTP_AUTHORIZATION": "JWT {access_token}".format(access_token=self.expected_jwt)
        }
        resp = self.client.post(ENROLLMENT_ENDPOINT, data={
                "full_name": email, "email": email, "course_code": "t1"}, **headers)
        self.assertEqual(resp.status_code, 201)

    def test_enrollment_without_token(self):
        email = 'bob@bob.com'
        resp = self.client.post(ENROLLMENT_ENDPOINT, data={
                "full_name": email, "email": email, "course_code": "t1"})
        self.assertEqual(resp.status_code, 401)
        