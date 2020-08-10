from django.conf.urls import url

from .views import challenge_handler


urlpatterns = [
    url(r'^webhook', challenge_handler, name='challenge_handler'),
]
