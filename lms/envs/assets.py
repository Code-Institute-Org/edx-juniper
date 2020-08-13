"""
Bare minimum settings for collecting production assets.
"""
from .common import *
from openedx.core.lib.derived import derive_settings

COMPREHENSIVE_THEME_DIRS.append('/openedx/themes')
STATIC_ROOT_BASE = '/openedx/staticfiles'

SECRET_KEY = 'secret'
XQUEUE_INTERFACE = {
    'django_auth': None,
    'url': None,
}
DATABASES = {
    "default": {},
}

STATIC_ROOT = path(STATIC_ROOT_BASE)
WEBPACK_LOADER['DEFAULT']['STATS_FILE'] = STATIC_ROOT / "webpack-stats.json"

derive_settings(__name__)

LOCALE_PATHS.append("/openedx/locale/contrib/locale")
LOCALE_PATHS.append("/openedx/locale/user/locale")

# Adding debug toolbar here because I want the debug toolbar static assets
# for local debugging, when DEBUG=True
INSTALLED_APPS += ['debug_toolbar', 'debug_toolbar_mongo']
MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')

ZOHO_CLIENT_ID = None
ZOHO_CLIENT_SECRET = None
ZOHO_REFRESH_TOKEN = None
ZOHO_REFRESH_ENDPOINT = None
ZOHO_STUDENTS_ENDPOINT = None
ZOHO_MENTORS_ENDPOINT = None
ZAPIER_STUDENT_CARE_EMAIL_ENDPOINT = None

RDS_DB_USER = None
RDS_DB_PASS = None
RDS_DB_ENDPOINT = None
RDS_DB_PORT = None
RDS_LMS_DB = None

LMS_SYLLABUS = None
BREADCRUMB_INDEX_URL = None
