from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json

# Import from other apps
from loans_core.views import get_user_company
from .services import ReportService
from .models import ReportConfiguration, ReportExport


@login_required
def dashboard(request):
    """
    Main loan reports dashboard with 100% dynamic data
    """
    try:
        user_company = get_user_company(request.user)
        report_service = ReportService(user_company)
        
        # Get all dynamic data using the service
        portfolio_data = report_service.portfolio_analytics()
        aging_data = report_service.aging_analysis()
        monthly_data = report_service.monthly_trends(months=9)
        customer_data = report_service.customer_performance(limit=5)
        risk_data = report_service.risk_metrics()
        
        # Get user's saved report configurations
        user_configs = ReportConfiguration.objects.filter(
            user=request.user,
            company=user_company,
            is_active=True
        )[:5]
        
        context = {
            'title': 'Dynamic Loan Reports & Analytics',
            'company': user_company,
            'portfolio_stats': portfolio_data,
            'aging_analysis': aging_data,
            'monthly_data': monthly_data,
            'top_customers': customer_data,
            'risk_metrics': risk_data,
            'user_configs': user_configs,
            'data_status': '100% Dynamic',
            'last_updated': timezone.now(),
        }
        
        return render(request, 'loan_report/dashboard.html', context)
        
    except Exception as e:
        messages.error(request, f"Error loading reports: {str(e)}")
        # Fail-safe: render with minimal data
        return render(request, 'loan_report/dashboard.html', {
            'title': 'Loan Reports - Error',
            'error': str(e),
            'data_status': 'Error',
        })


@login_required
def api_portfolio_data(request):
    """
    API endpoint for dynamic portfolio data
    """
    try:
        user_company = get_user_company(request.user)
        report_service = ReportService(user_company)
        
        # Get date range from request
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        data = report_service.portfolio_analytics(start_date, end_date)
        
        # Convert Decimal to float for JSON serialization
        for key, value in data.items():
            if isinstance(value, Decimal):
                data[key] = float(value)
        
        return JsonResponse({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def api_monthly_trends(request):
    """
    API endpoint for monthly trends data
    """
    try:
        user_company = get_user_company(request.user)
        report_service = ReportService(user_company)
        
        months = int(request.GET.get('months', 12))
        data = report_service.monthly_trends(months)
        
        return JsonResponse({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def api_aging_analysis(request):
    """
    API endpoint for aging analysis data
    """
    try:
        user_company = get_user_company(request.user)
        report_service = ReportService(user_company)
        
        data = report_service.aging_analysis()
        
        # Convert Decimal to float for JSON serialization
        def convert_decimals(obj):
            if isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, Decimal):
                return float(obj)
            return obj
        
        data = convert_decimals(data)
        
        return JsonResponse({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def export_report(request):
    """
    Handle report export requests
    """
    try:
        user_company = get_user_company(request.user)
        
        export_format = request.POST.get('format', 'pdf')
        report_type = request.POST.get('report_type', 'portfolio')
        
        # Create export record
        export_obj = ReportExport.objects.create(
            user=request.user,
            company=user_company,
            report_type=report_type,
            format=export_format,
            status='pending',
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        # TODO: Implement actual export generation (PDF/Excel/CSV)
        # For now, mark as completed with mock file
        export_obj.status = 'completed'
        export_obj.file_path = f'exports/{report_type}_{export_format}_{export_obj.id}.{export_format}'
        export_obj.completed_at = timezone.now()
        export_obj.save()
        
        return JsonResponse({
            'success': True,
            'export_id': export_obj.id,
            'message': f'{export_format.upper()} export created successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def save_report_config(request):
    """
    Save user report configuration
    """
    try:
        user_company = get_user_company(request.user)
        
        config_data = json.loads(request.body)
        
        config = ReportConfiguration.objects.create(
            user=request.user,
            company=user_company,
            report_type=config_data.get('report_type', 'portfolio'),
            name=config_data.get('name', 'My Report'),
            date_range=config_data.get('date_range', '30d'),
            filters=config_data.get('filters', {}),
            is_favorite=config_data.get('is_favorite', False)
        )
        
        return JsonResponse({
            'success': True,
            'config_id': config.id,
            'message': 'Report configuration saved'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def refresh_cache(request):
    """
    Force refresh all cached report data
    """
    try:
        user_company = get_user_company(request.user)
        report_service = ReportService(user_company, use_cache=False)
        
        # Force refresh all report types
        report_service.portfolio_analytics()
        report_service.aging_analysis()
        report_service.monthly_trends()
        report_service.customer_performance()
        report_service.risk_metrics()
        
        return JsonResponse({
            'success': True,
            'message': 'Cache refreshed successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
