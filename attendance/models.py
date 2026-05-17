from django.db import models
from django.conf import settings
from hub.models import Course

class AttendanceRecord(models.Model):
    STATUS_CHOICES = (
        ('present', 'Present'),
        ('absent', 'Absent'),
    )

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='attendance_records')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')
    notes = models.TextField(blank=True, help_text="Notes for late arrivals, absences, and behavior")

    class Meta:
        unique_together = ('course', 'student', 'date')

    def __str__(self):
        return f"{self.student.username} - {self.course.name} - {self.date} ({self.status})"
