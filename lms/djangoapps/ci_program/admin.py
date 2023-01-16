from django import forms
from django.contrib import admin
from ci_program.models import ProgramCourseCode, CourseCode, Program


class ProgramAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ProgramAdminForm, self).__init__(*args, **kwargs)
        self.fields['sample_content'].queryset = Program.objects.exclude(id=self.instance.id)
        self.fields['support_programs'].queryset = Program.objects.exclude(id=self.instance.id)


class ProgramAdmin(admin.ModelAdmin):
    form = ProgramAdminForm

    list_display = (
        "program_code",
        "status",
        "name",
    )

    ordering = ("-status",)

admin.site.register(ProgramCourseCode)
admin.site.register(CourseCode)
admin.site.register(Program, ProgramAdmin)
