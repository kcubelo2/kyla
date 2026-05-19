from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import User, StudentProfile, TeacherProfile

def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing.html')

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('landing')

def register_view(request):
    if request.method == 'POST':
        # Simple custom registration logic for demo
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role') # 'teacher' or 'student'
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('register')
            
        user = User.objects.create_user(username=username, email=email, password=password)
        
        if role == 'teacher':
            user.is_teacher = True
            user.save()
            TeacherProfile.objects.create(user=user)
        else:
            user.is_student = True
            user.save()
            StudentProfile.objects.create(user=user)
            
            # Create Enrollment Application
            from enrollment.models import EnrollmentApplication, EnrollmentDocument
            
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            date_of_birth = request.POST.get('date_of_birth')
            gender = request.POST.get('gender')
            address = request.POST.get('address')
            contact_number = request.POST.get('contact_number')
            grade_level = request.POST.get('grade_level')
            previous_school = request.POST.get('previous_school', '')

            app = EnrollmentApplication.objects.create(
                user=user,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=date_of_birth,
                gender=gender,
                address=address,
                contact_number=contact_number,
                email=email, # Using the registration email
                grade_level=grade_level,
                previous_school=previous_school
            )

            # Handle file uploads
            files = request.FILES.getlist('credentials')
            for f in files:
                EnrollmentDocument.objects.create(
                    application=app,
                    file=f,
                    document_type="Credential"
                )
            
        login(request, user)
        return redirect('dashboard')
        
    return render(request, 'register.html')

def dashboard_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
        
    if request.user.is_teacher:
        return redirect('teacher_dashboard')
    elif request.user.is_student:
        from enrollment.models import EnrollmentApplication
        app = EnrollmentApplication.objects.filter(user=request.user).first()
        if app and app.status != 'approved':
            return redirect('enrollment_status')
        return redirect('student_dashboard')
    else:
        return redirect('landing')

@login_required
def student_profile_view(request):
    """Show and update the student's profile page."""
    if not request.user.is_student:
        return redirect('dashboard')

    profile, _ = StudentProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        photo = request.FILES.get('profile_photo')
        if photo:
            # Delete old photo to avoid orphan files
            if profile.profile_photo:
                try:
                    import os
                    if os.path.isfile(profile.profile_photo.path):
                        os.remove(profile.profile_photo.path)
                except Exception:
                    pass
            profile.profile_photo = photo
            profile.save()
            messages.success(request, 'Profile photo updated successfully!')
        else:
            messages.error(request, 'Please select a photo to upload.')
        return redirect('student_profile')

    from enrollment.models import EnrollmentApplication
    enrollment = EnrollmentApplication.objects.filter(user=request.user).first()

    return render(request, 'student_profile.html', {
        'profile': profile,
        'enrollment': enrollment,
    })
