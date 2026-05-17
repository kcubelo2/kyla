from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, HttpResponseForbidden
from .models import Course, Announcement, LessonFile, Assignment, Submission, AcademicYear, GradeReport
from datetime import date

@login_required
def teacher_dashboard(request):
    if not request.user.is_teacher:
        return redirect('student_dashboard')
    courses = Course.objects.filter(teacher=request.user)
    return render(request, 'hub/teacher_dashboard.html', {'courses': courses})

@login_required
def student_dashboard(request):
    if not request.user.is_student:
        return redirect('teacher_dashboard')
    courses = list(Course.objects.filter(students=request.user))
    return render(request, 'hub/student_dashboard.html', {'courses': courses})

@login_required
def create_course(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        desc = request.POST.get('description', '')
        academic_year_id = request.POST.get('academic_year')
        
        academic_year = None
        if academic_year_id:
            academic_year = get_object_or_404(AcademicYear, id=academic_year_id)
        else:
            # Use current active year if none selected
            academic_year = AcademicYear.get_current_year()
        
        course = Course.objects.create(
            name=name, 
            description=desc, 
            teacher=request.user,
            academic_year=academic_year
        )
        messages.success(request, f"Subject '{course.name}' created! Class Code: {course.class_code}")
        return redirect('teacher_dashboard')
    
    academic_years = AcademicYear.objects.all().order_by('-start_date')
    current_year = AcademicYear.get_current_year()
    return render(request, 'hub/create_course.html', {
        'academic_years': academic_years,
        'current_year': current_year
    })

@login_required
def edit_course(request, course_id):
    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    if request.method == 'POST':
        course.name = request.POST.get('name')
        course.description = request.POST.get('description', '')
        course.save()
        messages.success(request, f"Subject '{course.name}' updated successfully.")
        return redirect('dashboard')
    return render(request, 'hub/edit_course.html', {'course': course})

@login_required
def delete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    if request.method == 'POST':
        course.delete()
        messages.success(request, f"Subject '{course.name}' deleted successfully.")
        return redirect('dashboard')
    return render(request, 'hub/delete_course.html', {'course': course})

@login_required
def join_course(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        try:
            course = Course.objects.get(class_code=code)
            course.students.add(request.user)
            messages.success(request, f"Successfully joined {course.name}")
            return redirect('student_dashboard')
        except Course.DoesNotExist:
            messages.error(request, "Invalid class code.")
    return render(request, 'hub/join_course.html')

@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    is_teacher = course.teacher == request.user
    
    # Ensure user has access
    if not is_teacher and request.user not in course.students.all():
        messages.error(request, "You don't have access to this course.")
        return redirect('dashboard')
        
    announcements = course.announcements.all().order_by('-created_at')
    materials = course.lesson_files.all().order_by('-uploaded_at')
    assignments = course.assignments.all().order_by('-created_at')
    
    # Get attendance records for this course
    from attendance.models import AttendanceRecord
    if is_teacher:
        # Teachers see all students' attendance for this course
        attendance_records = AttendanceRecord.objects.filter(course=course).order_by('-date')
    else:
        # Students see only their own attendance for this course
        attendance_records = AttendanceRecord.objects.filter(course=course, student=request.user).order_by('-date')
    
    submitted_assignment_ids = []
    submissions_dict = {}
    if not is_teacher:
        subs = Submission.objects.filter(student=request.user, assignment__course=course)
        submitted_assignment_ids = list(subs.values_list('assignment_id', flat=True))
        submissions_dict = {s.assignment_id: s for s in subs}
        
    for task in assignments:
        task.student_submission = submissions_dict.get(task.id)
    
    context = {
        'course': course, 'is_teacher': is_teacher,
        'announcements': announcements, 'materials': materials, 'assignments': assignments,
        'submitted_assignment_ids': submitted_assignment_ids, 'attendance_records': attendance_records
    }
    return render(request, 'hub/course_detail.html', context)

@login_required
def create_announcement(request, course_id):
    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        Announcement.objects.create(course=course, title=title, content=content)
        return redirect('course_detail', course_id=course.id)
    return render(request, 'hub/create_announcement.html', {'course': course})

@login_required
def create_assignment(request, course_id):
    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    if request.method == 'POST':
        title = request.POST.get('title')
        desc = request.POST.get('description')
        due_date = request.POST.get('due_date')
        activity_type = request.POST.get('activity_type', 'assignment')
        file = request.FILES.get('file')
        Assignment.objects.create(
            course=course, title=title, description=desc, 
            due_date=due_date, activity_type=activity_type, file=file,
            academic_year=course.academic_year
        )
        return redirect('course_detail', course_id=course.id)
    return render(request, 'hub/create_assignment.html', {'course': course})

@login_required
def upload_material(request, course_id):
    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    if request.method == 'POST':
        title = request.POST.get('title')
        file = request.FILES.get('file')
        LessonFile.objects.create(course=course, title=title, file=file)
        return redirect('course_detail', course_id=course.id)
    return render(request, 'hub/upload_material.html', {'course': course})

@login_required
def edit_assignment(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    if request.user != assignment.course.teacher:
        return redirect('dashboard')
    if request.method == 'POST':
        assignment.title = request.POST.get('title')
        assignment.description = request.POST.get('description')
        assignment.due_date = request.POST.get('due_date')
        assignment.activity_type = request.POST.get('activity_type')
        assignment.is_closed = request.POST.get('is_closed') == 'on'
        if request.FILES.get('file'):
            assignment.file = request.FILES.get('file')
        assignment.save()
        messages.success(request, "Task updated successfully.")
        return redirect('course_detail', course_id=assignment.course.id)
    return render(request, 'hub/edit_assignment.html', {'assignment': assignment})

@login_required
def submit_assignment(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    existing_submission = Submission.objects.filter(assignment=assignment, student=request.user).first()
    
    if assignment.is_closed:
        messages.error(request, "This task is closed.")
        return redirect('course_detail', course_id=assignment.course.id)
        
    if existing_submission and existing_submission.score is not None:
        messages.error(request, "This task has already been graded and cannot be edited.")
        return redirect('course_detail', course_id=assignment.course.id)

    if request.method == 'POST':
        content = request.POST.get('content', '')
        file = request.FILES.get('file')
        Submission.objects.update_or_create(
            assignment=assignment, student=request.user,
            defaults={'content': content}
        )
        sub = Submission.objects.get(assignment=assignment, student=request.user)
        if file:
            sub.file = file
            sub.save()
        messages.success(request, "Assignment submitted!")
        return redirect('course_detail', course_id=assignment.course.id)
    return render(request, 'hub/submit_assignment.html', {'assignment': assignment, 'submission': existing_submission})

@login_required
def grade_submission(request, submission_id):
    sub = get_object_or_404(Submission, id=submission_id)
    if request.user != sub.assignment.course.teacher:
        return redirect('dashboard')
    if request.method == 'POST':
        score = request.POST.get('score')
        letter_grade = request.POST.get('letter_grade')
        feedback = request.POST.get('feedback')
        sub.score = score or None
        sub.letter_grade = letter_grade or ''
        sub.feedback = feedback
        sub.save()
        return redirect('course_detail', course_id=sub.assignment.course.id)
    return render(request, 'hub/grade_submission.html', {'submission': sub})

@login_required
def download_submission_file(request, submission_id):
    """Allow student or teacher to download submission file"""
    sub = get_object_or_404(Submission, id=submission_id)
    
    # Check permissions: student must be the submitter, teacher must be the course teacher
    is_student = sub.student == request.user
    is_teacher = sub.assignment.course.teacher == request.user
    
    if not (is_student or is_teacher):
        return HttpResponseForbidden("You don't have permission to download this file.")
    
    if not sub.file:
        return HttpResponseForbidden("No file attached to this submission.")
    
    # Serve the file
    response = FileResponse(sub.file.open('rb'), as_attachment=True)
    response['Content-Disposition'] = f'attachment; filename="{sub.file.name.split("/")[-1]}"'
    return response

# --- GLOBAL VIEWS (SIDEBAR) --- #

@login_required
def course_scores(request, course_id):
    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    submissions = Submission.objects.filter(assignment__course=course).select_related('assignment', 'student').order_by('student__last_name', 'assignment__due_date')
    grade_choices = Submission.GRADE_CHOICES

    if request.method == 'POST':
        saved = 0
        for submission in submissions:
            score = request.POST.get(f'score_{submission.id}')
            letter_grade = request.POST.get(f'letter_grade_{submission.id}')
            feedback = request.POST.get(f'feedback_{submission.id}')

            if score == '':
                submission.score = None
            elif score is not None:
                try:
                    submission.score = int(score)
                except ValueError:
                    submission.score = None

            submission.letter_grade = letter_grade or ''
            submission.feedback = feedback or ''
            submission.save()
            saved += 1

        messages.success(request, f'{saved} grades updated successfully.')
        return redirect('course_scores', course_id=course.id)

    return render(request, 'hub/course_scores.html', {
        'course': course,
        'submissions': submissions,
        'grade_choices': grade_choices,
    })

@login_required
def teacher_tasks(request):
    if not request.user.is_teacher: return redirect('dashboard')
    tasks = Assignment.objects.filter(course__teacher=request.user).order_by('-created_at')
    courses = Course.objects.filter(teacher=request.user)
    return render(request, 'hub/teacher_tasks.html', {'tasks': tasks, 'courses': courses})

@login_required
def teacher_materials(request):
    if not request.user.is_teacher: return redirect('dashboard')
    materials = LessonFile.objects.filter(course__teacher=request.user).order_by('-uploaded_at')
    courses = Course.objects.filter(teacher=request.user)
    return render(request, 'hub/teacher_materials.html', {'materials': materials, 'courses': courses})

@login_required
def teacher_students(request):
    if not request.user.is_teacher: return redirect('dashboard')
    courses = Course.objects.filter(teacher=request.user).prefetch_related('students')
    return render(request, 'hub/teacher_students.html', {'courses': courses})

@login_required
def student_scores(request, student_id):
    if not request.user.is_teacher: return redirect('dashboard')
    from accounts.models import User
    student = get_object_or_404(User, id=student_id, is_student=True)
    # Check if student is actually in any of the teacher's courses to prevent snooping
    if not Course.objects.filter(teacher=request.user, students=student).exists():
        return redirect('teacher_students')
    submissions = Submission.objects.filter(
        student=student, 
        assignment__course__teacher=request.user
    ).select_related('assignment', 'assignment__course').order_by('-submitted_at')

    current_year = AcademicYear.get_current_year()
    report = GradeReport.objects.filter(
        student=student, teacher=request.user, academic_year=current_year
    ).first()
    
    return render(request, 'hub/student_scores.html', {
        'student_user': student, 
        'submissions': submissions,
        'report': report
    })

@login_required
def student_grade_report(request, student_id):
    if not request.user.is_teacher:
        return redirect('dashboard')
    from accounts.models import User
    student = get_object_or_404(User, id=student_id, is_student=True)

    if not Course.objects.filter(teacher=request.user, students=student).exists():
        return redirect('teacher_students')

    current_year = AcademicYear.get_current_year()
    report, _ = GradeReport.objects.get_or_create(
        student=student,
        teacher=request.user,
        academic_year=current_year,
        defaults={
            'display_name': student.get_full_name() or student.username,
        }
    )

    if request.method == 'POST':
        report.report_title = request.POST.get('report_title', report.report_title)
        report.display_name = request.POST.get('display_name', report.display_name)
        
        # Validate and set quarterly grades
        try:
            report.quarter_1 = request.POST.get('quarter_1') or None
            report.quarter_2 = request.POST.get('quarter_2') or None
            report.quarter_3 = request.POST.get('quarter_3') or None
            report.quarter_4 = request.POST.get('quarter_4') or None
            report.clean()  # Validate grade ranges
        except Exception as e:
            messages.error(request, f'Grade validation error: {str(e)}')
            return render(request, 'hub/student_grade_report.html', {
                'student_user': student,
                'report': report,
                'current_year': current_year,
                'teacher': request.user,
            })
        
        report.final_grade = request.POST.get('final_grade', report.final_grade)
        report.remarks = request.POST.get('remarks', report.remarks)
        if request.FILES.get('logo'):
            report.logo = request.FILES.get('logo')
        report.save()
        messages.success(request, 'Quarterly grade report saved. Review in Print Preview before finalizing.')
        return redirect('student_grade_report', student_id=student_id)

    return render(request, 'hub/student_grade_report.html', {
        'student_user': student,
        'report': report,
        'current_year': current_year,
        'teacher': request.user,
    })

@login_required
def print_grade_report(request, student_id):
    """
    Display a print-optimized view of the grade report.
    Allows final edits before printing.
    """
    if not request.user.is_teacher:
        return redirect('dashboard')
    from accounts.models import User
    student = get_object_or_404(User, id=student_id, is_student=True)

    if not Course.objects.filter(teacher=request.user, students=student).exists():
        return redirect('teacher_students')

    current_year = AcademicYear.get_current_year()
    report = get_object_or_404(
        GradeReport,
        student=student,
        teacher=request.user,
        academic_year=current_year
    )

    # Handle last-minute edits before printing
    if request.method == 'POST':
        # Update any fields from the print view
        report.final_grade = request.POST.get('final_grade', report.final_grade)
        report.remarks = request.POST.get('remarks', report.remarks)
        try:
            report.clean()  # Validate before saving
            report.save()
            messages.success(request, 'Grade report updated successfully.')
        except Exception as e:
            messages.error(request, f'Validation error: {str(e)}')
            return redirect('print_grade_report', student_id=student_id)

    # Calculate average grade if quarters are filled
    quarters = []
    if report.quarter_1:
        quarters.append(float(report.quarter_1))
    if report.quarter_2:
        quarters.append(float(report.quarter_2))
    if report.quarter_3:
        quarters.append(float(report.quarter_3))
    if report.quarter_4:
        quarters.append(float(report.quarter_4))
    
    average_grade = sum(quarters) / len(quarters) if quarters else None

    return render(request, 'hub/print_grade_report.html', {
        'student_user': student,
        'report': report,
        'current_year': current_year,
        'teacher': request.user,
        'average_grade': average_grade,
    })

@login_required
def teacher_announcements(request):
    if not request.user.is_teacher: return redirect('dashboard')
    announcements = Announcement.objects.filter(course__teacher=request.user).order_by('-created_at')
    courses = Course.objects.filter(teacher=request.user)
    return render(request, 'hub/teacher_announcements.html', {'announcements': announcements, 'courses': courses})

@login_required
def student_tasks(request):
    if not request.user.is_student: return redirect('dashboard')
    tasks = list(Assignment.objects.filter(course__students=request.user).order_by('-created_at'))
    submissions = {sub.assignment_id: sub for sub in Submission.objects.filter(student=request.user)}
    for task in tasks:
        task.student_submission = submissions.get(task.id)
    courses = Course.objects.filter(students=request.user)
    return render(request, 'hub/student_tasks.html', {'tasks': tasks, 'courses': courses})

@login_required
def student_materials(request):
    if not request.user.is_student: return redirect('dashboard')
    materials = LessonFile.objects.filter(course__students=request.user).order_by('-uploaded_at')
    courses = Course.objects.filter(students=request.user)
    return render(request, 'hub/student_materials.html', {'materials': materials, 'courses': courses})

@login_required
def student_announcements(request):
    if not request.user.is_student: return redirect('dashboard')
    announcements = Announcement.objects.filter(course__students=request.user).order_by('-created_at')
    courses = Course.objects.filter(students=request.user)
    return render(request, 'hub/student_announcements.html', {'announcements': announcements, 'courses': courses})

@login_required
def student_attendance_page(request):
    if not request.user.is_student: return redirect('dashboard')
    from attendance.models import AttendanceRecord
    records = AttendanceRecord.objects.filter(student=request.user).order_by('-date')
    courses = Course.objects.filter(students=request.user)
    return render(request, 'hub/student_attendance.html', {'records': records, 'courses': courses})

@login_required
def student_scores_view(request):
    if not request.user.is_student: return redirect('dashboard')
    submissions = Submission.objects.filter(
        student=request.user
    ).select_related('assignment', 'assignment__course').order_by('-submitted_at')
    
    return render(request, 'hub/student_scores_view.html', {
        'submissions': submissions
    })

@login_required
def manage_academic_years(request):
    if not request.user.is_teacher: return redirect('dashboard')
    academic_years = AcademicYear.objects.all().order_by('-start_date')
    current_year = AcademicYear.get_current_year()
    return render(request, 'hub/manage_academic_years.html', {
        'academic_years': academic_years,
        'current_year': current_year
    })

@login_required
def create_academic_year(request):
    if not request.user.is_teacher: return redirect('dashboard')
    if request.method == 'POST':
        name = request.POST.get('name')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        is_active = request.POST.get('is_active') == 'on'
        
        try:
            academic_year = AcademicYear.objects.create(
                name=name,
                start_date=start_date,
                end_date=end_date,
                is_active=is_active
            )
            messages.success(request, f"Academic year '{academic_year.name}' created successfully.")
            return redirect('manage_academic_years')
        except Exception as e:
            messages.error(request, f"Error creating academic year: {str(e)}")
    
    return render(request, 'hub/create_academic_year.html')

@login_required
def set_active_year(request, year_id):
    if not request.user.is_teacher: return redirect('dashboard')
    academic_year = get_object_or_404(AcademicYear, id=year_id)
    academic_year.is_active = True
    academic_year.save()
    messages.success(request, f"Academic year '{academic_year.name}' is now active.")
    return redirect('manage_academic_years')

@login_required
def delete_academic_year(request, year_id):
    if not request.user.is_teacher: return redirect('dashboard')
    academic_year = get_object_or_404(AcademicYear, id=year_id)
    
    # Prevent deletion if there are courses or assignments associated
    if academic_year.courses.exists() or academic_year.assignments.exists():
        messages.error(request, "Cannot delete academic year with associated courses or assignments.")
        return redirect('manage_academic_years')
    
    academic_year.delete()
    messages.success(request, f"Academic year '{academic_year.name}' deleted successfully.")
    return redirect('manage_academic_years')

@login_required
def forms_dashboard(request):
    if not request.user.is_teacher: return redirect('dashboard')
    
    forms_list = [
        {'id': 'SF1', 'title': 'School Register', 'description': 'Master list of class enrollment and profile'},
        {'id': 'SF2', 'title': 'Daily Attendance', 'description': 'Daily recording of learner attendance'},
        {'id': 'SF3', 'title': 'Books Issued', 'description': 'List of books and materials issued to learners'},
        {'id': 'SF4', 'title': 'Monthly Learner Movement', 'description': 'Summary of enrollment and learner movement'},
        {'id': 'SF5', 'title': 'Report on Promotion', 'description': 'List of promoted and retained learners'},
        {'id': 'SF6', 'title': 'Summarized Report on Promotion', 'description': 'Summary of SF5 data'},
        {'id': 'SF7', 'title': 'School Personnel Assignment', 'description': 'List of school personnel and teaching assignments'},
        {'id': 'SF8', 'title': 'Learner Basic Health Profile', 'description': 'Nutritional status and health profile of learners'},
    ]
    
    return render(request, 'hub/forms_dashboard.html', {'forms_list': forms_list})

@login_required
def edit_school_form(request, form_type):
    if not request.user.is_teacher: return redirect('dashboard')
    
    from .models import SchoolFormContent
    
    # Get current academic year
    current_year = AcademicYear.get_current_year()
    
    # Get or create the form content for this teacher, form type, and academic year
    form_content, created = SchoolFormContent.objects.get_or_create(
        form_type=form_type,
        teacher=request.user,
        academic_year=current_year,
        defaults={'title': f'{form_type} ({current_year.name if current_year else "No Year"})'}
    )
    
    if request.method == 'POST':
        form_content.title = request.POST.get('title', form_content.title)
        form_content.content = request.POST.get('content', '')
        form_content.save()
        messages.success(request, f"{form_content.get_form_type_display()} saved successfully.")
        return redirect('forms_dashboard')
        
    return render(request, 'hub/edit_school_form.html', {
        'form_content': form_content,
        'form_type': form_type
    })

