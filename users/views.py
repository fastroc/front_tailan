from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from .forms import SimpleRegistrationForm, SimpleProfileForm
from .models import UserProfile


def get_client_ip(request):
    """Get client IP address."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@csrf_protect
def register_view(request):
    """Simple registration - create account and login immediately."""
    
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    context = {
        'title': 'Create Account',
        'page_title': 'Join Us Today'
    }
    
    if request.method == 'POST':
        form = SimpleRegistrationForm(request.POST)
        
        if form.is_valid():
            # Create user
            user = form.save()
            
            # Auto-login after registration (simple approach!)
            login(request, user)
            
            messages.success(request, f'Welcome, {user.get_full_name()}! Your account is ready.')
            return redirect('dashboard')
        
        else:
            messages.error(request, 'Please fix the errors below.')
    
    else:
        form = SimpleRegistrationForm()
    
    context['form'] = form
    return render(request, 'users/register.html', context)


@csrf_protect
def login_view(request):
    """Simple login view."""
    
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    context = {
        'title': 'Sign In',
        'page_title': 'Welcome Back',
        'next': request.GET.get('next', '/dashboard/')
    }
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            # Update login stats (optional - won't break if it fails)
            try:
                profile = user.userprofile
                profile.login_count += 1
                profile.last_login_ip = get_client_ip(request)
                profile.save()
            except Exception:
                pass  # Don't break login if profile update fails
            
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            
            # Redirect to next or dashboard
            next_url = request.POST.get('next') or request.GET.get('next') or '/dashboard/'
            return redirect(next_url)
        
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
    
    else:
        form = AuthenticationForm()
    
    context['form'] = form
    return render(request, 'users/login_working.html', context)


@login_required
def profile_view(request):
    """Simple profile view and editing."""
    
    context = {
        'title': 'My Profile',
        'page_title': 'User Profile'
    }
    
    # Ensure profile exists
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = SimpleProfileForm(request.POST, instance=request.user)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('users:profile')
        
        else:
            messages.error(request, 'Please correct the errors below.')
    
    else:
        form = SimpleProfileForm(instance=request.user)
    
    # Add user stats for template display
    context.update({
        'form': form,
        'profile': profile,
        'user_stats': {
            'login_count': profile.login_count,
            'member_since': request.user.date_joined,
            'last_login': request.user.last_login,
        },
        'user_initials': profile.get_initials(),
    })
    
    return render(request, 'users/profile.html', context)


def logout_view(request):
    """Simple logout."""
    user_name = request.user.get_full_name() or request.user.username if request.user.is_authenticated else "User"
    
    logout(request)
    messages.success(request, f'Goodbye, {user_name}! You have been logged out.')
    return redirect('welcome')


# Helper view for testing
def welcome_view(request):
    """Welcome page for non-authenticated users."""
    return render(request, 'welcome.html', {
        'title': 'Welcome',
        'page_title': 'Accounting System'
    })


def dashboard_view(request):
    """Enhanced dashboard view with setup integration."""
    if not request.user.is_authenticated:
        return redirect('users:login')
    
    # Get setup status from middleware or calculate it
    setup_status = getattr(request, 'setup_status', None)
    if not setup_status:
        setup_status = get_user_setup_status(request)
    
    # Get active company for context
    from company.views import get_active_company
    active_company = get_active_company(request)
    
    # Determine dashboard state based on setup completion
    if not active_company:
        dashboard_state = 'no_company'
        main_message = "🏢 Let's start by creating your first company"
        action_url = '/company/create/'
        action_text = "Create Company"
    elif setup_status and setup_status.get('needs_setup', True):
        completion = setup_status.get('completion_percentage', 0)
        if completion == 0:
            dashboard_state = 'setup_start'
            main_message = f"🚀 Let's set up {active_company.name} to get started!"
        elif completion < 50:
            dashboard_state = 'setup_critical'
            main_message = f"⚙️ Please complete essential setup for {active_company.name}"
        elif completion < 100:
            dashboard_state = 'setup_optional'
            main_message = f"🎯 {active_company.name} is ready! Complete remaining setup when convenient."
        else:
            dashboard_state = 'setup_complete'
            main_message = f"✅ {active_company.name} is fully configured!"
            
        action_url = setup_status.get('setup_url', '/setup/')
        action_text = "Continue Setup" if completion < 100 else "Review Setup"
    else:
        dashboard_state = 'ready'
        main_message = f"Welcome back to {active_company.name}!"
        action_url = None
        action_text = None
    
    context = {
        'title': 'Dashboard',
        'page_title': f'Welcome, {request.user.get_full_name() or request.user.username}!',
        'active_company': active_company,
        'setup_status': setup_status,
        'dashboard_state': dashboard_state,
        'main_message': main_message,
        'action_url': action_url,
        'action_text': action_text,
    }
    
    return render(request, 'dashboard.html', context)


def get_user_setup_status(request):
    """Get user setup status when not available from middleware"""
    from setup.models import CompanySetupStatus
    from company.views import get_active_company
    
    if not request.user.is_authenticated:
        return None
    
    active_company = get_active_company(request)
    
    if not active_company:
        return {
            'has_company': False,
            'needs_setup': True,
            'completion_percentage': 0,
            'next_step': 'create_company',
            'setup_url': '/company/create/'
        }
    
    try:
        setup_status = CompanySetupStatus.objects.get(company=active_company)
        return {
            'has_company': True,
            'needs_setup': setup_status.completion_percentage < 100,
            'completion_percentage': setup_status.completion_percentage,
            'next_step': setup_status.next_step,
            'setup_url': '/setup/',
            'company': active_company
        }
    except CompanySetupStatus.DoesNotExist:
        return {
            'has_company': True,
            'needs_setup': True,
            'completion_percentage': 0,
            'next_step': 'company_info',
            'setup_url': '/setup/',
            'company': active_company
        }
