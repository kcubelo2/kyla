from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, HttpResponseForbidden
from .models import Course, Announcement, LessonFile, Assignment, Submission, GradeReport
from accounts.models import StudentProfile
from enrollment.models import EnrollmentApplication
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
def student_profile(request):
    if not request.user.is_student:
        return redirect('teacher_dashboard')

    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    application = request.user.enrollment_applications.order_by('-created_at').first()

    if request.method == 'POST':
        photo = request.FILES.get('profile_photo')
        if photo:
            profile.profile_photo = photo
            profile.save()
            messages.success(request, 'Profile photo updated successfully.')
        else:
            messages.error(request, 'Please select a profile photo to upload.')
        return redirect('student_profile')

    return render(request, 'hub/student_profile.html', {
        'profile': profile,
        'application': application,
    })

@login_required
def create_course(request):
    if not request.user.is_teacher:
        return HttpResponseForbidden("Only teachers can create subjects.")
    if request.method == 'POST':
        name = request.POST.get('name')
        desc = request.POST.get('description', '')
        course = Course.objects.create(
            name=name, 
            description=desc, 
            teacher=request.user
        )
        messages.success(request, f"Subject '{course.name}' created! Class Code: {course.class_code}")
        return redirect('teacher_dashboard')
    
    return render(request, 'hub/create_course.html')

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
    prefill_code = request.GET.get('code', '')
    if request.method == 'POST':
        code = request.POST.get('code')
        try:
            course = Course.objects.get(class_code=code)
            if request.user in course.students.all():
                messages.info(request, f"You are already enrolled in {course.name}.")
                return redirect('student_dashboard')
            course.students.add(request.user)
            messages.success(request, f"Successfully joined {course.name}!")
            return redirect('student_dashboard')
        except Course.DoesNotExist:
            messages.error(request, "Invalid class code. Please check and try again.")
    return render(request, 'hub/join_course.html', {'prefill_code': prefill_code})

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
    
    # Show only one task per activity type (preferring the most recent/upper one)
    all_assignments = course.assignments.all().order_by('-created_at')
    assignments = []
    seen_types = set()
    for assign in all_assignments:
        if assign.activity_type not in seen_types:
            assignments.append(assign)
            seen_types.add(assign.activity_type)
    
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
    if not request.user.is_teacher:
        return HttpResponseForbidden("Only teachers can create announcements.")
    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        Announcement.objects.create(course=course, title=title, content=content)
        return redirect('course_detail', course_id=course.id)
    return render(request, 'hub/create_announcement.html', {'course': course})

@login_required
def create_assignment(request, course_id):
    if not request.user.is_teacher:
        return HttpResponseForbidden("Only teachers can create assignments.")
    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    if request.method == 'POST':
        title = request.POST.get('title')
        desc = request.POST.get('description')
        due_date = request.POST.get('due_date')
        activity_type = request.POST.get('activity_type', 'assignment')
        file = request.FILES.get('file')
        Assignment.objects.create(
            course=course, title=title, description=desc, 
            due_date=due_date, activity_type=activity_type, file=file
        )
        return redirect('course_detail', course_id=course.id)
    return render(request, 'hub/create_assignment.html', {'course': course})

@login_required
def upload_material(request, course_id):
    if not request.user.is_teacher:
        return HttpResponseForbidden("Only teachers can upload materials.")
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
        
    if assignment.is_overdue:
        messages.error(request, "The deadline for this assignment has passed.")
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
    
    from django.core.signing import Signer
    signer = Signer()
    preview_token = signer.sign(str(sub.id)).split(':')[1]
    
    if request.method == 'POST':
        score = request.POST.get('score')
        letter_grade = request.POST.get('letter_grade')
        feedback = request.POST.get('feedback')
        sub.score = score or None
        sub.letter_grade = letter_grade or ''
        sub.feedback = feedback
        sub.save()
        return redirect('course_detail', course_id=sub.assignment.course.id)
    return render(request, 'hub/grade_submission.html', {'submission': sub, 'preview_token': preview_token})

@login_required
def export_assignment_grades(request, assignment_id):
    import csv
    from django.http import HttpResponse
    assignment = get_object_or_404(Assignment, id=assignment_id)
    if request.user != assignment.course.teacher:
        return HttpResponseForbidden("Only the teacher can export grades.")
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="Grades_{assignment.title}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student Name', 'Username', 'Score', 'Max Score', 'Letter Grade', 'Status', 'Submitted At', 'Feedback'])
    
    # Get all students in the course
    enrolled_students = assignment.course.students.all().order_by('last_name', 'first_name')
    
    # Get all submissions for this assignment
    submissions = Submission.objects.filter(assignment=assignment).select_related('student')
    sub_dict = {sub.student_id: sub for sub in submissions}
    
    for student in enrolled_students:
        sub = sub_dict.get(student.id)
        if sub:
            status = 'Graded' if sub.score is not None else 'Submitted (Not Graded)'
            score_display = sub.score if sub.score is not None else ''
            letter_display = sub.letter_grade
            date_display = sub.submitted_at.strftime("%Y-%m-%d %H:%M") if sub.submitted_at else 'N/A'
            feedback_display = sub.feedback
        else:
            status = 'Not Submitted'
            score_display = ''
            letter_display = ''
            date_display = ''
            feedback_display = ''
            
        writer.writerow([
            student.get_full_name() or student.username,
            student.username,
            score_display,
            assignment.max_score,
            letter_display,
            status,
            date_display,
            feedback_display
        ])
    
    return response

@login_required
def download_submission_file(request, submission_id):
    """Allow student or teacher to download submission file"""
    sub = get_object_or_404(Submission, id=submission_id)
    
    is_student = sub.student == request.user
    is_teacher = sub.assignment.course.teacher == request.user
    
    if not (is_student or is_teacher):
        return HttpResponseForbidden("You don't have permission to download this file.")
    
    if not sub.file:
        return HttpResponseForbidden("No file attached to this submission.")
    
    response = FileResponse(sub.file.open('rb'), as_attachment=True)
    response['Content-Disposition'] = f'attachment; filename="{sub.file.name.split("/")[-1]}"'
    return response


from django.views.decorators.clickjacking import xframe_options_sameorigin

@xframe_options_sameorigin
def preview_submission_file(request, submission_id):
    """Serve the submission file inline so the browser can display it (no download prompt)."""
    import mimetypes
    from django.core.signing import Signer, BadSignature
    from django.shortcuts import redirect
    from django.conf import settings
    
    sub = get_object_or_404(Submission, id=submission_id)

    token = request.GET.get('token')
    if token:
        signer = Signer()
        try:
            signer.unsign(f"{submission_id}:{token}")
            has_access = True
        except BadSignature:
            has_access = False
    else:
        if not request.user.is_authenticated:
            return redirect(f"{settings.LOGIN_URL}?next={request.path}")
        
        is_student = sub.student == request.user
        is_teacher = sub.assignment.course.teacher == request.user
        has_access = is_student or is_teacher

    if not has_access:
        return HttpResponseForbidden("You don't have permission to view this file.")

    if not sub.file:
        return HttpResponseForbidden("No file attached to this submission.")

    file_name = sub.file.name.split('/')[-1]
    
    # Try rendering DOCX natively with mammoth
    if file_name.lower().endswith('.docx'):
        import mammoth
        try:
            with sub.file.open('rb') as docx_file:
                result = mammoth.convert_to_html(docx_file)
                html = result.value
                return render(request, 'hub/docx_preview.html', {'html_content': html})
        except Exception as e:
            # Fallback to standard file serving if conversion fails
            pass

    mime_type, _ = mimetypes.guess_type(file_name)
    if not mime_type:
        mime_type = 'application/octet-stream'

    response = FileResponse(sub.file.open('rb'), content_type=mime_type)
    # inline = display in browser, not download
    response['Content-Disposition'] = f'inline; filename="{file_name}"'
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
    all_tasks = Assignment.objects.filter(course__teacher=request.user).order_by('-created_at')
    
    # Show only one task per activity type per course
    seen = {}
    tasks = []
    for task in all_tasks:
        course_id = task.course_id
        if course_id not in seen:
            seen[course_id] = set()
        if task.activity_type not in seen[course_id]:
            tasks.append(task)
            seen[course_id].add(task.activity_type)
            
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

    report = GradeReport.objects.filter(
        student=student, teacher=request.user
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

    report, _ = GradeReport.objects.get_or_create(
        student=student,
        teacher=request.user,
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

    report = get_object_or_404(
        GradeReport,
        student=student,
        teacher=request.user
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
    all_tasks = Assignment.objects.filter(course__students=request.user).order_by('-created_at')
    
    # Show only one task per activity type per course
    seen = {}
    tasks = []
    for task in all_tasks:
        course_id = task.course_id
        if course_id not in seen:
            seen[course_id] = set()
        if task.activity_type not in seen[course_id]:
            tasks.append(task)
            seen[course_id].add(task.activity_type)
            
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
def forms_dashboard(request):
    if not request.user.is_teacher:
        return redirect('dashboard')

    from .models import SchoolFormContent
    teacher_forms = {form.form_type: form for form in SchoolFormContent.objects.filter(teacher=request.user)}
    forms_list = []
    processed_types = set()

    for code, label in SchoolFormContent.FORM_TYPES:
        form_content = teacher_forms.get(code)
        processed_types.add(code)
        forms_list.append({
            'id': form_content.id if form_content else None,
            'type_code': code,
            'title': label,
            'description': form_content.title if form_content and form_content.title else label,
            'record': form_content,
            'has_file': bool(form_content and form_content.file),
            'file_name': form_content.file_name if form_content and form_content.file else '',
            'file_url': form_content.file.url if form_content and form_content.file else '',
        })

    for code, form_content in teacher_forms.items():
        if code not in processed_types:
            forms_list.append({
                'id': form_content.id,
                'type_code': code,
                'title': form_content.title or code,
                'description': form_content.content[:100] if form_content.content else "Custom Form",
                'record': form_content,
                'has_file': bool(form_content.file),
                'file_name': form_content.file_name,
                'file_url': form_content.file.url if form_content.file else '',
            })

    return render(request, 'hub/forms_dashboard.html', {'forms_list': forms_list})

@login_required
def create_custom_form(request):
    if not request.user.is_teacher:
        return redirect('dashboard')
    
    import uuid
    code = f"C_{uuid.uuid4().hex[:8]}"
    
    return redirect('edit_school_form', form_type=code)


@login_required
def download_school_form(request, form_id):
    from .models import SchoolFormContent
    form_content = get_object_or_404(SchoolFormContent, id=form_id)

    if request.user.is_teacher:
        if form_content.teacher != request.user:
            return HttpResponseForbidden("You don't have access to download this form.")
    elif request.user.is_student:
        if not Course.objects.filter(teacher=form_content.teacher, students=request.user).exists():
            return HttpResponseForbidden("You don't have access to download this form.")
    else:
        return HttpResponseForbidden("You don't have permission to download this file.")

    if not form_content.file:
        messages.error(request, "No file attached to this form yet.")
        return redirect('forms_dashboard' if request.user.is_teacher else 'student_forms')

    response = FileResponse(form_content.file.open('rb'), as_attachment=True, filename=form_content.file_name)
    return response

@login_required
def delete_school_form(request, form_id):
    if not request.user.is_teacher:
        return HttpResponseForbidden("Only teachers can delete forms.")

    from .models import SchoolFormContent
    form_content = get_object_or_404(SchoolFormContent, id=form_id, teacher=request.user)
    if request.method == 'POST':
        if form_content.file:
            form_content.file.delete(save=False)
        form_content.delete()
        messages.success(request, f"{form_content.get_form_type_display()} deleted successfully.")
        return redirect('forms_dashboard')

    return render(request, 'hub/delete_school_form.html', {'form_content': form_content})

@login_required
def bulk_invite(request, course_id):
    if not request.user.is_teacher:
        return HttpResponseForbidden("Only teachers can invite students.")
    course = get_object_or_404(Course, id=course_id, teacher=request.user)

    from accounts.models import User
    # All students registered in the system not already in this course
    enrolled_ids = course.students.values_list('id', flat=True)
    available_students = User.objects.filter(is_student=True).exclude(id__in=enrolled_ids).order_by('last_name', 'first_name')

    if request.method == 'POST':
        selected_ids = request.POST.getlist('student_ids')
        if selected_ids:
            students_to_add = User.objects.filter(id__in=selected_ids, is_student=True)
            course.students.add(*students_to_add)
            count = students_to_add.count()
            messages.success(request, f"Successfully added {count} student{'s' if count != 1 else ''} to {course.name}.")
        else:
            messages.error(request, "No students were selected.")
        return redirect('bulk_invite', course_id=course.id)

    return render(request, 'hub/bulk_invite.html', {
        'course': course,
        'available_students': available_students,
        'enrolled_students': course.students.all().order_by('last_name', 'first_name'),
    })


@login_required
def student_forms(request):
    if not request.user.is_student:
        return redirect('dashboard')

    from .models import SchoolFormContent
    teacher_ids = Course.objects.filter(students=request.user).values_list('teacher_id', flat=True).distinct()
    forms = SchoolFormContent.objects.filter(teacher_id__in=teacher_ids).order_by('form_type')
    return render(request, 'hub/student_forms.html', {'forms': forms})

@login_required
def edit_school_form(request, form_type):
    if not request.user.is_teacher:
        return redirect('dashboard')

    from .models import SchoolFormContent
    form_content, created = SchoolFormContent.objects.get_or_create(
        form_type=form_type,
        teacher=request.user,
        defaults={'title': form_type}
    )

    if request.method == 'POST':
        form_content.title = request.POST.get('title', form_content.title)
        form_content.content = request.POST.get('content', form_content.content)

        if request.FILES.get('file'):
            if form_content.file:
                form_content.file.delete(save=False)
            form_content.file = request.FILES['file']

        if request.POST.get('remove_file') == '1' and form_content.file:
            form_content.file.delete(save=False)
            form_content.file = None

        form_content.save()
        messages.success(request, f"{form_content.get_form_type_display()} saved successfully.")
        return redirect('forms_dashboard')

    return render(request, 'hub/edit_school_form.html', {
        'form_content': form_content,
        'form_type': form_type,
        'is_custom': form_type.startswith('C_') or form_type not in dict(SchoolFormContent.FORM_TYPES)
    })

