from django.db import models
from django.conf import settings
import uuid
import random
import string

def generate_class_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


class AcademicYear(models.Model):
    name = models.CharField(max_length=20, unique=True, help_text="e.g., 2024-2025")
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Ensure only one active academic year at a time
        if self.is_active:
            AcademicYear.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_current_year(cls):
        return cls.objects.filter(is_active=True).first() or cls.objects.order_by('-start_date').first()


class Course(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='taught_courses')
    students = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='enrolled_courses', blank=True)
    class_code = models.CharField(max_length=10, unique=True, default=generate_class_code)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='courses', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Announcement(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='announcements')
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.course.name}"

class LessonFile(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lesson_files')
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='lesson_files/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Assignment(models.Model):
    ACTIVITY_TYPES = [
        ('assignment', 'Assignment'),
        ('quiz', 'Quiz'),
        ('activity', 'Activity'),
    ]
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES, default='assignment')
    description = models.TextField()
    is_closed = models.BooleanField(default=False)
    file = models.FileField(upload_to='assignments/', blank=True, null=True)
    due_date = models.DateTimeField()
    max_score = models.IntegerField(default=100)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='assignments', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Submission(models.Model):
    GRADE_CHOICES = [
        ('A+', 'A+'), ('A', 'A'), ('A-', 'A-'),
        ('B+', 'B+'), ('B', 'B'), ('B-', 'B-'),
        ('C+', 'C+'), ('C', 'C'), ('C-', 'C-'),
        ('D', 'D'), ('F', 'F'),
    ]
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submissions')
    content = models.TextField(blank=True, help_text="Essay text or additional notes")
    file = models.FileField(upload_to='submissions/', blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    # Grading fields
    score = models.IntegerField(null=True, blank=True)
    letter_grade = models.CharField(max_length=2, choices=GRADE_CHOICES, blank=True)
    feedback = models.TextField(blank=True)

    class Meta:
        unique_together = ('assignment', 'student')

    def __str__(self):
        return f"Submission by {self.student.username} for {self.assignment.title}"

class GradeReport(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='grade_reports')
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_grade_reports')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='grade_reports', null=True, blank=True)
    report_title = models.CharField(max_length=200, default='Quarterly Grade Report')
    display_name = models.CharField(max_length=200, blank=True)
    quarter_1 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    quarter_2 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    quarter_3 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    quarter_4 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    final_grade = models.CharField(max_length=50, blank=True)
    remarks = models.TextField(blank=True)
    logo = models.ImageField(upload_to='grade_reports/logos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'teacher', 'academic_year')

    def __str__(self):
        student_name = self.student.get_full_name() or self.student.username
        return f"Grade report for {student_name} ({self.academic_year or 'No Year'})"
    
    def clean(self):
        """Validate grade values are within acceptable range (0-100)"""
        from django.core.exceptions import ValidationError
        errors = {}
        
        for quarter, value in [('quarter_1', self.quarter_1), ('quarter_2', self.quarter_2), 
                               ('quarter_3', self.quarter_3), ('quarter_4', self.quarter_4)]:
            if value is not None and (value < 0 or value > 100):
                errors[quarter] = f'{quarter.replace("_", " ").title()} grade must be between 0 and 100.'
        
        if errors:
            raise ValidationError(errors)

class Schedule(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.CharField(max_length=20)
    start_time = models.TimeField()
    end_time = models.TimeField()
    topic = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.course.name} - {self.day_of_week}"

class SchoolFormContent(models.Model):
    FORM_TYPES = [
        ('SF1', 'School Register'),
        ('SF2', 'Daily Attendance'),
        ('SF3', 'Books Issued'),
        ('SF4', 'Monthly Learner Movement'),
        ('SF5', 'Report on Promotion'),
        ('SF6', 'Summarized Report on Promotion'),
        ('SF7', 'School Personnel Assignment'),
        ('SF8', 'Learner Basic Health Profile'),
    ]
    form_type = models.CharField(max_length=3, choices=FORM_TYPES)
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField(help_text="Rich text content of the form")
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='school_forms')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('form_type', 'teacher', 'academic_year')

    def __str__(self):
        return f"{self.get_form_type_display()} - {self.teacher.username}"
