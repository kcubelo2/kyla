from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    is_teacher = models.BooleanField(default=False)
    is_student = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        if not self.id:
            if not self.is_teacher and not self.is_student:
                # Default to student if neither is specified, or handle as needed
                self.is_student = True
        
        # Ensure exclusivity
        if self.is_teacher == True:
            self.is_student = False
            
        super().save(*args, **kwargs)

class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    department = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return f"Teacher: {self.user.get_full_name() or self.user.username}"

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    student_id = models.CharField(max_length=20, blank=True, null=True)
    overall_notes = models.TextField(blank=True, help_text="Notes for growth over a semester/year")
    
    def __str__(self):
        return f"Student: {self.user.get_full_name() or self.user.username}"
