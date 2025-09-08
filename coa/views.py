from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from .models import Account, TaxRate, AccountType


# @login_required
def chart_of_accounts_view(request):
    """Display chart of accounts."""
    
    # Get search and filter parameters
    search_query = request.GET.get('search', '')
    account_type_filter = request.GET.get('type', '')
    
    # Base queryset
    accounts = Account.objects.select_related('tax_rate', 'parent_account', 'created_by', 'updated_by').order_by('code')
    
    # Apply search filter
    if search_query:
        accounts = accounts.filter(
            Q(code__icontains=search_query) |
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Apply account type filter
    if account_type_filter:
        accounts = accounts.filter(account_type=account_type_filter)
    
    # Calculate totals
    from django.db.models import Sum
    # Calculate total for all asset types
    asset_types = ['CURRENT_ASSET', 'FIXED_ASSET', 'INVENTORY', 'NON_CURRENT_ASSET', 'PREPAYMENT']
    total_assets = accounts.filter(account_type__in=asset_types).aggregate(
        total=Sum('ytd_balance'))['total'] or 0
    
    # Get all tax rates for context
    tax_rates = TaxRate.objects.filter(is_active=True)
    
    context = {
        'accounts': accounts,
        'total_assets': total_assets,
        'tax_rates': tax_rates,
        'account_types': AccountType.choices,
        'search_query': search_query,
        'current_filter': account_type_filter,
    }
    
    return render(request, 'coa/chart_of_accounts_simple.html', context)


# @login_required
def account_detail_view(request, account_id):
    """Display account details."""
    account = get_object_or_404(Account, id=account_id)
    children = account.get_children()
    
    context = {
        'account': account,
        'children': children,
        'balance': account.ytd_balance,
    }
    return render(request, 'coa/account_detail.html', context)


# @login_required
def create_account_view(request):
    """Create new account."""
    if request.method == 'POST':
        code = request.POST.get('code')
        name = request.POST.get('name')
        account_type = request.POST.get('account_type')
        tax_rate_id = request.POST.get('tax_rate')
        description = request.POST.get('description', '')
        parent_account_id = request.POST.get('parent_account')
        
        try:
            tax_rate = TaxRate.objects.get(id=tax_rate_id)
            
            # Get parent account if provided
            parent_account = None
            if parent_account_id:
                parent_account = Account.objects.get(id=parent_account_id)
            
            account = Account.objects.create(
                code=code,
                name=name,
                account_type=account_type,
                tax_rate=tax_rate,
                description=description,
                ytd_balance=0.00,  # YTD balance will be populated programmatically later
                parent_account=parent_account,
                created_by=request.user,
                updated_by=request.user
            )
            
            messages.success(request, f'Account "{account.full_name}" created successfully!')
            return redirect('coa:chart_of_accounts')
            
        except TaxRate.DoesNotExist:
            messages.error(request, 'Invalid tax rate selected.')
        except Account.DoesNotExist:
            messages.error(request, 'Invalid parent account selected.')
        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
    
    tax_rates = TaxRate.objects.filter(is_active=True)
    parent_accounts = Account.objects.filter(is_active=True).order_by('code')
    
    context = {
        'tax_rates': tax_rates,
        'parent_accounts': parent_accounts,
        'account_types': AccountType.choices,
    }
    return render(request, 'coa/create_account_simple.html', context)


# @login_required
def account_search_api(request):
    """API endpoint for searching accounts."""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'accounts': []})
    
    accounts = Account.objects.filter(
        Q(name__icontains=query) | Q(code__icontains=query),
        is_active=True
    )[:10]  # Limit to 10 results
    
    accounts_data = []
    for account in accounts:
        accounts_data.append({
            'id': account.id,
            'name': account.name,
            'code': account.code,
            'account_type': account.account_type,
            'balance': str(account.ytd_balance),
            'tax_rate': account.tax_rate.name
        })
    
    return JsonResponse({'accounts': accounts_data})
