from django.conf.urls import url
from django.conf import settings

from .views import support, tutor, mentor, slack, troubleshooting, studentcare

urlpatterns = [
    url(r'^courses/{}/support$'.format(
        settings.COURSE_ID_PATTERN), support, name='support'),
    url(r'^courses/{}/tutor$'.format(
        settings.COURSE_ID_PATTERN), tutor, name='tutor'),
    url(r'^courses/{}/mentor$'.format(
        settings.COURSE_ID_PATTERN), mentor, name='mentor'),
    url(r'^courses/{}/slack$'.format(
        settings.COURSE_ID_PATTERN), slack, name='slack'),
    url(r'^courses/{}/troubleshooting$'.format(
        settings.COURSE_ID_PATTERN), troubleshooting, name='troubleshooting'),
    url(r'^courses/{}/studentcare$'.format(
        settings.COURSE_ID_PATTERN), studentcare, name='studentcare'),
]
