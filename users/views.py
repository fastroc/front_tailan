from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.utils import timezone
from .models import CustomUser, UserProfile


def register_view(request):
    """User registration view."""
    if request.method == 'POST':
        # Handle registration logic here
        email = request.POST.get('email')
        username = request.POST.get('username')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        
        # Basic validation
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'users/register.html')
        
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return render(request, 'users/register.html')
            
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'users/register.html')
        
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name
        )
        
        # Create user profile
        UserProfile.objects.get_or_create(user=user)
        
        messages.success(request, 'Account created successfully! Please log in.')
        return redirect('users:login')
    
    return render(request, 'users/register.html')


def login_view(request):
    """User login view."""
    if request.method == 'POST':
        username = request.POST.get('username')  # Can be username or email
        password = request.POST.get('password')
        
        # Try authentication with username first
        user = authenticate(request, username=username, password=password)
        
        # If that fails, try with email
        if user is None:
            try:
                user_obj = CustomUser.objects.get(email=username)
                user = authenticate(request, username=user_obj.username, password=password)
            except CustomUser.DoesNotExist:
                pass
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            
            # Redirect to next page if specified, otherwise dashboard
            next_page = request.GET.get('next', '/')
            return redirect(next_page)
        else:
            messages.error(request, 'Invalid username/email or password.')
    
    return render(request, 'users/login.html')


@login_required
def profile_view(request):
    """User profile view with stats."""
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # Calculate some basic stats
    days_active = (timezone.now().date() - request.user.date_joined.date()).days
    
    if request.method == 'POST':
        # Handle profile update
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.email = request.POST.get('email', '')
        request.user.username = request.POST.get('username', '')
        request.user.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('users:profile')
    
    context = {
        'user': request.user,
        'profile': user_profile,
        'days_active': days_active,
        'companies_count': 0,  # Will be updated in Phase 2
    }
    return render(request, 'users/profile.html', context)


@login_required
def profile_edit_view(request):
    """Edit user profile view."""
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Update user info
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.email = request.POST.get('email', '')
        request.user.save()
        
        # Update profile info
        user_profile.phone = request.POST.get('phone', '')
        user_profile.bio = request.POST.get('bio', '')
        user_profile.address = request.POST.get('address', '')
        user_profile.city = request.POST.get('city', '')
        user_profile.country = request.POST.get('country', '')
        user_profile.postal_code = request.POST.get('postal_code', '')
        user_profile.website = request.POST.get('website', '')
        user_profile.company = request.POST.get('company', '')
        user_profile.job_title = request.POST.get('job_title', '')
        user_profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('users:profile')
    
    context = {
        'user': request.user,
        'profile': user_profile,
    }
    return render(request, 'users/profile_edit.html', context)


@login_required
def password_change_view(request):
    """Change user password."""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            messages.success(request, 'Your password has been changed successfully!')
            return redirect('users:profile')
        else:
            # Display form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field.title()}: {error}')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'users/password_change.html', {'form': form})


def logout_view(request):
    """User logout view."""
    user_name = request.user.first_name or request.user.username
    logout(request)
    messages.success(request, f'Goodbye {user_name}! You have been logged out successfully.')
    return redirect('users:login')
