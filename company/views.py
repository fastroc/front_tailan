from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json

from .models import Company, UserCompanyAccess, UserCompanyPreference
from .forms import SimpleCompanyForm, CompanySettingsForm


@login_required
def company_list(request):
    """Display list of user's companies"""
    companies = Company.objects.filter(
        user_access__user=request.user
    ).distinct().order_by('-created_at')
    
    # Get active company
    active_company = get_active_company(request)
    
    context = {
        'companies': companies,
        'active_company': active_company,
        'title': 'My Companies',
    }
    return render(request, 'company/company_list.html', context)


@login_required
def company_create(request):
    """Simple company creation"""
    if request.method == 'POST':
        form = SimpleCompanyForm(request.POST, request.FILES)
        if form.is_valid():
            company = form.save(commit=False)
            company.owner = request.user
            company.save()
            
            # Give user owner access
            UserCompanyAccess.objects.create(
                user=request.user,
                company=company,
                role='owner'
            )
            
            # Set as active company if user doesn't have one
            try:
                preferences = request.user.company_preference
                if not preferences.active_company:
                    preferences.active_company = company
                    preferences.save()
            except UserCompanyPreference.DoesNotExist:
                UserCompanyPreference.objects.create(
                    user=request.user,
                    active_company=company
                )
            
            messages.success(request, f'Company "{company.name}" created successfully!')
            return redirect('company:company_list')
    else:
        form = SimpleCompanyForm()
    
    context = {
        'form': form,
        'title': 'Create Company',
        'page_title': 'Create New Company'
    }
    return render(request, 'company/company_create.html', context)


@login_required
def company_detail(request, company_id):
    """Company detail view"""
    company = get_object_or_404(
        Company,
        id=company_id,
        user_access__user=request.user
    )
    
    # Get user's access level
    user_access = UserCompanyAccess.objects.get(
        user=request.user,
        company=company
    )
    
    context = {
        'company': company,
        'user_access': user_access,
        'title': f'{company.name} - Details',
        'can_edit': user_access.role in ['owner', 'admin'],
    }
    return render(request, 'company/company_detail.html', context)


@login_required
def company_settings(request, company_id):
    """Company settings management"""
    company = get_object_or_404(
        Company,
        id=company_id,
        user_access__user=request.user
    )
    
    # Check permissions
    user_access = UserCompanyAccess.objects.get(
        user=request.user,
        company=company
    )
    
    if user_access.role not in ['owner', 'admin']:
        messages.error(request, 'You do not have permission to edit company settings.')
        return redirect('company:company_detail', company_id=company_id)
    
    if request.method == 'POST':
        form = CompanySettingsForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Company settings updated successfully!')
            return redirect('company:company_detail', company_id=company_id)
    else:
        form = CompanySettingsForm(instance=company)
    
    context = {
        'company': company,
        'form': form,
        'user_access': user_access,
        'title': f'{company.name} - Settings',
    }
    return render(request, 'company/company_settings.html', context)


@login_required
@require_POST
def company_switch(request):
    """Switch active company for the user"""
    try:
        data = json.loads(request.body)
        company_id = data.get('company_id')
        
        if not company_id:
            return JsonResponse({'error': 'Company ID required'}, status=400)
        
        # Verify user has access to this company
        try:
            company = Company.objects.get(
                id=company_id,
                user_access__user=request.user,
                is_active=True
            )
        except Company.DoesNotExist:
            return JsonResponse({'error': 'Company not found or access denied'}, status=404)
        
        # Update user's active company preference
        try:
            preferences = request.user.company_preference
            preferences.active_company = company
            preferences.save()
        except UserCompanyPreference.DoesNotExist:
            UserCompanyPreference.objects.create(
                user=request.user,
                active_company=company
            )
        
        # Store in session for immediate access
        request.session['active_company_id'] = company.id
        
        return JsonResponse({
            'success': True,
            'company': {
                'id': company.id,
                'name': company.name,
            },
            'message': f'Switched to {company.name}'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        # Log the error for debugging
        import logging
        logging.error(f"Company switch error: {str(e)}")
        return JsonResponse({'error': 'An error occurred while switching companies'}, status=500)


def get_active_company(request):
    """Utility function to get user's active company"""
    if not request.user.is_authenticated:
        return None
    
    # Try to get from session first
    company_id = request.session.get('active_company_id')
    if company_id:
        try:
            return Company.objects.get(
                id=company_id,
                user_access__user=request.user,
                is_active=True
            )
        except Company.DoesNotExist:
            # Clear invalid session data
            del request.session['active_company_id']
    
    # Fall back to user preferences
    try:
        preferences = request.user.company_preference
        if preferences.active_company and preferences.active_company.is_active:
            return preferences.active_company
    except UserCompanyPreference.DoesNotExist:
        pass
    
    # If no active company set, return the first available company
    first_company = Company.objects.filter(
        user_access__user=request.user,
        is_active=True
    ).first()
    
    if first_company:
        # Set as active company for future requests
        try:
            preferences = request.user.company_preference
            preferences.active_company = first_company
            preferences.save()
        except UserCompanyPreference.DoesNotExist:
            UserCompanyPreference.objects.create(
                user=request.user,
                active_company=first_company
            )
        
        request.session['active_company_id'] = first_company.id
        
    return first_company
