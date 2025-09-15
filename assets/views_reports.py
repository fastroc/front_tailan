"""
Fixed Asset Reporting Views
Accounting-focused views for balance sheet, trial balance, and tax reporting
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db import models
from datetime import datetime, date
from decimal import Decimal

from .reports import AssetAccountingReports, BalanceSheetIntegration, TrialBalanceIntegration
from .models import FixedAsset, AssetType


class AssetReportsMenuView(LoginRequiredMixin, TemplateView):
    """Main reports menu for asset accounting reports"""
    template_name = 'assets/reports/menu.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get basic statistics for the menu
        company = self.request.user.company
        total_assets = FixedAsset.objects.filter(company=company).count()
        total_value = FixedAsset.objects.filter(company=company).aggregate(
            total=models.Sum('purchase_price')
        )['total'] or 0
        
        context.update({
            'total_assets': total_assets,
            'total_value': total_value,
            'current_date': timezone.now().date()
        })
        
        return context


@login_required
def balance_sheet_assets_report(request):
    """Balance sheet assets report"""
    # Get report parameters
    as_of_date_str = request.GET.get('as_of_date')
    if as_of_date_str:
        as_of_date = datetime.strptime(as_of_date_str, '%Y-%m-%d').date()
    else:
        as_of_date = timezone.now().date()
    
    # Generate report
    reports = AssetAccountingReports(
        company=request.user.company,
        as_of_date=as_of_date
    )
    
    balance_sheet_data = reports.get_balance_sheet_assets()
    
    context = {
        'report_data': balance_sheet_data,
        'report_title': 'Fixed Assets - Balance Sheet',
        'company': request.user.company,
        'as_of_date': as_of_date
    }
    
    return render(request, 'assets/reports/balance_sheet.html', context)


@login_required
def trial_balance_assets_report(request):
    """Trial balance assets report"""
    # Get report parameters
    as_of_date_str = request.GET.get('as_of_date')
    if as_of_date_str:
        as_of_date = datetime.strptime(as_of_date_str, '%Y-%m-%d').date()
    else:
        as_of_date = timezone.now().date()
    
    # Generate report
    reports = AssetAccountingReports(
        company=request.user.company,
        as_of_date=as_of_date
    )
    
    trial_balance_data = reports.get_trial_balance_assets()
    
    context = {
        'report_data': trial_balance_data,
        'report_title': 'Trial Balance - Fixed Assets',
        'company': request.user.company,
        'as_of_date': as_of_date
    }
    
    return render(request, 'assets/reports/trial_balance.html', context)


@login_required
def tax_depreciation_schedule_report(request):
    """Tax depreciation schedule report"""
    # Get report parameters
    tax_year = request.GET.get('year')
    if tax_year:
        tax_year = int(tax_year)
    else:
        tax_year = timezone.now().year
    
    # Generate report
    reports = AssetAccountingReports(
        company=request.user.company,
        as_of_date=date(tax_year, 12, 31)
    )
    
    tax_schedule_data = reports.get_tax_depreciation_schedule(tax_year)
    
    context = {
        'report_data': tax_schedule_data,
        'report_title': f'Tax Depreciation Schedule - {tax_year}',
        'company': request.user.company,
        'tax_year': tax_year
    }
    
    return render(request, 'assets/reports/tax_schedule.html', context)


@login_required
def asset_movements_report(request):
    """Asset movements (additions/disposals) report"""
    # Get report parameters
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    else:
        start_date = date(timezone.now().year, 1, 1)  # Start of current year
    
    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    else:
        end_date = timezone.now().date()
    
    # Generate report
    reports = AssetAccountingReports(
        company=request.user.company
    )
    
    movements_data = reports.get_asset_movements_report(start_date, end_date)
    
    context = {
        'report_data': movements_data,
        'report_title': 'Asset Additions & Disposals',
        'company': request.user.company
    }
    
    return render(request, 'assets/reports/movements.html', context)


@login_required
def depreciation_expense_report(request):
    """Depreciation expense summary report"""
    # Get report parameters
    year = request.GET.get('year')
    if year:
        year = int(year)
    else:
        year = timezone.now().year
    
    # Generate report
    reports = AssetAccountingReports(
        company=request.user.company
    )
    
    expense_data = reports.get_depreciation_expense_summary(year)
    
    context = {
        'report_data': expense_data,
        'report_title': f'Depreciation Expense Summary - {year}',
        'company': request.user.company,
        'year': year
    }
    
    return render(request, 'assets/reports/depreciation_expense.html', context)


@login_required
def asset_register_report(request):
    """Complete asset register report"""
    # Get report parameters
    as_of_date_str = request.GET.get('as_of_date')
    category_id = request.GET.get('category')
    status = request.GET.get('status', 'active')
    
    if as_of_date_str:
        as_of_date = datetime.strptime(as_of_date_str, '%Y-%m-%d').date()
    else:
        as_of_date = timezone.now().date()
    
    # Build queryset
    assets = FixedAsset.objects.filter(
        company=request.user.company,
        purchase_date__lte=as_of_date
    ).select_related('asset_type').order_by('asset_type__name', 'name')
    
    if category_id:
        assets = assets.filter(asset_type_id=category_id)
    
    if status != 'all':
        assets = assets.filter(status=status)
    
    # Calculate totals
    total_cost = sum(asset.purchase_price for asset in assets)
    total_accumulated_dep = sum(asset.accumulated_depreciation for asset in assets)
    net_book_value = total_cost - total_accumulated_dep
    
    # Group by category for summary
    categories_summary = {}
    for asset in assets:
        category_name = asset.asset_type.name if asset.asset_type else 'Uncategorized'
        if category_name not in categories_summary:
            categories_summary[category_name] = {
                'count': 0,
                'cost': 0,
                'accumulated_dep': 0
            }
        categories_summary[category_name]['count'] += 1
        categories_summary[category_name]['cost'] += asset.purchase_price
        categories_summary[category_name]['accumulated_dep'] += asset.accumulated_depreciation
    
    # Calculate net values for each category
    for category in categories_summary.values():
        category['net_book_value'] = category['cost'] - category['accumulated_dep']
    
    context = {
        'assets': assets,
        'categories_summary': categories_summary,
        'totals': {
            'count': assets.count(),
            'total_cost': total_cost,
            'total_accumulated_dep': total_accumulated_dep,
            'net_book_value': net_book_value
        },
        'report_title': 'Fixed Asset Register',
        'company': request.user.company,
        'as_of_date': as_of_date,
        'asset_types': AssetType.objects.filter(is_active=True),
        'selected_category': category_id,
        'selected_status': status
    }
    
    return render(request, 'assets/reports/asset_register.html', context)


# ===== AJAX ENDPOINTS FOR INTEGRATION =====

@login_required
def api_balance_sheet_assets(request):
    """API endpoint for balance sheet integration"""
    as_of_date_str = request.GET.get('as_of_date')
    if as_of_date_str:
        as_of_date = datetime.strptime(as_of_date_str, '%Y-%m-%d').date()
    else:
        as_of_date = timezone.now().date()
    
    balance_sheet_data = BalanceSheetIntegration.get_fixed_assets_for_balance_sheet(
        company=request.user.company,
        as_of_date=as_of_date
    )
    
    # Convert Decimal to float for JSON serialization
    def decimal_to_float(obj):
        if hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
            return {k: decimal_to_float(v) for k, v in obj.items()} if isinstance(obj, dict) else [decimal_to_float(item) for item in obj]
        return float(obj) if isinstance(obj, Decimal) else obj
    
    return JsonResponse(decimal_to_float(balance_sheet_data))


@login_required
def api_trial_balance_assets(request):
    """API endpoint for trial balance integration"""
    as_of_date_str = request.GET.get('as_of_date')
    if as_of_date_str:
        as_of_date = datetime.strptime(as_of_date_str, '%Y-%m-%d').date()
    else:
        as_of_date = timezone.now().date()
    
    trial_balance_data = TrialBalanceIntegration.get_asset_trial_balance_entries(
        company=request.user.company,
        as_of_date=as_of_date
    )
    
    # Convert Decimal to float for JSON serialization
    def decimal_to_float(obj):
        if hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
            return {k: decimal_to_float(v) for k, v in obj.items()} if isinstance(obj, dict) else [decimal_to_float(item) for item in obj]
        return float(obj) if isinstance(obj, Decimal) else obj
    
    return JsonResponse(decimal_to_float(trial_balance_data))


# ===== EXPORT FUNCTIONALITY =====

@login_required
def export_report(request, report_type):
    """Export reports to Excel/PDF"""
    # This would be implemented based on specific export requirements
    # For now, return a placeholder response
    
    export_format = request.GET.get('format', 'excel')
    
    if export_format == 'excel':
        # Implement Excel export
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report.xlsx"'
        
        # Add Excel generation logic here
        return response
    
    elif export_format == 'pdf':
        # Implement PDF export
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report.pdf"'
        
        # Add PDF generation logic here
        return response
    
    else:
        return JsonResponse({'error': 'Invalid export format'}, status=400)
