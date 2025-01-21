from django.conf.urls import url

from .views import show_programs, show_program_bookmarks, set_bookmark_preference

urlpatterns = [
    url(r'^(?P<program_name>[\w\-]+)$', show_programs, name='show_programs'),
    url(r'^(?P<program_name>[\w\-]+)/bookmarks', show_program_bookmarks, name='show_program_bookmarks'),
    url(r'^(?P<program_name>[\w\-]+)/bookmark_preference', set_bookmark_preference, name='set_bookmark_preference'),
]
