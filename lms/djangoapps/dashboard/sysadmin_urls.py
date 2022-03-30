"""
Urls for sysadmin dashboard feature
"""


from django.conf.urls import url

from dashboard import sysadmin

urlpatterns = [
    url(r'^$', sysadmin.Users.as_view(), name="sysadmin"),
    url(r'^courses/?$', sysadmin.Courses.as_view(), name="sysadmin_courses"),
    url(r'^staffing/?$', sysadmin.Staffing.as_view(), name="sysadmin_staffing"),
    url(r'^student_enrollment/?$', sysadmin.Enrollment.as_view(), name="sysadmin_enrollment"),
    url(r'^student_unenrollment/?$', sysadmin.Unenrollment.as_view(), name="sysadmin_unenrollment"),
    url(r'^student_unenrollment/search/?$', sysadmin.search_by_email, name="unenrollment_search"),
    url(r'^fdcc/?$', sysadmin.FiveDay.as_view(), name="sysadmin_fdcc"),
    url(r'^gitlogs/?$', sysadmin.GitLogs.as_view(), name="gitlogs"),
    url(r'^gitlogs/(?P<course_id>.+)$', sysadmin.GitLogs.as_view(),
        name="gitlogs_detail"),
]
