from django.conf.urls import url

from .views import show_programs

urlpatterns = [
    url(r'^(?P<program_name>[\w\-]+)', show_programs, name='show_programs'),
]
