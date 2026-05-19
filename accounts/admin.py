from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, TeacherProfile, StudentProfile

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Roles', {'fields': ('is_teacher', 'is_student')}),
    )
    list_display = ('username', 'email', 'is_teacher', 'is_student', 'is_staff')
    list_filter = ('is_teacher', 'is_student', 'is_staff', 'is_superuser', 'is_active')

admin.site.register(User, CustomUserAdmin)

@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'department')
    search_fields = ('user__username', 'user__email', 'department')

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'student_id')
    search_fields = ('user__username', 'user__email', 'student_id')
