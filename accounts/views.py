from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
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
            
        login(request, user)
        return redirect('dashboard')
        
    return render(request, 'register.html')

def dashboard_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
        
    if request.user.is_teacher:
        return redirect('teacher_dashboard')
    elif request.user.is_student:
        return redirect('student_dashboard')
    else:
        return redirect('landing')
