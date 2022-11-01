from django.contrib import admin
from ci_program.models import ProgramCourseCode, CourseCode, Program


class ProgramAdmin(admin.ModelAdmin):
    list_display = (
        "program_code",
        "status",
        "name",
    )

    ordering = ("-status",)

admin.site.register(ProgramCourseCode)
admin.site.register(CourseCode)
admin.site.register(Program, ProgramAdmin)
