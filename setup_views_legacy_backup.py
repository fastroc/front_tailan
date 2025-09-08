from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from datetime import datetime, timedelta
from django.views.decorators.http import require_http_methods
import json


@login_required
def financial_year_wizard(request):
    """Financial Year Setup Wizard - First step in account setup"""
    
    if request.method == 'POST':
        # Process financial year setup
        try:
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            fy_type = request.POST.get('fy_type', 'calendar')
            reporting_frequency = request.POST.get('reporting_frequency', 'monthly')
            
            # Validate dates
            if not start_date or not end_date:
                messages.error(request, 'Please select valid start and end dates.')
                return render(request, 'setup/financial_year_wizard.html')
            
            # Store in session for now (later we'll create proper models)
            request.session['financial_year_setup'] = {
                'start_date': start_date,
                'end_date': end_date,
                'type': fy_type,
                'reporting_frequency': reporting_frequency,
                'setup_date': datetime.now().isoformat(),
            }
            
            messages.success(request, 'Financial year setup completed successfully!')
            
            # Redirect to next step (Chart of Accounts)
            return redirect('coa:chart_of_accounts')
            
        except Exception as e:
            messages.error(request, f'Error setting up financial year: {str(e)}')
    
    # Default context for GET request
    context = {
        'current_year': datetime.now().year,
        'next_year': datetime.now().year + 1,
        'popular_options': [
            {
                'name': 'Calendar Year',
                'start': f'{datetime.now().year}-01-01',
                'end': f'{datetime.now().year}-12-31',
                'type': 'calendar',
                'description': 'Most common for businesses',
                'recommended': True,
            },
            {
                'name': 'UK Tax Year',
                'start': f'{datetime.now().year}-04-01',
                'end': f'{datetime.now().year + 1}-03-31',
                'type': 'uk',
                'description': 'Aligned with UK tax calendar',
                'recommended': False,
            },
            {
                'name': 'Australian FY',
                'start': f'{datetime.now().year}-07-01',
                'end': f'{datetime.now().year + 1}-06-30',
                'type': 'australia',
                'description': 'Australian financial year',
                'recommended': False,
            },
        ]
    }
    
    return render(request, 'setup/financial_year_wizard.html', context)


@login_required 
def company_setup_wizard(request):
    """Company Details Setup - Step before Financial Year"""
    
    if request.method == 'POST':
        # Process company setup
        try:
            company_name = request.POST.get('company_name')
            industry = request.POST.get('industry')
            currency = request.POST.get('currency', 'USD')
            timezone = request.POST.get('timezone')
            
            # Store in session
            request.session['company_setup'] = {
                'company_name': company_name,
                'industry': industry,
                'currency': currency,
                'timezone': timezone,
                'setup_date': datetime.now().isoformat(),
            }
            
            messages.success(request, f'Welcome to Professional Accounting, {company_name}!')
            
            # Redirect to Financial Year setup
            return redirect('setup:financial_year_wizard')
            
        except Exception as e:
            messages.error(request, f'Error setting up company: {str(e)}')
    
    context = {
        'industries': [
            ('retail', 'Retail'),
            ('consulting', 'Consulting'),
            ('manufacturing', 'Manufacturing'),
            ('technology', 'Technology'),
            ('services', 'Professional Services'),
            ('healthcare', 'Healthcare'),
            ('construction', 'Construction'),
            ('other', 'Other'),
        ],
        'currencies': [
            ('USD', 'US Dollar ($)'),
            ('EUR', 'Euro (€)'),
            ('GBP', 'British Pound (£)'),
            ('AUD', 'Australian Dollar (A$)'),
            ('CAD', 'Canadian Dollar (C$)'),
        ],
    }
    
    return render(request, 'setup/company_wizard.html', context)


@login_required
def opening_balances_wizard(request):
    """Opening Balances Entry - Final setup step"""
    from coa.models import Account
    
    if request.method == 'POST':
        # Process opening balances
        try:
            balances_data = []
            
            # Process each account balance
            for key, value in request.POST.items():
                if key.startswith('balance_') and value:
                    account_id = key.replace('balance_', '')
                    try:
                        account = Account.objects.get(id=account_id)
                        balance_amount = float(value)
                        if balance_amount != 0:
                            balances_data.append({
                                'account_id': account_id,
                                'account_name': account.name,
                                'balance': balance_amount,
                            })
                    except (Account.DoesNotExist, ValueError):
                        continue
            
            # Store in session
            request.session['opening_balances_setup'] = {
                'balances': balances_data,
                'total_assets': sum([b['balance'] for b in balances_data if Account.objects.get(id=b['account_id']).account_type in ['asset', 'current_asset', 'fixed_asset']]),
                'total_liabilities': sum([b['balance'] for b in balances_data if Account.objects.get(id=b['account_id']).account_type in ['liability', 'current_liability', 'long_term_liability']]),
                'total_equity': sum([b['balance'] for b in balances_data if Account.objects.get(id=b['account_id']).account_type == 'equity']),
                'setup_date': datetime.now().isoformat(),
            }
            
            messages.success(request, 'Opening balances configured successfully!')
            
            # Mark setup as complete and redirect to completion page
            request.session['setup_complete'] = True
            return redirect('setup:setup_completion')
            
        except Exception as e:
            messages.error(request, f'Error setting up opening balances: {str(e)}')
    
    # Get all accounts organized by type
    try:
        accounts_by_type = {}
        account_types = [
            ('current_asset', 'Current Assets', 'bi-wallet2'),
            ('fixed_asset', 'Fixed Assets', 'bi-building'),
            ('current_liability', 'Current Liabilities', 'bi-credit-card'),
            ('long_term_liability', 'Long-term Liabilities', 'bi-bank'),
            ('equity', 'Equity', 'bi-pie-chart'),
        ]
        
        for account_type, type_label, icon in account_types:
            accounts = Account.objects.filter(account_type=account_type).order_by('code')
            if accounts.exists():
                accounts_by_type[account_type] = {
                    'label': type_label,
                    'icon': icon,
                    'accounts': accounts,
                    'is_debit_normal': account_type in ['current_asset', 'fixed_asset'],
                }
    
    except Exception:
        # Fallback if COA not set up yet
        accounts_by_type = {}
        messages.warning(request, 'Please set up your Chart of Accounts first.')
    
    context = {
        'accounts_by_type': accounts_by_type,
        'company_setup': request.session.get('company_setup', {}),
        'financial_year_setup': request.session.get('financial_year_setup', {}),
    }
    
    return render(request, 'setup/opening_balances_wizard.html', context)


@login_required
@require_http_methods(['GET'])
def setup_status_api(request):
    """API endpoint to check setup completion status"""
    
    setup_status = {
        'company_setup': bool(request.session.get('company_setup')),
        'financial_year_setup': bool(request.session.get('financial_year_setup')),
        'chart_of_accounts_setup': False,  # TODO: Check if COA has accounts
        'opening_balances_setup': bool(request.session.get('opening_balances_setup')),
    }
    
    # Check if COA has been set up (has accounts)
    try:
        from coa.models import Account
        setup_status['chart_of_accounts_setup'] = Account.objects.exists()
    except Exception:
        pass
    
    completion_percentage = sum(setup_status.values()) / len(setup_status) * 100
    
    return JsonResponse({
        'setup_status': setup_status,
        'completion_percentage': completion_percentage,
        'next_step': get_next_setup_step(setup_status),
        'setup_complete': request.session.get('setup_complete', False),
    })


def get_next_setup_step(setup_status):
    """Determine the next setup step for the user"""
    
    if not setup_status['company_setup']:
        return {
            'step': 'company_setup',
            'title': 'Company Details',
            'url': '/setup/company/',
        }
    elif not setup_status['financial_year_setup']:
        return {
            'step': 'financial_year',
            'title': 'Financial Year',
            'url': '/setup/financial-year/',
        }
    elif not setup_status['chart_of_accounts_setup']:
        return {
            'step': 'chart_of_accounts',
            'title': 'Chart of Accounts',
            'url': '/coa/',
        }
    elif not setup_status['opening_balances_setup']:
        return {
            'step': 'opening_balances',
            'title': 'Opening Balances',
            'url': '/setup/opening-balances/',
        }
    else:
        return {
            'step': 'complete',
            'title': 'Setup Complete',
            'url': '/dashboard/',
        }


@login_required
def setup_completion_view(request):
    """Setup completion celebration page"""
    
    company_setup = request.session.get('company_setup', {})
    financial_year_setup = request.session.get('financial_year_setup', {})
    
    context = {
        'company_name': company_setup.get('company_name', 'Your Company'),
        'financial_year': financial_year_setup,
        'setup_complete': True,
    }
    
    return render(request, 'setup/completion.html', context)
