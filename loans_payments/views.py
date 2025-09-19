"""
Basic views for payment processing functionality
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from decimal import Decimal
from company.models import Company


def get_user_company(user):
    """Helper function to get user's company"""
    return Company.objects.first()


@login_required
def payment_list(request):
    """List all payments with statistics and data"""
    # Calculate payment statistics (demo data for now)
    stats = {
        'payments_today': Decimal('25780.00'),
        'due_this_week': Decimal('67450.00'),
        'overdue_payments': Decimal('12350.00'),
        'monthly_collection': Decimal('450890.00'),
    }
    
    # Get active loans and recent payments (placeholder for now)
    active_loans = []
    recent_payments = []
    upcoming_payments = []
    
    return render(request, 'loans_payments/payment_list.html', {
        'stats': stats,
        'active_loans': active_loans,
        'recent_payments': recent_payments,
        'upcoming_payments': upcoming_payments,
        'today_date': timezone.now().date(),
        'title': 'Payment Processing',
    })


@login_required
def payment_create(request):
    """Create a new payment"""
    messages.info(request, 'Payment creation functionality coming soon.')
    return redirect('loans_payments:payment_list')


@login_required
def payment_quick_create(request):
    """Quick payment creation"""
    messages.info(request, 'Quick payment functionality coming soon.')
    return redirect('loans_payments:payment_list')


@login_required
def payment_detail(request, pk):
    """View payment details"""
    return render(request, 'loans_payments/payment_list.html', {
        'title': f'Payment #{pk}',
        'stats': {
            'payments_today': Decimal('0'),
            'due_this_week': Decimal('0'),
            'overdue_payments': Decimal('0'),
            'monthly_collection': Decimal('0'),
        },
        'active_loans': [],
        'recent_payments': [],
        'upcoming_payments': [],
        'today_date': timezone.now().date(),
    })


@login_required
def auto_payment_list(request):
    """List auto payments"""
    return render(request, 'loans_payments/payment_list.html', {
        'title': 'Auto Payments',
        'stats': {
            'payments_today': Decimal('0'),
            'due_this_week': Decimal('0'),
            'overdue_payments': Decimal('0'),
            'monthly_collection': Decimal('0'),
        },
        'active_loans': [],
        'recent_payments': [],
        'upcoming_payments': [],
        'today_date': timezone.now().date(),
    })


@login_required
def auto_payment_create(request):
    """Create auto payment"""
    messages.info(request, 'Auto payment functionality coming soon.')
    return redirect('loans_payments:auto_payment_list')


@login_required
def auto_payment_edit(request, pk):
    """Edit auto payment"""
    messages.info(request, 'Auto payment editing functionality coming soon.')
    return redirect('loans_payments:auto_payment_list')


@login_required
def bulk_payment_process(request):
    """Bulk payment processing"""
    messages.info(request, 'Bulk payment processing functionality coming soon.')
    return redirect('loans_payments:payment_list')


@login_required
def payment_search(request):
    """Payment search API"""
    return JsonResponse({'success': False, 'message': 'Search functionality coming soon.'})
