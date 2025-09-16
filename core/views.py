from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

@login_required
def dashboard_view(request):
    """Professional Dashboard - Requires Authentication"""
    return render(request, 'dashboard.html', {
        'user': request.user,
        'current_period': 'January 2025',
    })

def reports_dashboard_view(request):
    """Reports Dashboard Showcase - REDIRECT TO MODULAR VERSION"""
    from django.shortcuts import redirect
    return redirect('/reports/dashboard/')

def test_404_view(request):
    """Test 404 Page"""
    return render(request, '404.html')

def test_500_view(request):
    """Test 500 Page"""  
    return render(request, '500.html')

def template_showcase(request):
    """Template Showcase - Show all templates"""
    return HttpResponse("""
    <h1>Professional Accounting Template Showcase</h1>
    <h2>Phase 1 Foundation Templates:</h2>
    <ul style="font-size: 16px; line-height: 2;">
        <li><a href="/dashboard/" target="_blank">📊 Professional Dashboard</a> - Main interface</li>
        <li><a href="/reports/" target="_blank">📈 Reports Dashboard</a> - Business intelligence</li>
        <li><a href="/test-404/" target="_blank">❌ 404 Error Page</a> - Page not found</li>  
        <li><a href="/test-500/" target="_blank">⚠️ 500 Error Page</a> - Server error</li>
    </ul>
    
    <h2>Design Features:</h2>
    <ul style="font-size: 14px; color: #666;">
        <li>✅ Professional Navy Blue & Gray Color Scheme</li>
        <li>✅ Clean Minimalistic Design</li>
        <li>✅ Responsive Bootstrap Layout</li>
        <li>✅ Professional Typography (Inter Font)</li>
        <li>✅ Enterprise-Level Navigation</li>
        <li>✅ Professional Accounting Module Structure</li>
    </ul>
    
    <p><strong>Next:</strong> <a href="/reconciliation/">Test Reconciliation Module</a> (when ready)</p>
    """)

def debug_context_view(request):
    """Debug Context Variables - No Login Required"""
    context = {
        'user_authenticated': request.user.is_authenticated,
        'user': request.user if request.user.is_authenticated else None,
    }
    
    if request.user.is_authenticated:
        # Import here to avoid circular imports
        from company.models import Company
        from company.views import get_active_company
        
        # Get context the same way the context processor does
        user_companies = Company.objects.filter(
            user_access__user=request.user,
            is_active=True
        ).distinct().order_by('name')
        
        active_company = get_active_company(request)
        
        context.update({
            'active_company': active_company,
            'user_companies': user_companies,
            'user_companies_list': list(user_companies.values('id', 'name')),
            'context_processor_test': True,
        })
    
    return render(request, 'debug_context.html', context)
