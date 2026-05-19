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
    
    # Student Profile
    path('profile/', account_views.student_profile_view, name='student_profile'),
    
    # App URLs
    path('hub/', include('hub.urls')),
    path('attendance/', include('attendance.urls')),
    path('enrollment/', include('enrollment.urls')),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
