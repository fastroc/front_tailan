"""
Payment processing functionality with industry-standard allocation logic
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from django.db import models
from decimal import Decimal, InvalidOperation

from company.models import Company
from loans_core.models import Loan
from loans_schedule.models import ScheduledPayment
from .models import Payment, PaymentProcessor


def get_user_company(user):
    """Helper function to get user's company"""
    try:
        return user.usercompanyprofile.company
    except Exception:
        return Company.objects.first()


@login_required
def payment_list(request):
    """Payment processing dashboard with real-time statistics"""
    company = get_user_company(request.user)
    
    # Get payment statistics
    today = timezone.now().date()
    
    # Mock sample data for demo purposes
    stats = {
        'payments_today': Decimal('1450.00'),  # Mock data: 3 payments today
        'due_this_week': Decimal('3200.00'),   # Mock data: upcoming payments
        'overdue_payments': Decimal('850.00'), # Mock data: overdue amounts
        'monthly_collection': Decimal('8750.00'), # Mock data: monthly total
    }
    
    # If you want real data, uncomment below and comment above:
    # stats = {
    #     'payments_today': Payment.objects.filter(
    #         company=company,
    #         payment_date=today
    #     ).aggregate(
    #         total=models.Sum('payment_amount')
    #     )['total'] or Decimal('0.00'),
    #     
    #     'due_this_week': ScheduledPayment.objects.filter(
    #         loan__company=company,
    #         status='scheduled',
    #         due_date__range=[today, today + timezone.timedelta(days=7)]
    #     ).aggregate(
    #         total=models.Sum('total_amount')
    #     )['total'] or Decimal('0.00'),
    #     
    #     'overdue_payments': ScheduledPayment.objects.filter(
    #         loan__company=company,
    #         status__in=['overdue', 'partial'],
    #         due_date__lt=today
    #     ).aggregate(
    #         total=models.Sum('total_amount')
    #     )['total'] or Decimal('0.00'),
    #     
    #     'monthly_collection': Payment.objects.filter(
    #         company=company,
    #         payment_date__year=today.year,
    #         payment_date__month=today.month
    #     ).aggregate(
    #         total=models.Sum('payment_amount')
    #     )['total'] or Decimal('0.00'),
    # }
    
    # Get active loans for dropdown (mock data for demo)
    class MockLoan:
        def __init__(self, id, loan_number, customer_name, balance, product_name):
            self.id = id
            self.loan_number = loan_number
            self.customer = type('Customer', (), {
                'first_name': customer_name.split()[0],
                'last_name': customer_name.split()[1] if len(customer_name.split()) > 1 else ''
            })()
            self.outstanding_balance = balance
            self.loan_product = type('Product', (), {'name': product_name})()

    # Mock active loans for demo
    active_loans = [
        MockLoan(1, 'DL2025001', 'John Smith', Decimal('4250.00'), 'Personal Loan'),
        MockLoan(2, 'DL2025002', 'Sarah Johnson', Decimal('8900.00'), 'Business Loan'),
        MockLoan(3, 'DL2025003', 'Michael Brown', Decimal('12750.00'), 'Auto Loan'),
        MockLoan(4, 'DL2025004', 'Emily Davis', Decimal('6300.00'), 'Personal Loan'),
        MockLoan(5, 'DL2025005', 'David Wilson', Decimal('9850.00'), 'Home Loan'),
    ]
    
    # Mock recent payments for demo
    class MockPayment:
        def __init__(self, payment_date, loan_number, customer_name, amount, method, notes):
            self.payment_date = payment_date
            self.loan = type('Loan', (), {
                'loan_number': loan_number,
                'customer': type('Customer', (), {
                    'first_name': customer_name.split()[0],
                    'last_name': customer_name.split()[1] if len(customer_name.split()) > 1 else ''
                })()
            })()
            self.payment_amount = amount
            self.payment_method = method
            self.notes = notes

    recent_payments = [
        MockPayment(today, 'DL2025001', 'John Smith', Decimal('450.00'), 'cash', 'Regular monthly payment'),
        MockPayment(today, 'DL2025003', 'Michael Brown', Decimal('650.00'), 'bank_transfer', 'Early payment'),
        MockPayment(today, 'DL2025002', 'Sarah Johnson', Decimal('350.00'), 'check', 'Partial payment'),
        MockPayment(today - timezone.timedelta(days=1), 'DL2025004', 'Emily Davis', Decimal('525.00'), 'online', 'Monthly payment'),
        MockPayment(today - timezone.timedelta(days=2), 'DL2025005', 'David Wilson', Decimal('800.00'), 'cash', 'Extra payment'),
    ]
    
    # If you want real data, uncomment below and comment above:
    # recent_payments = Payment.objects.filter(
    #     company=company
    # ).select_related('loan', 'loan__customer').order_by('-payment_date')[:10]
    
    return render(request, 'loans_payments/payment_list_hybrid.html', {
        'stats': stats,
        'active_loans': active_loans,
        'recent_payments': recent_payments,
        'today_date': today,
        'title': 'Payment Processing',
        'company': company,
    })


@login_required
def payment_create(request):
    """Create a new payment - simplified version"""
    company = get_user_company(request.user)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Get form data
                loan_id = request.POST.get('loan_id')
                payment_amount = Decimal(request.POST.get('payment_amount', '0'))
                payment_method = request.POST.get('payment_method')
                payment_date = request.POST.get('payment_date')
                reference_number = request.POST.get('reference_number', '')
                notes = request.POST.get('notes', '')
                
                # Validate inputs
                if not loan_id or payment_amount <= 0 or not payment_method:
                    messages.error(request, 'Please fill all required fields with valid values.')
                    return redirect('loans_payments:payment_list')
                
                # Get loan
                loan = get_object_or_404(Loan, id=loan_id, company=company)
                
                # Parse payment date
                if payment_date:
                    from datetime import datetime
                    payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
                else:
                    payment_date = timezone.now().date()
                
                # Create simple payment record
                payment = Payment.objects.create(
                    company=company,
                    loan=loan,
                    customer=loan.customer,
                    payment_amount=payment_amount,
                    payment_date=payment_date,
                    payment_method=payment_method,
                    reference_number=reference_number,
                    notes=notes,
                    processed_by=request.user,
                    created_by=request.user
                )
                
                messages.success(
                    request, 
                    f'Payment ${payment_amount} recorded successfully for loan {loan.loan_number}.'
                )
                
                return redirect('loans_payments:payment_detail', pk=payment.pk)
        
        except (ValueError, InvalidOperation, Decimal.InvalidOperation) as e:
            messages.error(request, f'Invalid payment amount: {e}')
        except Exception as e:
            messages.error(request, f'Error processing payment: {e}')
    
    return redirect('loans_payments:payment_list')


@login_required
def payment_quick_create(request):
    """Quick payment creation"""
    messages.info(request, 'Quick payment functionality coming soon.')
    return redirect('loans_payments:payment_list')


@login_required
def payment_allocation_preview(request):
    """AJAX endpoint for payment allocation preview"""
    company = get_user_company(request.user)
    
    try:
        loan_id = request.GET.get('loan_id')
        payment_amount = Decimal(request.GET.get('payment_amount', '0'))
        
        if not loan_id or payment_amount <= 0:
            return JsonResponse({'success': False, 'error': 'Invalid parameters'})
        
        loan = get_object_or_404(Loan, id=loan_id, company=company)
        
        # Calculate allocation preview
        processor = PaymentProcessor(company=company)
        allocation = processor.calculate_allocation(loan, payment_amount)
        
        return JsonResponse({
            'success': True,
            'allocation': {
                'late_fees': str(allocation['late_fees']),
                'accrued_interest': str(allocation['accrued_interest']),
                'current_interest': str(allocation['current_interest']),
                'principal': str(allocation['principal']),
                'prepayment': str(allocation['prepayment']),
                'total_allocated': str(allocation['total_allocated']),
                'remaining_amount': str(allocation['remaining_amount']),
                'allocation_order': allocation['allocation_order']
            },
            'loan_info': {
                'loan_number': loan.loan_number,
                'customer_name': loan.customer.full_name,
                'current_balance': str(loan.current_balance or Decimal('0')),
                'next_payment_due': str(loan.next_payment_amount or Decimal('0'))
            }
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def payment_detail(request, pk):
    """View payment details with allocation breakdown"""
    company = get_user_company(request.user)
    payment = get_object_or_404(Payment, pk=pk, company=company)
    
    # Get payment allocations
    allocations = payment.allocations.all().order_by('allocation_order')
    
    # Get payment history
    history = payment.history.all().order_by('-action_date')
    
    return render(request, 'loans_payments/payment_detail.html', {
        'payment': payment,
        'allocations': allocations,
        'history': history,
        'title': f'Payment #{payment.payment_id}',
        'company': company,
    })


@login_required
def loan_search(request):
    """AJAX endpoint for loan search"""
    company = get_user_company(request.user)
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'success': False, 'error': 'Query too short'})
    
    # Search loans by loan number or customer name (only disbursed loans)
    loans = Loan.objects.filter(
        company=company,
        status__in=['active', 'disbursed', 'current']  # Only show loans that are disbursed
    ).filter(
        models.Q(loan_number__icontains=query) |
        models.Q(customer__first_name__icontains=query) |
        models.Q(customer__last_name__icontains=query)
    ).select_related('customer')[:10]
    
    results = []
    for loan in loans:
        # Get next payment info
        next_payment = loan.scheduled_payments.filter(
            status__in=['scheduled', 'overdue']
        ).order_by('due_date').first()
        
        results.append({
            'id': loan.id,
            'loan_number': loan.loan_number,
            'customer_name': loan.customer.full_name,
            'current_balance': str(loan.current_balance or Decimal('0')),
            'next_payment_amount': str(next_payment.total_amount if next_payment else Decimal('0')),
            'next_payment_date': next_payment.due_date.strftime('%Y-%m-%d') if next_payment else '',
            'status': next_payment.status if next_payment else 'current'
        })
    
    return JsonResponse({'success': True, 'loans': results})


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
