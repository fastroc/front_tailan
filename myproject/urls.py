"""
URL configuration for myproject project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render, redirect

def welcome_view(request):
    """Welcome page for anonymous visitors"""
    return render(request, 'welcome.html')

def home_view(request):
    """Smart home page that handles both authenticated and anonymous users"""
    return render(request, 'home.html')

def accounts_login_redirect(request):
    """Redirect /accounts/login/ to /users/login/"""
    return redirect('/users/login/')

urlpatterns = [
    path('', welcome_view, name='welcome'),
    path('home/', home_view, name='home'),  # Smart home page for backward compatibility
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path('company/', include('company.urls')),  # Multi-company management
    path('api/', include('api.urls')),
    path('coa/', include('coa.urls')),
    path('reconciliation/', include('reconciliation.urls')),
    path('journal/', include('journal.urls')),
    path('assets/', include('assets.urls')),     # Fixed Assets management
    path('reports/', include('reports.urls')),     # New modular reports
    path('setup/', include('setup_urls')),
    # Fallback redirect for Django's default login URL
    path('accounts/login/', accounts_login_redirect),
    # Template testing routes - include the core URLs
    path('', include('core.urls')),  # This will make /dashboard/, /test-404/, etc. work directly
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
