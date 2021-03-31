from django.conf.urls import url

from .views import test_lrs

urlpatterns = [
    url(r'^$', test_lrs, name='test_lrs'),
]
