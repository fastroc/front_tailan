from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json

from .models import Company, UserCompanyRole, UserCompanyPreference
from .forms import CompanyCreateForm

def company_list(request):
    """
    Display list of companies - DEMO VERSION (No auth required)
    """
    # Mock data for template showcase
    context = {
        'companies': [],  # Empty for demo
        'active_company': None,
        'total_companies': 0,
    }
    return render(request, 'company/company_list.html', context)

@login_required
def company_create(request):
    """
    Company creation wizard
    """
    if request.method == 'POST':
        form = CompanyCreateForm(request.POST, request.FILES)
        if form.is_valid():
            company = form.save()
            
            # Create owner role for the user who created the company
            UserCompanyRole.objects.create(
                user=request.user,
                company=company,
                role='owner',
                can_edit_settings=True,
                can_manage_users=True,
                can_view_reports=True
            )
            
            # Set as user's active and default company if they don't have one
            preferences, created = UserCompanyPreference.objects.get_or_create(
                user=request.user
            )
            if not preferences.active_company:
                preferences.active_company = company
            if not preferences.default_company:
                preferences.default_company = company
            preferences.save()
            
            messages.success(request, f'Company "{company.name}" created successfully!')
            return redirect('company:company_list')
    else:
        form = CompanyCreateForm()
    
    return render(request, 'company/company_create.html', {'form': form})

@login_required
@require_POST
def company_switch(request):
    """
    Switch active company for the user
    """
    try:
        data = json.loads(request.body)
        company_id = data.get('company_id')
        
        if not company_id:
            return JsonResponse({'error': 'Company ID required'}, status=400)
        
        # Verify user has access to this company
        company = get_object_or_404(
            Company,
            id=company_id,
            user_roles__user=request.user,
            user_roles__is_active=True,
            is_active=True
        )
        
        # Update user's active company
        preferences, created = UserCompanyPreference.objects.get_or_create(
            user=request.user
        )
        preferences.active_company = company
        preferences.save()
        
        # Store in session for immediate access
        request.session['active_company_id'] = str(company.id)
        
        return JsonResponse({
            'success': True,
            'company': {
                'id': str(company.id),
                'name': company.name,
                'display_name': company.display_name
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def company_detail(request, company_id):
    """
    Company detail and settings page
    """
    company = get_object_or_404(
        Company,
        id=company_id,
        user_roles__user=request.user,
        user_roles__is_active=True
    )
    
    # Check if user can edit settings
    user_role = UserCompanyRole.objects.get(
        user=request.user,
        company=company
    )
    
    context = {
        'company': company,
        'user_role': user_role,
        'can_edit': user_role.can_edit_settings or user_role.role == 'owner',
    }
    return render(request, 'company/company_detail.html', context)

@login_required
def company_settings(request, company_id):
    """
    Company settings management
    """
    company = get_object_or_404(
        Company,
        id=company_id,
        user_roles__user=request.user,
        user_roles__is_active=True
    )
    
    # Check permissions
    user_role = UserCompanyRole.objects.get(
        user=request.user,
        company=company
    )
    
    if not (user_role.can_edit_settings or user_role.role == 'owner'):
        messages.error(request, 'You do not have permission to edit company settings.')
        return redirect('company:company_detail', company_id=company_id)
    
    if request.method == 'POST':
        form = CompanyCreateForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Company settings updated successfully!')
            return redirect('company:company_detail', company_id=company_id)
    else:
        form = CompanyCreateForm(instance=company)
    
    context = {
        'company': company,
        'form': form,
        'user_role': user_role,
    }
    return render(request, 'company/company_settings.html', context)

def get_active_company(request):
    """
    Utility function to get user's active company
    """
    if not request.user.is_authenticated:
        return None
    
    # Try to get from session first (for immediate access after switching)
    company_id = request.session.get('active_company_id')
    if company_id:
        try:
            return Company.objects.get(
                id=company_id,
                user_roles__user=request.user,
                user_roles__is_active=True,
                is_active=True
            )
        except Company.DoesNotExist:
            # Clear invalid session data
            del request.session['active_company_id']
    
    # Fall back to user preferences
    try:
        preferences = request.user.company_preferences
        if preferences.active_company:
            return preferences.active_company
    except UserCompanyPreference.DoesNotExist:
        pass
    
    # If no active company set, return the first available company
    user_companies = Company.objects.filter(
        user_roles__user=request.user,
        user_roles__is_active=True,
        is_active=True
    ).first()
    
    if user_companies:
        # Set as active company for future requests
        preferences, created = UserCompanyPreference.objects.get_or_create(
            user=request.user
        )
        preferences.active_company = user_companies
        preferences.save()
        request.session['active_company_id'] = str(user_companies.id)
        
    return user_companies
