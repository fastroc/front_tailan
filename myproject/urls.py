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

def dashboard_view(request):
    """Simple dashboard."""
    from users.views import dashboard_view as user_dashboard
    return user_dashboard(request)

def home_view(request):
    """Smart home page that handles both authenticated and anonymous users"""
    return render(request, 'home.html')

def accounts_login_redirect(request):
    """Redirect /accounts/login/ to /users/login/"""
    return redirect('/users/login/')

def loan_schedule_prototype_view(request):
    """Independent loan scheduling showcase for prototyping"""
    return render(request, 'loan_schedule_prototype.html')

urlpatterns = [
    path('', welcome_view, name='welcome'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('home/', home_view, name='home'),  # Smart home page for backward compatibility
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path('company/', include('company.urls')),  # Multi-company management
    path('api/', include('api.urls')),
    path('coa/', include('coa.urls')),
    path('bank_accounts/', include('bank_accounts.urls')),
    path('reconciliation/', include('reconciliation.urls')),
    path('journal/', include('journal.urls')),
    path('assets/', include('assets.urls')),     # Fixed Assets management
    path('reports/', include('reports.urls')),     # New modular reports
    path('setup/', include('setup.urls')),
    path('conversion/', include('conversion.urls')),  # Conversion balances (opening balances)
    path('loans/', include('loans_core.urls')),  # Loan management core
    path('loans/customers/', include('loans_customers.urls')),  # Customer management
    path('loans/schedule/', include('loans_schedule.urls')),  # Payment scheduling
    path('loans/payments/', include('loans_payments.urls')),  # Payment processing
    path('loan-bridge/', include('loan_reconciliation_bridge.urls')),  # Loan reconciliation bridge
    # Fallback redirect for Django's default login URL
    path('accounts/login/', accounts_login_redirect),
    # Loan Schedule Prototype - Independent showcase
    path('loan-schedule-prototype/', loan_schedule_prototype_view, name='loan_schedule_prototype'),
    # Template testing routes - include the core URLs
    path('', include('core.urls')),  # This will make /dashboard/, /test-404/, etc. work directly
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Add debug toolbar URLs
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
