from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from .models import EnrollmentApplication, EnrollmentDocument

@login_required
def apply_enrollment(request):
    if not request.user.is_student:
        return HttpResponseForbidden("Only students can apply for enrollment.")
        
    # Check if student already has a pending or approved application
    existing_app = EnrollmentApplication.objects.filter(user=request.user).first()
    if existing_app and existing_app.status in ['pending', 'approved']:
        messages.info(request, f"You already have an application with status: {existing_app.get_status_display()}")
        return redirect('enrollment_status')

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        date_of_birth = request.POST.get('date_of_birth')
        gender = request.POST.get('gender')
        address = request.POST.get('address')
        contact_number = request.POST.get('contact_number')
        email = request.POST.get('email')
        grade_level = request.POST.get('grade_level')
        previous_school = request.POST.get('previous_school', '')

        app = EnrollmentApplication.objects.create(
            user=request.user,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            gender=gender,
            address=address,
            contact_number=contact_number,
            email=email,
            grade_level=grade_level,
            previous_school=previous_school
        )

        # Handle file uploads
        files = request.FILES.getlist('credentials')
        for f in files:
            EnrollmentDocument.objects.create(
                application=app,
                file=f,
                document_type="Credential" # Generic for now
            )

        messages.success(request, "Enrollment application submitted successfully!")
        return redirect('enrollment_status')

    return render(request, 'enrollment/apply.html')

@login_required
def enrollment_status(request):
    if not request.user.is_student:
        return HttpResponseForbidden("Only students can view their enrollment status.")
        
    application = EnrollmentApplication.objects.filter(user=request.user).first()
    return render(request, 'enrollment/status.html', {'application': application})

@login_required
def manage_enrollments(request):
    if not request.user.is_teacher:
        return HttpResponseForbidden("Only teachers can manage enrollments.")
        
    applications = EnrollmentApplication.objects.all().order_by('-created_at')
    
    if request.method == 'POST':
        app_id = request.POST.get('app_id')
        new_status = request.POST.get('status')
        app = get_object_or_404(EnrollmentApplication, id=app_id)
        if new_status in ['approved', 'rejected']:
            app.status = new_status
            app.save()
            messages.success(request, f"Application for {app.first_name} {app.last_name} updated to {new_status}.")
        return redirect('manage_enrollments')
        
    return render(request, 'enrollment/manage.html', {'applications': applications})
