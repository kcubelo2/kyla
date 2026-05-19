from django.contrib import admin
from .models import Course, Section, Announcement, LessonFile, Assignment, Submission, GradeReport, Schedule, SchoolFormContent

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('grade_level', 'name')
    list_filter = ('grade_level',)
    search_fields = ('name',)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'section', 'teacher', 'class_code')
    list_filter = ('section', 'teacher')
    search_fields = ('name', 'class_code')

admin.site.register(Announcement)
admin.site.register(LessonFile)
admin.site.register(Assignment)
admin.site.register(Submission)
admin.site.register(GradeReport)
admin.site.register(Schedule)
admin.site.register(SchoolFormContent)
