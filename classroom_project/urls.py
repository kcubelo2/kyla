from django.contrib import admin
from django.urls import path, include
from accounts import views as account_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Open Landing page
    path('', account_views.landing, name='landing'),
    
    # Auth
    path('login/', account_views.login_view, name='login'),
    path('logout/', account_views.logout_view, name='logout'),
    path('register/', account_views.register_view, name='register'),
    
    # Dashboard dispatcher (Teacher or Student)
    path('dashboard/', account_views.dashboard_view, name='dashboard'),
    
    # App URLs
    path('hub/', include('hub.urls')),
    path('attendance/', include('attendance.urls')),
]
