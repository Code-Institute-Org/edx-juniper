
from .production import *

DATABASES = {
    'default': {
        'ATOMIC_REQUESTS': True,
        'CONN_MAX_AGE': 0,
        'ENGINE': 'django.db.backends.mysql',
        'HOST': '127.0.0.1',
        'NAME': 'edxapp',
        'OPTIONS': {},
        'PASSWORD': 'password',
        'PORT': '3306',
        'USER': 'root'
    },
}
#SOUTH_TESTS_MIGRATE = False

#INSTALLED_APPS.append('django_nose')

#TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

