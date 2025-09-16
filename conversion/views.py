from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from datetime import date, timedelta
import json

from .models import ConversionDate, ConversionBalance
from .forms import ConversionDateForm
from coa.models import Account
from company.models import Company


@login_required
def conversion_date_view(request, company_id):
    """View for setting conversion date"""
    company = get_object_or_404(
        Company,
        id=company_id,
        user_access__user=request.user,
        is_active=True
    )
    
    # Get or create conversion date
    conv_date, created = ConversionDate.objects.get_or_create(
        company=company,
        defaults={'conversion_date': date.today().replace(day=1)}
    )
    
    if request.method == 'POST':
        form = ConversionDateForm(request.POST, instance=conv_date)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conversion date saved successfully.')
            return redirect('conversion:balances', company_id=company.id)
    else:
        form = ConversionDateForm(instance=conv_date)
    
    # Prepare context for template
    context = {
        'company': company,
        'form': form,
        'conv_date': conv_date,
        'months': [
            {'value': i, 'label': date(2000, i, 1).strftime('%B')}
            for i in range(1, 13)
        ],
        'years': list(range(date.today().year - 5, date.today().year + 2)),
        'default_month': conv_date.conversion_date.month if conv_date.conversion_date else date.today().month,
        'default_year': conv_date.conversion_date.year if conv_date.conversion_date else date.today().year,
    }
    
    return render(request, 'conversion/conversion_date.html', context)


@login_required
def conversion_balances_view(request, company_id):
    """View for entering conversion balances"""
    company = get_object_or_404(
        Company,
        id=company_id,
        user_access__user=request.user,
        is_active=True
    )
    
    # Get conversion date
    try:
        conv_date = ConversionDate.objects.get(company=company)
        as_at_date = conv_date.as_at_date
    except ConversionDate.DoesNotExist:
        messages.warning(request, 'Please set a conversion date first.')
        return redirect('conversion:date', company_id=company.id)
    
    # Get existing balances
    existing_balances = ConversionBalance.objects.filter(
        company=company,
        as_at_date=as_at_date
    ).select_related('account')
    
    # Get all accounts for the company
    accounts = Account.objects.filter(company=company).order_by('code', 'name')
    
    # Prepare periods for tabs
    periods = get_conversion_periods(company, as_at_date)
    
    # Prepare rows for template
    rows = []
    for balance in existing_balances:
        rows.append({
            'account': balance.account.code,
            'debit': balance.debit_amount if balance.debit_amount > 0 else None,
            'credit': balance.credit_amount if balance.credit_amount > 0 else None,
        })
    
    # Add some empty rows if no balances exist
    if not rows:
        rows = [{'account': '', 'debit': None, 'credit': None} for _ in range(5)]
    
    context = {
        'company': company,
        'conv_date': conv_date,
        'as_at': as_at_date,
        'periods': periods,
        'rows': rows,
        'accounts': accounts,
        'help_items': [
            {
                'title': 'Enter bank balances',
                'body': 'Enter the exact balance shown on your bank statements as at the conversion date.'
            },
            {
                'title': 'Outstanding invoices',
                'body': 'Enter all unpaid customer invoices as at the conversion date.'
            },
            {
                'title': 'Outstanding bills',
                'body': 'Enter all unpaid supplier bills as at the conversion date.'
            },
            {
                'title': 'Inventory and assets',
                'body': 'Enter the value of inventory, equipment, and other assets.'
            },
            {
                'title': 'Loans and liabilities',
                'body': 'Enter loan balances, credit cards, and other liabilities.'
            }
        ]
    }
    
    return render(request, 'conversion/conversion_balances.html', context)


@login_required
def conversion_comparatives_view(request, company_id):
    """View for adding comparative balances"""
    company = get_object_or_404(
        Company,
        id=company_id,
        user_access__user=request.user,
        is_active=True
    )
    
    context = {
        'company': company,
    }
    
    return render(request, 'conversion/conversion_comparatives.html', context)


@require_http_methods(["POST"])
@login_required
def save_conversion_balances(request, company_id):
    """API endpoint to save conversion balances"""
    company = get_object_or_404(
        Company,
        id=company_id,
        user_access__user=request.user,
        is_active=True
    )
    
    try:
        data = json.loads(request.body)
        as_at_date = data.get('as_at')
        lines = data.get('lines', [])
        
        with transaction.atomic():
            # Delete existing balances for this date
            ConversionBalance.objects.filter(
                company=company,
                as_at_date=as_at_date
            ).delete()
            
            # Create new balances
            for line in lines:
                account = get_object_or_404(
                    Account, 
                    company=company, 
                    code=line['account']
                )
                
                ConversionBalance.objects.create(
                    company=company,
                    account=account,
                    as_at_date=as_at_date,
                    debit_amount=line.get('debit', 0),
                    credit_amount=line.get('credit', 0)
                )
        
        return JsonResponse({
            'success': True,
            'message': 'Conversion balances saved successfully.'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


def get_conversion_periods(company, as_at_date):
    """Generate period tabs for conversion balances"""
    current_year = as_at_date.year
    
    # Format dates in "1 Jan 2024" format
    def format_date(dt):
        return dt.strftime("%d %b %Y").lstrip('0')
    
    periods = [
        {
            'label': f'{format_date(date(current_year, 1, 1))} - {format_date(date(current_year, 12, 31))}, Current year',
            'start': date(current_year, 1, 1),
            'end': date(current_year, 12, 31),
            'active': True
        },
        {
            'label': f'{format_date(date(current_year - 1, 1, 1))} - {format_date(date(current_year - 1, 12, 31))}, Previous year',
            'start': date(current_year - 1, 1, 1),
            'end': date(current_year - 1, 12, 31),
            'active': False
        },
        {
            'label': f'{format_date(as_at_date - timedelta(days=180))} - {format_date(as_at_date)}, Last 6 months',
            'start': as_at_date - timedelta(days=180),
            'end': as_at_date,
            'active': False
        }
    ]
    
    return periods
