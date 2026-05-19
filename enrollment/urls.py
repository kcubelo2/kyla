from django.urls import path
from . import views

urlpatterns = [
    path('apply/', views.apply_enrollment, name='apply_enrollment'),
    path('status/', views.enrollment_status, name='enrollment_status'),
    path('manage/', views.manage_enrollments, name='manage_enrollments'),
]
