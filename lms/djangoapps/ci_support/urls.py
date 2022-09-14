from django.conf.urls import url
from django.conf import settings

from .views import support, tutor, mentor, slack, troubleshooting, studentcare, careers

urlpatterns = [
    url(r'^(?P<program_slug>\w+)/support$', support, name='support'),
    url(r'^(?P<program_slug>\w+)/tutor$', tutor, name='tutor'),
    url(r'^(?P<program_slug>\w+)/mentor$', mentor, name='mentor'),
    url(r'^(?P<program_slug>\w+)/slack$', slack, name='slack'),
    url(r'^(?P<program_slug>\w+)/troubleshooting$', troubleshooting, name='troubleshooting'),
    url(r'^(?P<program_slug>\w+)/studentcare$', studentcare, name='studentcare'),
    url(r'^(?P<program_slug>\w+)/careers$', careers, name='careers'),
]
