from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from .models import AttendanceRecord
from hub.models import Course
from hub.models import Submission
from django.db.models import Avg
import openpyxl
from datetime import date

@login_required
def mark_attendance(request, course_id):
    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    
    if request.method == 'POST':
        date_obj = date.today()
        
        for student in course.students.all():
            status = request.POST.get(f'status_{student.id}', 'present')
            
            AttendanceRecord.objects.update_or_create(
                course=course, student=student, date=date_obj,
                defaults={'status': status}
            )
            
        messages.success(request, f"Attendance marked for {date_obj}")
        return redirect('course_detail', course_id=course.id)
        
    students = course.students.all()
    today_date = date.today().strftime('%Y-%m-%d')
    return render(request, 'attendance/mark_attendance.html', {'course': course, 'students': students, 'today_date': today_date})

@login_required
def export_attendance_report(request, course_id):
    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    
    # Create an active Excel workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Attendance Report"
    
    # Headers
    headers = ["Student Name", "Date", "Status", "Notes", "Average Grade"]
    ws.append(headers)
    
    # Precompute average scores for each student in this course
    grade_data = Submission.objects.filter(
        assignment__course=course,
        score__isnull=False
    ).values('student').annotate(avg_score=Avg('score'))
    grade_map = {item['student']: item['avg_score'] for item in grade_data}
    
    records = AttendanceRecord.objects.filter(course=course).order_by('date', 'student__username')
    
    for record in records:
        avg_score = grade_map.get(record.student_id)
        grade_text = f"{avg_score:.2f}" if avg_score is not None else "N/A"
        ws.append([
            record.student.get_full_name() or record.student.username,
            str(record.date),
            record.get_status_display(),
            record.notes,
            grade_text
        ])
        
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="attendance_{course.name}.xlsx"'
    wb.save(response)
    
    return response
