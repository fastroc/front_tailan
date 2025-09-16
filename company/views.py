from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
import json

from .models import Company, UserCompanyAccess, UserCompanyPreference
from .forms import SimpleCompanyForm, CompanySettingsForm


def create_essential_accounts(company):
    """Create essential accounts for a new company"""
    from coa.models import Account
    
    try:
        with transaction.atomic():
            # Create Cash Account
            Account.objects.get_or_create(
                company=company,
                code="1001",
                defaults={
                    'name': 'Cash',
                    'account_type': 'CURRENT_ASSET',
                    'description': 'Company cash and bank accounts',
                    'is_active': True
                }
            )
            
            # Create Income Account
            Account.objects.get_or_create(
                company=company,
                code="4001",
                defaults={
                    'name': 'Sales Revenue',
                    'account_type': 'REVENUE',
                    'description': 'Revenue from sales and services',
                    'is_active': True
                }
            )
            
            # Create Expense Account
            Account.objects.get_or_create(
                company=company,
                code="6001",
                defaults={
                    'name': 'General Expenses',
                    'account_type': 'EXPENSE',
                    'description': 'General business expenses',
                    'is_active': True
                }
            )
            
            # Mark accounts setup as complete
            from setup.models import CompanySetupStatus
            setup_status, created = CompanySetupStatus.objects.get_or_create(
                company=company
            )
            setup_status.accounts_complete = True
            setup_status.save()
            
            return True
            
    except Exception as e:
        # Log the error but don't fail company creation
        import logging
        logging.error(f"Error creating essential accounts for company {company.name}: {str(e)}")
        return False


@login_required
def company_list(request):
    """Display list of user's companies"""
    companies = Company.objects.filter(
        user_access__user=request.user,
        is_active=True  # Only show active companies
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
            
            # Automatically create essential accounts
            create_essential_accounts(company)
            
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
            
            messages.success(request, f'Company "{company.name}" created successfully with essential accounts!')
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
    
    # Get active company for comparison
    active_company = get_active_company(request)
    
    # Get all company users
    company_users = UserCompanyAccess.objects.filter(
        company=company
    ).select_related('user').order_by('-created_at')
    
    context = {
        'company': company,
        'user_access': user_access,
        'user_role': user_access.role,
        'active_company': active_company,
        'company_users': company_users,
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


@login_required
@require_POST
def company_delete(request, company_id):
    """Delete a company (only owner can delete)"""
    company = get_object_or_404(
        Company,
        id=company_id,
        user_access__user=request.user
    )
    
    # Check if user is owner
    user_access = UserCompanyAccess.objects.get(
        user=request.user,
        company=company
    )
    
    if user_access.role != 'owner':
        messages.error(request, 'Only company owners can delete companies.')
        return redirect('company:company_detail', company_id=company_id)
    
    # Check if this is the user's only company
    user_companies_count = Company.objects.filter(
        user_access__user=request.user,
        is_active=True
    ).count()
    
    if user_companies_count <= 1:
        messages.error(request, 'Cannot delete your only company. Create another company first.')
        return redirect('company:company_detail', company_id=company_id)
    
    company_name = company.name
    
    # If this is the active company, switch to another one
    active_company = get_active_company(request)
    if active_company and active_company.id == company.id:
        # Find another company to switch to
        other_company = Company.objects.filter(
            user_access__user=request.user,
            is_active=True
        ).exclude(id=company.id).first()
        
        if other_company:
            try:
                preferences = request.user.company_preference
                preferences.active_company = other_company
                preferences.save()
            except UserCompanyPreference.DoesNotExist:
                UserCompanyPreference.objects.create(
                    user=request.user,
                    active_company=other_company
                )
            request.session['active_company_id'] = other_company.id
    
    # Soft delete the company
    company.is_active = False
    company.save()
    
    messages.success(request, f'Company "{company_name}" has been deleted.')
    return redirect('company:company_list')
