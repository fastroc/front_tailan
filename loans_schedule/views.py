"""
Views for payment scheduling functionality
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from decimal import Decimal
import json
from datetime import timedelta
import calendar

from .models import PaymentSchedule, ScheduledPayment, CustomPaymentPreset, PaymentDateRule
from company.models import Company
from .forms import (
    PaymentScheduleForm, ScheduledPaymentForm, CustomPaymentPresetForm,
    PaymentDateRuleForm, PaymentScheduleGeneratorForm, BulkPaymentUpdateForm
)
from loans_core.models import Loan


def get_user_company(user):
    """Helper function to get user's company"""
    # For now, just return the first company since UserProfile doesn't have company relationships
    return Company.objects.first()


@login_required
def payment_schedule_list(request):
    """List all payment schedules"""
    user_company = get_user_company(request.user)
    schedules = PaymentSchedule.objects.filter(
        company=user_company
    ).select_related('loan', 'loan__customer').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        is_active = status_filter == 'active'
        schedules = schedules.filter(is_active=is_active)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        schedules = schedules.filter(
            Q(loan__loan_number__icontains=search_query) |
            Q(loan__customer__first_name__icontains=search_query) |
            Q(loan__customer__last_name__icontains=search_query) |
            Q(schedule_type__icontains=search_query)
        )
    
    paginator = Paginator(schedules, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'loans_schedule/payment_schedules.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
    })


@login_required
def payment_schedule_detail(request, pk):
    """View payment schedule details"""
    user_company = get_user_company(request.user)
    schedule = get_object_or_404(
        PaymentSchedule.objects.select_related('loan', 'loan__customer'),
        pk=pk, company=user_company
    )
    
    # Get scheduled payments
    payments = ScheduledPayment.objects.filter(
        schedule=schedule
    ).order_by('payment_number')
    
    # Calculate statistics
    stats = {
        'total_payments': payments.count(),
        'paid_payments': payments.filter(is_paid=True).count(),
        'overdue_payments': payments.filter(
            due_date__lt=timezone.now().date(), is_paid=False
        ).count(),
        'total_amount': payments.aggregate(total=Sum('total_amount'))['total'] or Decimal('0'),
        'paid_amount': payments.filter(is_paid=True).aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0'),
        'remaining_amount': payments.filter(is_paid=False).aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0'),
    }
    
    return render(request, 'loans_schedule/payment_schedule_detail.html', {
        'schedule': schedule,
        'payments': payments,
        'stats': stats,
    })


@login_required
def payment_schedule_create(request):
    """Create a new payment schedule"""
    user_company = get_user_company(request.user)
    
    if request.method == 'POST':
        form = PaymentScheduleForm(request.POST, company=user_company)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.company = user_company
            schedule.created_by = request.user
            schedule.save()
            
            # Generate scheduled payments
            generate_scheduled_payments(schedule)
            
            messages.success(request, f'Payment schedule created with {schedule.total_payments} payments.')
            return redirect('loans_schedule:schedule_detail', pk=schedule.pk)
    else:
        form = PaymentScheduleForm(company=user_company)
    
    return render(request, 'loans_schedule/payment_schedule_form.html', {
        'form': form,
        'title': 'Create Payment Schedule',
    })


@login_required
def payment_schedule_generate(request):
    """Generate payment schedule with advanced options"""
    user_company = get_user_company(request.user)
    
    if request.method == 'POST':
        form = PaymentScheduleGeneratorForm(request.POST, company=user_company)
        if form.is_valid():
            loan = form.cleaned_data['loan']
            
            # Create payment schedule
            schedule = PaymentSchedule.objects.create(
                company=user_company,
                loan=loan,
                schedule_type=form.cleaned_data['calculation_method'],
                payment_frequency=form.cleaned_data['payment_frequency'],
                start_date=form.cleaned_data['start_date'],
                payment_amount=form.cleaned_data.get('custom_payment_amount', Decimal('0')),
                is_active=True,
                created_by=request.user
            )
            
            # Generate payments based on method
            generate_advanced_payments(
                schedule, 
                form.cleaned_data['calculation_method'],
                form.cleaned_data
            )
            
            messages.success(request, f'Advanced payment schedule generated for loan {loan.loan_number}.')
            return redirect('loans_schedule:schedule_detail', pk=schedule.pk)
    else:
        form = PaymentScheduleGeneratorForm(company=user_company)
    
    return render(request, 'loans_schedule/payment_schedule_generator.html', {
        'form': form,
        'title': 'Generate Payment Schedule',
    })


@login_required
def scheduled_payment_edit(request, schedule_pk, payment_pk):
    """Edit a scheduled payment"""
    user_company = get_user_company(request.user)
    schedule = get_object_or_404(PaymentSchedule, pk=schedule_pk, company=user_company)
    payment = get_object_or_404(ScheduledPayment, pk=payment_pk, schedule=schedule)
    
    if request.method == 'POST':
        form = ScheduledPaymentForm(request.POST, instance=payment)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.updated_by = request.user
            payment.save()
            messages.success(request, f'Payment #{payment.payment_number} updated successfully.')
            return redirect('loans_schedule:schedule_detail', pk=schedule.pk)
    else:
        form = ScheduledPaymentForm(instance=payment)
    
    return render(request, 'loans_schedule/scheduled_payment_form.html', {
        'form': form,
        'schedule': schedule,
        'payment': payment,
        'title': f'Edit Payment #{payment.payment_number}',
    })


@login_required
def custom_preset_list(request):
    """List custom payment presets"""
    user_company = get_user_company(request.user)
    presets = CustomPaymentPreset.objects.filter(company=user_company).order_by('-created_at')
    
    return render(request, 'loans_schedule/custom_presets.html', {
        'presets': presets,
    })


@login_required
def custom_preset_create(request):
    """Create a custom payment preset"""
    if request.method == 'POST':
        form = CustomPaymentPresetForm(request.POST)
        if form.is_valid():
            preset = form.save(commit=False)
            preset.company = get_user_company(request.user)
            preset.created_by = request.user
            preset.save()
            messages.success(request, f'Payment preset "{preset.name}" created successfully.')
            return redirect('loans_schedule:preset_list')
    else:
        form = CustomPaymentPresetForm()
    
    return render(request, 'loans_schedule/custom_preset_form.html', {
        'form': form,
        'title': 'Create Payment Preset',
    })


@login_required
def payment_date_rule_list(request):
    """List payment date rules"""
    user_company = get_user_company(request.user)
    rules = PaymentDateRule.objects.filter(company=user_company).order_by('-created_at')
    
    return render(request, 'loans_schedule/payment_date_rules.html', {
        'rules': rules,
    })


@login_required
def payment_date_rule_create(request):
    """Create a payment date rule"""
    if request.method == 'POST':
        form = PaymentDateRuleForm(request.POST)
        if form.is_valid():
            rule = form.save(commit=False)
            rule.company = get_user_company(request.user)
            rule.created_by = request.user
            rule.save()
            messages.success(request, f'Payment date rule "{rule.name}" created successfully.')
            return redirect('loans_schedule:rule_list')
    else:
        form = PaymentDateRuleForm()
    
    return render(request, 'loans_schedule/payment_date_rule_form.html', {
        'form': form,
        'title': 'Create Payment Date Rule',
    })


@login_required
def bulk_payment_update(request, schedule_pk):
    """Bulk update scheduled payments"""
    user_company = get_user_company(request.user)
    schedule = get_object_or_404(PaymentSchedule, pk=schedule_pk, company=user_company)
    
    if request.method == 'POST':
        form = BulkPaymentUpdateForm(request.POST)
        if form.is_valid():
            payment_ids = form.cleaned_data['payment_ids']
            update_type = form.cleaned_data['update_type']
            
            payments = ScheduledPayment.objects.filter(
                id__in=payment_ids, schedule=schedule
            )
            
            updated_count = process_bulk_update(payments, update_type, form.cleaned_data)
            
            messages.success(request, f'{updated_count} payments updated successfully.')
            return redirect('loans_schedule:schedule_detail', pk=schedule.pk)
    else:
        form = BulkPaymentUpdateForm()
    
    return render(request, 'loans_schedule/bulk_payment_update.html', {
        'form': form,
        'schedule': schedule,
        'title': 'Bulk Update Payments',
    })


# AJAX Views
@login_required
def calculate_payment_schedule(request):
    """Calculate payment schedule for AJAX requests"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            principal = Decimal(str(data.get('principal', 0)))
            annual_rate = Decimal(str(data.get('annual_rate', 0)))
            months = int(data.get('months', 0))
            method = data.get('method', 'equal_payment')
            
            if principal > 0 and annual_rate >= 0 and months > 0:
                monthly_rate = annual_rate / 100 / 12
                
                if method == 'equal_payment' and monthly_rate > 0:
                    # Standard amortization formula
                    monthly_payment = principal * (monthly_rate * (1 + monthly_rate)**months) / ((1 + monthly_rate)**months - 1)
                elif method == 'equal_principal':
                    monthly_payment = principal / months + (principal * monthly_rate)
                elif method == 'interest_only':
                    monthly_payment = principal * monthly_rate
                else:
                    monthly_payment = Decimal('0')
                
                return JsonResponse({
                    'success': True,
                    'monthly_payment': float(monthly_payment),
                    'total_payment': float(monthly_payment * months),
                    'total_interest': float((monthly_payment * months) - principal),
                })
            else:
                return JsonResponse({'success': False, 'error': 'Invalid parameters'})
        except (ValueError, TypeError, KeyError):
            return JsonResponse({'success': False, 'error': 'Invalid data'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def get_payment_schedule_data(request, pk):
    """Get payment schedule data for charts and tables"""
    user_company = get_user_company(request.user)
    schedule = get_object_or_404(PaymentSchedule, pk=pk, company=user_company)
    
    payments = ScheduledPayment.objects.filter(schedule=schedule).order_by('payment_number')
    
    payment_data = []
    for payment in payments:
        payment_data.append({
            'payment_number': payment.payment_number,
            'due_date': payment.due_date.isoformat(),
            'principal_amount': float(payment.principal_amount),
            'interest_amount': float(payment.interest_amount),
            'total_amount': float(payment.total_amount),
            'is_paid': payment.is_paid,
            'remaining_balance': float(payment.remaining_balance),
        })
    
    return JsonResponse({
        'success': True,
        'schedule': {
            'id': schedule.pk,
            'loan_number': schedule.loan.loan_number,
            'total_payments': schedule.total_payments,
            'payment_frequency': schedule.payment_frequency,
        },
        'payments': payment_data,
    })


# Helper functions
def generate_scheduled_payments(schedule):
    """Generate scheduled payments for a payment schedule"""
    loan = schedule.loan
    principal = loan.current_balance
    annual_rate = loan.interest_rate
    monthly_rate = annual_rate / 100 / 12
    
    current_date = schedule.start_date
    remaining_balance = principal
    
    for payment_num in range(1, schedule.total_payments + 1):
        if schedule.schedule_type == 'equal_payment':
            interest_amount = remaining_balance * monthly_rate
            principal_amount = schedule.payment_amount - interest_amount
        elif schedule.schedule_type == 'equal_principal':
            principal_amount = principal / schedule.total_payments
            interest_amount = remaining_balance * monthly_rate
        else:  # interest_only
            if payment_num < schedule.total_payments:
                interest_amount = remaining_balance * monthly_rate
                principal_amount = Decimal('0')
            else:  # Final balloon payment
                interest_amount = remaining_balance * monthly_rate
                principal_amount = remaining_balance
        
        total_amount = principal_amount + interest_amount
        remaining_balance -= principal_amount
        
        ScheduledPayment.objects.create(
            company=schedule.company,
            schedule=schedule,
            payment_number=payment_num,
            due_date=current_date,
            principal_amount=principal_amount,
            interest_amount=interest_amount,
            total_amount=total_amount,
            remaining_balance=remaining_balance,
            created_by=schedule.created_by
        )
        
        # Calculate next payment date
        current_date = calculate_next_payment_date(current_date, schedule.payment_frequency)


def generate_advanced_payments(schedule, method, form_data):
    """Generate payments using advanced calculation methods"""
    loan = schedule.loan
    principal = loan.current_balance
    annual_rate = loan.interest_rate
    
    if method == 'custom':
        payment_amount = form_data['custom_payment_amount']
        # Calculate number of payments needed
        monthly_rate = annual_rate / 100 / 12
        if monthly_rate > 0:
            months = -(Decimal(1) / 12) * Decimal(str(monthly_rate)).ln() / Decimal(str(1 + monthly_rate)).ln()
            schedule.total_payments = int(months) + 1
        else:
            schedule.total_payments = int(principal / payment_amount)
        schedule.payment_amount = payment_amount
    else:
        # Use standard calculation
        schedule.total_payments = loan.term_months
        if method == 'equal_payment':
            monthly_rate = annual_rate / 100 / 12
            if monthly_rate > 0:
                schedule.payment_amount = principal * (monthly_rate * (1 + monthly_rate)**loan.term_months) / ((1 + monthly_rate)**loan.term_months - 1)
            else:
                schedule.payment_amount = principal / loan.term_months
        elif method == 'equal_principal':
            schedule.payment_amount = principal / loan.term_months
    
    schedule.save()
    generate_scheduled_payments(schedule)


def calculate_next_payment_date(current_date, frequency):
    """Calculate the next payment date based on frequency"""
    if frequency == 'weekly':
        return current_date + timedelta(weeks=1)
    elif frequency == 'bi_weekly':
        return current_date + timedelta(weeks=2)
    elif frequency == 'monthly':
        # Add one month
        if current_date.month == 12:
            return current_date.replace(year=current_date.year + 1, month=1)
        else:
            try:
                return current_date.replace(month=current_date.month + 1)
            except ValueError:
                # Handle month-end dates
                last_day = calendar.monthrange(current_date.year, current_date.month + 1)[1]
                return current_date.replace(month=current_date.month + 1, day=min(current_date.day, last_day))
    elif frequency == 'quarterly':
        # Add three months
        month = current_date.month + 3
        year = current_date.year
        if month > 12:
            month -= 12
            year += 1
        try:
            return current_date.replace(year=year, month=month)
        except ValueError:
            last_day = calendar.monthrange(year, month)[1]
            return current_date.replace(year=year, month=month, day=min(current_date.day, last_day))
    else:  # annual
        try:
            return current_date.replace(year=current_date.year + 1)
        except ValueError:
            # Handle leap year edge case
            return current_date.replace(year=current_date.year + 1, day=28)


def process_bulk_update(payments, update_type, form_data):
    """Process bulk update of scheduled payments"""
    updated_count = 0
    
    for payment in payments:
        if update_type == 'adjust_amount':
            if form_data.get('adjustment_amount'):
                payment.total_amount += form_data['adjustment_amount']
                payment.principal_amount += form_data['adjustment_amount']
            elif form_data.get('adjustment_percentage'):
                adjustment = payment.total_amount * (form_data['adjustment_percentage'] / 100)
                payment.total_amount += adjustment
                payment.principal_amount += adjustment
        
        elif update_type == 'reschedule_dates':
            payment.due_date += timedelta(days=form_data['date_offset_days'])
        
        elif update_type == 'mark_paid':
            payment.is_paid = True
            payment.paid_date = timezone.now().date()
        
        elif update_type == 'mark_unpaid':
            payment.is_paid = False
            payment.paid_date = None
        
        if form_data.get('notes'):
            payment.notes = form_data['notes']
        
        payment.save()
        updated_count += 1
    
    return updated_count
