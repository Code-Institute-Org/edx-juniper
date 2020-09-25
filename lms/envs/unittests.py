
from .production import *


# Replacing edx middleware which doesn't work well with django unittests
index = MIDDLEWARE.index(
    'openedx.core.djangoapps.safe_sessions.middleware.SafeSessionMiddleware')
MIDDLEWARE.remove(
    'openedx.core.djangoapps.safe_sessions.middleware.SafeSessionMiddleware')
MIDDLEWARE.insert(index, 'django.contrib.sessions.middleware.SessionMiddleware')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}
