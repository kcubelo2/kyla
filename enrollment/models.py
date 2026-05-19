from django.db import models
from django.conf import settings

class EnrollmentApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollment_applications')
    
    # Personal Details
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    address = models.TextField()
    
    # Contact Details
    contact_number = models.CharField(max_length=20)
    email = models.EmailField()
    
    # Academic Details
    grade_level = models.CharField(max_length=50)
    previous_school = models.CharField(max_length=200, blank=True)
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Enrollment for {self.first_name} {self.last_name} ({self.status})"

class EnrollmentDocument(models.Model):
    application = models.ForeignKey(EnrollmentApplication, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to='enrollment_docs/')
    document_type = models.CharField(max_length=100, help_text="e.g., Birth Certificate, Report Card")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document_type} for Application {self.application.id}"
