from django.urls import path
from . import views

urlpatterns = [
    path('course/<int:course_id>/mark/', views.mark_attendance, name='mark_attendance'),
    path('course/<int:course_id>/report/', views.export_attendance_report, name='export_attendance_report'),
]
