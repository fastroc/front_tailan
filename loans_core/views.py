"""
Views for loan core functionality
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Prefetch
from django.http import JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator
from decimal import Decimal
import json

from .models import LoanProduct, LoanApplication, Loan
from company.models import Company
from .forms import (
    LoanProductForm, LoanApplicationApprovalForm,
    QuickLoanApplicationForm, LoanDisbursementForm
)
from loans_customers.models import Customer


def get_user_company(user):
    """Helper function to get user's company"""
    # For now, just return the first company since UserProfile doesn't have company relationships
    return Company.objects.first()


@login_required
def loan_dashboard(request):
    """100% Dynamic loan dashboard with real-time statistics from database"""
    user_company = get_user_company(request.user)
    
    # Get real statistics from database
    today = timezone.now().date()
    
    # Calculate REAL statistics - NO MOCK DATA
    total_customers = Customer.objects.filter(company=user_company).count()
    active_loans_count = Loan.objects.filter(company=user_company, status__in=['active', 'current', 'disbursed']).count()
    pending_applications_count = LoanApplication.objects.filter(
        company=user_company, status__in=['pending', 'under_review', 'submitted']
    ).count()
    approved_applications_count = LoanApplication.objects.filter(
        company=user_company, status='approved'
    ).count()
    
    # Portfolio calculations - REAL DATA
    total_portfolio = Loan.objects.filter(
        company=user_company, status__in=['active', 'current', 'disbursed']
    ).aggregate(total=Sum('principal_amount'))['total'] or Decimal('0.00')
    
    total_outstanding = Loan.objects.filter(
        company=user_company, status__in=['active', 'current', 'disbursed']
    ).aggregate(total=Sum('current_balance'))['total'] or Decimal('0.00')
    
    # Overdue calculations - REAL DATA
    overdue_loans = Loan.objects.filter(
        company=user_company, 
        status__in=['active', 'current'],
        next_payment_date__lt=today
    )
    overdue_amount = overdue_loans.aggregate(total=Sum('current_balance'))['total'] or Decimal('0.00')
    overdue_count = overdue_loans.count()
    
    # Monthly disbursements (current month) - REAL DATA
    monthly_disbursements = Loan.objects.filter(
        company=user_company,
        disbursement_date__year=today.year,
        disbursement_date__month=today.month,
        status__in=['active', 'current', 'disbursed']
    ).aggregate(total=Sum('principal_amount'))['total'] or Decimal('0.00')
    
    monthly_disbursements_count = Loan.objects.filter(
        company=user_company,
        disbursement_date__year=today.year,
        disbursement_date__month=today.month
    ).count()
    
    # Collection rate calculation - REAL DATA
    from loans_payments.models import Payment
    total_payments_received = Payment.objects.filter(
        company=user_company,
        status='completed'
    ).aggregate(total=Sum('payment_amount'))['total'] or Decimal('0.00')
    
    if total_portfolio > 0:
        collection_rate = Decimal(str(total_payments_received / total_portfolio * 100)).quantize(Decimal('0.1'))
    else:
        collection_rate = Decimal('0.0')
    
    # Average loan size - REAL DATA
    if active_loans_count > 0:
        avg_loan_size = (total_portfolio / active_loans_count).quantize(Decimal('0.01'))
    else:
        avg_loan_size = Decimal('0.00')
    
    # Application approval rate - REAL DATA
    total_applications = LoanApplication.objects.filter(company=user_company).count()
    if total_applications > 0:
        approval_rate = Decimal(str(approved_applications_count / total_applications * 100)).quantize(Decimal('0.1'))
    else:
        approval_rate = Decimal('0.0')
    
    # Real-time dynamic statistics
    stats = {
        'total_portfolio': total_portfolio,
        'active_loans': active_loans_count,
        'pending_applications': pending_applications_count,
        'approved_applications': approved_applications_count,
        'overdue_amount': overdue_amount,
        'overdue_count': overdue_count,
        'monthly_disbursements': monthly_disbursements,
        'monthly_disbursements_count': monthly_disbursements_count,
        'collection_rate': collection_rate,
        'approval_rate': approval_rate,
        'avg_loan_size': avg_loan_size,
        'total_customers': total_customers,
        'total_outstanding': total_outstanding,
        'total_payments_received': total_payments_received,
        'total_applications': total_applications,
    }
    
    # Get recent applications (REAL DATA ONLY)
    recent_applications = LoanApplication.objects.filter(
        company=user_company
    ).select_related('customer', 'loan_product').order_by('-application_date')[:5]
    
    # Get active loans (REAL DATA ONLY)
    active_loans = Loan.objects.filter(
        company=user_company, status__in=['active', 'current', 'disbursed']
    ).select_related('customer', 'loan_product').order_by('-disbursement_date')[:5]
    
    # Get recent payments for dashboard activity
    from loans_payments.models import Payment
    recent_payments = Payment.objects.filter(
        company=user_company
    ).select_related('loan', 'loan__customer').order_by('-payment_date')[:5]
    
    # Calculate growth metrics (month-over-month)
    from datetime import datetime, timedelta
    last_month = today.replace(day=1) - timedelta(days=1)
    
    # Last month's stats for comparison
    last_month_applications = LoanApplication.objects.filter(
        company=user_company,
        application_date__year=last_month.year,
        application_date__month=last_month.month
    ).count()
    
    last_month_disbursements = Loan.objects.filter(
        company=user_company,
        disbursement_date__year=last_month.year,
        disbursement_date__month=last_month.month
    ).aggregate(total=Sum('principal_amount'))['total'] or Decimal('0.00')
    
    # Growth calculations
    current_month_applications = LoanApplication.objects.filter(
        company=user_company,
        application_date__year=today.year,
        application_date__month=today.month
    ).count()
    
    if last_month_applications > 0:
        application_growth = Decimal(str((current_month_applications - last_month_applications) / last_month_applications * 100)).quantize(Decimal('0.1'))
    else:
        application_growth = Decimal('100.0') if current_month_applications > 0 else Decimal('0.0')
    
    if last_month_disbursements > 0:
        disbursement_growth = Decimal(str((monthly_disbursements - last_month_disbursements) / last_month_disbursements * 100)).quantize(Decimal('0.1'))
    else:
        disbursement_growth = Decimal('100.0') if monthly_disbursements > 0 else Decimal('0.0')
    
    # Add growth metrics to stats
    stats.update({
        'application_growth': application_growth,
        'disbursement_growth': disbursement_growth,
        'current_month_applications': current_month_applications,
        'last_month_applications': last_month_applications,
    })
    
    return render(request, 'loans_core/dashboard_enhanced.html', {
        'stats': stats,
        'recent_applications': recent_applications,
        'active_loans': active_loans,
        'recent_payments': recent_payments,
        'title': 'Dynamic Loan Management Dashboard',
        'company': user_company,
        'today_date': today,
        'is_dynamic': True,  # Flag to indicate 100% dynamic data
    })


@login_required
def loan_product_list(request):
    """List all loan products"""
    user_company = get_user_company(request.user)
    products = LoanProduct.objects.filter(company=user_company).order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(category__icontains=search_query)
        )
    
    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'loans_core/product_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
    })


@login_required
def loan_product_create(request):
    """Create a new loan product"""
    if request.method == 'POST':
        form = LoanProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.company = get_user_company(request.user)
            product.created_by = request.user
            product.save()
            messages.success(request, f'Loan product "{product.name}" created successfully.')
            return redirect('loans_core:product_list')
    else:
        form = LoanProductForm()
    
    return render(request, 'loans_core/product_form.html', {
        'form': form,
        'title': 'Create Loan Product',
    })


@login_required
def loan_product_edit(request, pk):
    """Edit a loan product"""
    user_company = get_user_company(request.user)
    product = get_object_or_404(LoanProduct, pk=pk, company=user_company)
    
    if request.method == 'POST':
        form = LoanProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save(commit=False)
            product.updated_by = request.user
            product.save()
            messages.success(request, f'Loan product "{product.name}" updated successfully.')
            return redirect('loans_core:product_list')
    else:
        form = LoanProductForm(instance=product)
    
    return render(request, 'loans_core/product_form.html', {
        'form': form,
        'product': product,
        'title': 'Edit Loan Product',
    })


@login_required
def loan_application_list(request):
    """List all loan applications with comprehensive statistics"""
    user_company = get_user_company(request.user)
    
    # Base queryset
    applications = LoanApplication.objects.filter(
        company=user_company
    ).select_related('customer', 'loan_product').order_by('-created_at')
    
    # Calculate comprehensive statistics
    all_applications = LoanApplication.objects.filter(company=user_company)
    stats = {
        'total_applications': all_applications.count(),
        'pending_applications': all_applications.filter(status__in=['submitted', 'under_review']).count(),
        'approved_applications': all_applications.filter(status='approved').count(),
        'rejected_applications': all_applications.filter(status='rejected').count(),
        'draft_applications': all_applications.filter(status='draft').count(),
        'cancelled_applications': all_applications.filter(status='cancelled').count(),
        'total_requested_amount': all_applications.aggregate(
            total=Sum('requested_amount')
        )['total'] or Decimal('0.00'),
        'total_approved_amount': all_applications.filter(
            status='approved'
        ).aggregate(total=Sum('approved_amount'))['total'] or Decimal('0.00'),
        'approval_rate': 0,
        'average_requested_amount': Decimal('0.00'),
    }
    
    # Calculate approval rate
    if stats['total_applications'] > 0:
        stats['approval_rate'] = round(
            (stats['approved_applications'] / stats['total_applications']) * 100, 1
        )
    
    # Calculate average requested amount
    if stats['total_applications'] > 0:
        stats['average_requested_amount'] = stats['total_requested_amount'] / stats['total_applications']
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        applications = applications.filter(status=status_filter)
    
    # Filter by product
    product_filter = request.GET.get('product', '')
    if product_filter:
        applications = applications.filter(loan_product_id=product_filter)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        applications = applications.filter(
            Q(application_id__icontains=search_query) |
            Q(customer__first_name__icontains=search_query) |
            Q(customer__last_name__icontains=search_query) |
            Q(customer__email__icontains=search_query) |
            Q(customer__phone__icontains=search_query)
        )
    
    # Get loan products for filter dropdown
    loan_products = LoanProduct.objects.filter(company=user_company, is_active=True)
    
    # Pagination
    paginator = Paginator(applications, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'loans_core/application_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'product_filter': product_filter,
        'status_choices': LoanApplication.APPLICATION_STATUS,
        'loan_products': loan_products,
        'stats': stats,
        # Individual stats for template backwards compatibility
        'total_applications': stats['total_applications'],
        'pending_applications': stats['pending_applications'],
        'approved_applications': stats['approved_applications'],
        'rejected_applications': stats['rejected_applications'],
    })


@login_required
def loan_application_create(request):
    """Create a new loan application"""
    user_company = get_user_company(request.user)
    
    if request.method == 'POST':
        form = QuickLoanApplicationForm(request.POST, company=user_company)
        if form.is_valid():
            # Create or get customer
            customer = form.cleaned_data.get('existing_customer')
            if not customer:
                # Create new customer
                customer = Customer.objects.create(
                    company=user_company,
                    customer_type=form.cleaned_data['customer_type'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    email=form.cleaned_data['email'],
                    phone_primary=form.cleaned_data['phone_primary'],
                    national_id=form.cleaned_data['national_id'],
                    monthly_income=form.cleaned_data['monthly_income'],
                    is_active=True,
                    created_by=request.user
                )
            
            # Create loan application
            application = LoanApplication.objects.create(
                company=user_company,
                customer=customer,
                loan_product=form.cleaned_data['loan_product'],
                requested_amount=form.cleaned_data['requested_amount'],
                term_months=form.cleaned_data['term_months'],
                interest_rate=form.cleaned_data['loan_product'].default_interest_rate,
                purpose=form.cleaned_data['purpose'],
                status='submitted',
                application_date=timezone.now().date(),
                created_by=request.user
            )
            
            messages.success(request, f'Loan application {application.application_id} created successfully.')
            return redirect('loans_core:application_detail', pk=application.pk)
        else:
            # Add form errors to messages for debugging
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = QuickLoanApplicationForm(company=user_company)
    
    return render(request, 'loans_core/application_form.html', {
        'form': form,
        'title': 'New Loan Application',
    })


@login_required
def loan_application_detail(request, pk):
    """View loan application details"""
    user_company = get_user_company(request.user)
    application = get_object_or_404(
        LoanApplication.objects.select_related('customer', 'loan_product'),
        pk=pk, company=user_company
    )
    
    return render(request, 'loans_core/application_detail.html', {
        'application': application,
    })


@login_required
def loan_application_approve(request, pk):
    """Approve or reject a loan application with full contract creation and schedule storage"""
    from decimal import Decimal
    import datetime
    import json
    from django.utils import timezone
    from loans_schedule.models import PaymentSchedule, ScheduledPayment
    
    user_company = get_user_company(request.user)
    application = get_object_or_404(LoanApplication, pk=pk, company=user_company)
    
    if request.method == 'POST':
        action = request.POST.get('action', '')
        
        if action == 'approve':
            # Extract approval data from POST
            try:
                approved_amount = Decimal(request.POST.get('approved_amount', '0'))
                interest_rate = Decimal(request.POST.get('interest_rate', '0'))
                term_months = int(request.POST.get('term_months', '0'))
                schedule_type = request.POST.get('schedule_type', 'equal-total')
                schedule_data_json = request.POST.get('schedule_data', '[]')
                
                # Parse dates
                disbursement_date = datetime.datetime.strptime(
                    request.POST.get('disbursement_date'), '%Y-%m-%d'
                ).date()
                first_payment_date = datetime.datetime.strptime(
                    request.POST.get('first_payment_date'), '%Y-%m-%d'
                ).date()
                
                # Optional fields
                notes = request.POST.get('notes', '')
                
                # Parse schedule data
                schedule_data = []
                if schedule_data_json and schedule_data_json != '[]':
                    try:
                        schedule_data = json.loads(schedule_data_json)
                        print(f"DEBUG: Received schedule_data: {len(schedule_data)} payments")
                        if schedule_data:
                            print(f"DEBUG: First payment: {schedule_data[0]}")
                            print(f"DEBUG: Last payment: {schedule_data[-1]}")
                    except json.JSONDecodeError:
                        messages.error(request, 'Invalid schedule data format.')
                        return redirect('loans_core:application_approve', pk=pk)
                else:
                    print("DEBUG: No schedule data received, using standard calculation")
                
                # Validate basic fields
                if approved_amount <= 0 or interest_rate < 0 or term_months <= 0:
                    messages.error(request, 'Invalid loan parameters.')
                    return redirect('loans_core:application_approve', pk=pk)
                
                # Convert schedule_type from frontend format to database format
                db_schedule_type = 'equal_payment' if schedule_type == 'equal-total' else 'equal_principal'
                
                # Calculate maturity date
                maturity_date = first_payment_date
                months_added = 0
                while months_added < term_months - 1:
                    if maturity_date.month == 12:
                        maturity_date = maturity_date.replace(year=maturity_date.year + 1, month=1)
                    else:
                        maturity_date = maturity_date.replace(month=maturity_date.month + 1)
                    months_added += 1
                
                # Calculate average monthly payment from schedule data or formula
                if schedule_data:
                    total_payments = sum(Decimal(str(payment.get('payment', 0))) for payment in schedule_data)
                    monthly_payment = total_payments / len(schedule_data) if schedule_data else Decimal('0')
                else:
                    # Calculate using standard formula
                    monthly_rate = interest_rate / Decimal('100') / Decimal('12')
                    if monthly_rate > 0:
                        monthly_payment = approved_amount * (
                            monthly_rate * (1 + monthly_rate) ** term_months
                        ) / ((1 + monthly_rate) ** term_months - 1)
                    else:
                        monthly_payment = approved_amount / term_months
                
                # Update application
                application.status = 'approved'
                application.approved_amount = approved_amount
                application.interest_rate = interest_rate
                application.term_months = term_months
                application.repayment_method = db_schedule_type
                application.approval_date = timezone.now().date()
                application.disbursement_date = disbursement_date
                application.first_payment_date = first_payment_date
                application.notes = notes
                application.updated_by = request.user
                
                # Store the custom schedule configuration if provided
                if schedule_data:
                    application.custom_schedule_config = {
                        'schedule_type': schedule_type,
                        'calculated_schedule': schedule_data,
                        'total_payments': len(schedule_data),
                        'total_amount': float(sum(Decimal(str(p.get('payment', 0))) for p in schedule_data)),
                        'total_interest': float(sum(Decimal(str(p.get('interest', 0))) for p in schedule_data)),
                        'total_principal': float(sum(Decimal(str(p.get('principal', 0))) for p in schedule_data))
                    }
                
                application.save()
                
                # Create or update loan record
                existing_loan = None
                try:
                    existing_loan = Loan.objects.get(application=application)
                except Loan.DoesNotExist:
                    pass
                
                if existing_loan:
                    # Update existing loan with new terms
                    existing_loan.principal_amount = approved_amount
                    existing_loan.current_balance = approved_amount
                    existing_loan.interest_rate = interest_rate
                    existing_loan.term_months = term_months
                    existing_loan.monthly_payment = monthly_payment
                    existing_loan.disbursement_date = disbursement_date
                    existing_loan.first_payment_date = first_payment_date
                    existing_loan.maturity_date = maturity_date
                    existing_loan.next_payment_date = first_payment_date
                    existing_loan.payments_remaining = term_months
                    existing_loan.updated_by = request.user
                    existing_loan.save()
                    loan = existing_loan
                else:
                    # Create new loan record
                    loan = Loan.objects.create(
                    company=user_company,
                    application=application,
                    customer=application.customer,
                    loan_product=application.loan_product,
                    principal_amount=approved_amount,
                    current_balance=approved_amount,
                    interest_rate=interest_rate,
                    term_months=term_months,
                    monthly_payment=monthly_payment,
                    disbursement_date=disbursement_date,
                    first_payment_date=first_payment_date,
                    maturity_date=maturity_date,
                    next_payment_date=first_payment_date,
                    payments_remaining=term_months,
                    status='active',
                    created_by=request.user
                )
                
                # Create payment schedule master record
                has_custom_schedule = schedule_data and len(schedule_data) > 0
                if has_custom_schedule:
                    total_interest = sum(Decimal(str(p.get('interest', 0))) for p in schedule_data)
                    total_amount = sum(Decimal(str(p.get('payment', 0))) for p in schedule_data)
                    print(f"DEBUG: Using custom schedule - {len(schedule_data)} payments, total: ${total_amount}")
                else:
                    total_interest = (monthly_payment * term_months) - approved_amount
                    total_amount = monthly_payment * term_months
                    print(f"DEBUG: Using standard calculation - monthly: ${monthly_payment}, total: ${total_amount}")
                
                # Delete existing payment schedule and payments if they exist
                try:
                    existing_schedule = PaymentSchedule.objects.get(loan=loan)
                    # Delete all scheduled payments first
                    from loans_schedule.models import ScheduledPayment
                    ScheduledPayment.objects.filter(payment_schedule=existing_schedule).delete()
                    # Delete the payment schedule
                    existing_schedule.delete()
                    print(f"DEBUG: Deleted existing payment schedule for loan {loan.loan_number}")
                except PaymentSchedule.DoesNotExist:
                    pass
                
                payment_schedule = PaymentSchedule.objects.create(
                    company=user_company,
                    loan=loan,
                    schedule_type=db_schedule_type,
                    payment_frequency='monthly',
                    total_payments=term_months,
                    total_principal=approved_amount,
                    total_interest=total_interest,
                    total_amount=total_amount,
                    status='active',
                    created_by=request.user
                )
                
                # Create individual scheduled payments
                if has_custom_schedule:
                    # Use the calculated schedule from frontend
                    print(f"DEBUG: Creating {len(schedule_data)} custom scheduled payments")
                    for i, payment_data in enumerate(schedule_data):
                        # Parse payment data safely
                        principal_amount = Decimal(str(payment_data.get('principal', 0)))
                        interest_amount = Decimal(str(payment_data.get('interest', 0)))
                        payment_amount = Decimal(str(payment_data.get('payment', 0)))
                        balance = Decimal(str(payment_data.get('balance', 0)))
                        
                        # Parse due date from schedule data or calculate
                        due_date = first_payment_date
                        if payment_data.get('date'):
                            try:
                                # Try to parse the date from schedule data
                                import datetime
                                due_date = datetime.datetime.strptime(payment_data['date'], '%Y-%m-%d').date()
                            except (ValueError, KeyError):
                                # Fall back to calculated date
                                due_date = first_payment_date
                                months_to_add = i
                                while months_to_add > 0:
                                    if due_date.month == 12:
                                        due_date = due_date.replace(year=due_date.year + 1, month=1)
                                    else:
                                        due_date = due_date.replace(month=due_date.month + 1)
                                    months_to_add -= 1
                        else:
                            # Calculate due date based on payment number
                            due_date = first_payment_date
                            months_to_add = i
                            while months_to_add > 0:
                                if due_date.month == 12:
                                    due_date = due_date.replace(year=due_date.year + 1, month=1)
                                else:
                                    due_date = due_date.replace(month=due_date.month + 1)
                                months_to_add -= 1
                        
                        # Calculate beginning balance
                        if i == 0:
                            beginning_balance = approved_amount
                        else:
                            beginning_balance = Decimal(str(schedule_data[i-1].get('balance', 0)))
                        
                        ScheduledPayment.objects.create(
                            company=user_company,
                            payment_schedule=payment_schedule,
                            loan=loan,
                            payment_number=i + 1,
                            due_date=due_date,
                            principal_amount=principal_amount,
                            interest_amount=interest_amount,
                            total_amount=payment_amount,
                            beginning_balance=beginning_balance,
                            ending_balance=balance,
                            is_custom_amount=True,  # Mark as custom since user edited principals
                            status='scheduled',
                            created_by=request.user
                        )
                
                else:
                    # Generate standard schedule
                    monthly_rate = interest_rate / Decimal('100') / Decimal('12')
                    current_date = first_payment_date
                    remaining_balance = approved_amount
                    
                    for payment_num in range(1, term_months + 1):
                        if db_schedule_type == 'equal_payment':
                            # Equal payment calculation
                            interest_amount = remaining_balance * monthly_rate
                            principal_amount = monthly_payment - interest_amount
                        else:
                            # Equal principal calculation
                            principal_amount = approved_amount / term_months
                            interest_amount = remaining_balance * monthly_rate
                            payment_amount = principal_amount + interest_amount
                        
                        beginning_balance = remaining_balance
                        remaining_balance -= principal_amount
                        
                        # Ensure final payment zeroes out balance
                        if payment_num == term_months:
                            remaining_balance = Decimal('0.00')
                        
                        ScheduledPayment.objects.create(
                            company=user_company,
                            payment_schedule=payment_schedule,
                            loan=loan,
                            payment_number=payment_num,
                            due_date=current_date,
                            principal_amount=principal_amount,
                            interest_amount=interest_amount,
                            total_amount=principal_amount + interest_amount,
                            beginning_balance=beginning_balance,
                            ending_balance=max(remaining_balance, Decimal('0.00')),
                            status='scheduled',
                            created_by=request.user
                        )
                        
                        # Move to next month
                        if current_date.month == 12:
                            current_date = current_date.replace(year=current_date.year + 1, month=1)
                        else:
                            current_date = current_date.replace(month=current_date.month + 1)
                
                messages.success(
                    request, 
                    f'Application approved! Loan {loan.loan_number} created with {payment_schedule.total_payments} scheduled payments. '
                    f'Disbursement scheduled for {disbursement_date}.'
                )
                return redirect('loans_core:loan_detail', pk=loan.pk)
                
            except (ValueError, TypeError, KeyError) as e:
                messages.error(request, f'Error processing approval: {str(e)}')
                return redirect('loans_core:application_approve', pk=pk)
        
        elif action == 'reject':
            # Handle rejection
            rejection_reason = request.POST.get('rejection_reason', '')
            notes = request.POST.get('notes', '')
            
            if not rejection_reason.strip():
                messages.error(request, 'Rejection reason is required.')
                return redirect('loans_core:application_approve', pk=pk)
            
            application.status = 'rejected'
            application.rejection_reason = rejection_reason
            application.notes = notes
            application.updated_by = request.user
            application.save()
            
            messages.success(request, f'Application {application.application_id} has been rejected.')
            return redirect('loans_core:application_detail', pk=application.pk)
        
        else:
            # Handle legacy form submission
            form = LoanApplicationApprovalForm(request.POST, instance=application)
            if form.is_valid():
                application = form.save(commit=False)
                application.updated_by = request.user
                application.save()
                
                # If approved, create basic loan
                if application.status == 'approved':
                    loan = Loan.objects.create(
                        company=user_company,
                        application=application,
                        customer=application.customer,
                        loan_product=application.loan_product,
                        principal_amount=application.approved_amount or application.requested_amount,
                        current_balance=application.approved_amount or application.requested_amount,
                        interest_rate=application.interest_rate,
                        term_months=application.term_months,
                        monthly_payment=Decimal('100.00'),  # Default, will be calculated
                        disbursement_date=timezone.now().date(),
                        first_payment_date=timezone.now().date() + datetime.timedelta(days=30),
                        maturity_date=timezone.now().date() + datetime.timedelta(days=30*application.term_months),
                        next_payment_date=timezone.now().date() + datetime.timedelta(days=30),
                        payments_remaining=application.term_months,
                        status='active',
                        created_by=request.user
                    )
                    messages.success(request, f'Application approved and loan {loan.loan_number} created.')
                    return redirect('loans_core:loan_detail', pk=loan.pk)
                else:
                    messages.success(request, f'Application {application.application_id} updated.')
                    return redirect('loans_core:application_detail', pk=application.pk)
    else:
        form = LoanApplicationApprovalForm(instance=application)
    
    # Check if loan already exists for this application
    existing_loan = None
    try:
        existing_loan = Loan.objects.get(application=application)
    except Loan.DoesNotExist:
        pass
    
    return render(request, 'loans_core/application_approval.html', {
        'form': form,
        'application': application,
        'existing_loan': existing_loan,
    })


@login_required
def loan_application_delete(request, pk):
    """Delete a loan application"""
    from django.http import JsonResponse
    
    user_company = get_user_company(request.user)
    
    try:
        application = get_object_or_404(LoanApplication, pk=pk, company=user_company)
        
        # Define deletable statuses
        deletable_statuses = ['draft', 'submitted', 'rejected', 'cancelled']
        
        # Check if application status allows deletion
        if application.status not in deletable_statuses:
            return JsonResponse({
                'success': False,
                'error': f'Cannot delete application with status "{application.get_status_display()}". Only draft, submitted, rejected, and cancelled applications can be deleted.'
            })
        
        # Additional check for approved applications with loans
        if application.status == 'approved':
            try:
                Loan.objects.get(application=application)
                return JsonResponse({
                    'success': False,
                    'error': 'Cannot delete approved application with active loan. Please handle the loan first.'
                })
            except Loan.DoesNotExist:
                pass
        
        if request.method == 'POST':
            customer_name = application.customer.full_name
            application_id = application.application_id
            
            # Delete the application
            application.delete()
            
            messages.success(request, f'Loan application {application_id} for {customer_name} has been deleted successfully.')
            
            return JsonResponse({
                'success': True,
                'message': f'Application {application_id} for {customer_name} deleted successfully.'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid request method. Use POST to delete.'
            })
            
    except LoanApplication.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Loan application not found.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'An error occurred while deleting the application: {str(e)}'
        })


@login_required
def loan_list(request):
    """List all loans"""
    user_company = get_user_company(request.user)
    loans = Loan.objects.filter(
        company=user_company
    ).select_related('customer', 'loan_product').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        loans = loans.filter(status=status_filter)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        loans = loans.filter(
            Q(loan_number__icontains=search_query) |
            Q(customer__first_name__icontains=search_query) |
            Q(customer__last_name__icontains=search_query) |
            Q(customer__email__icontains=search_query)
        )
    
    paginator = Paginator(loans, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'loans_core/loan_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': Loan.LOAN_STATUS,
    })


@login_required
def loan_detail(request, pk):
    """View loan details with payment schedule"""
    from loans_schedule.models import PaymentSchedule, ScheduledPayment
    
    user_company = get_user_company(request.user)
    loan = get_object_or_404(
        Loan.objects.select_related('customer', 'loan_product', 'application'),
        pk=pk, company=user_company
    )
    
    # Get payment schedule for this loan
    payment_schedule = None
    scheduled_payments = []
    
    try:
        payment_schedule = PaymentSchedule.objects.get(loan=loan, company=user_company)
        scheduled_payments = ScheduledPayment.objects.filter(
            payment_schedule=payment_schedule,
            company=user_company
        ).order_by('payment_number')
    except PaymentSchedule.DoesNotExist:
        pass
    
    # Calculate summary statistics
    total_payments_due = scheduled_payments.count()
    total_amount_due = sum(payment.total_amount for payment in scheduled_payments)
    total_principal = sum(payment.principal_amount for payment in scheduled_payments)
    total_interest = sum(payment.interest_amount for payment in scheduled_payments)
    
    context = {
        'loan': loan,
        'payment_schedule': payment_schedule,
        'scheduled_payments': scheduled_payments,
        'payment_summary': {
            'total_payments': total_payments_due,
            'total_amount': total_amount_due,
            'total_principal': total_principal,
            'total_interest': total_interest,
        }
    }
    
    return render(request, 'loans_core/loan_detail.html', context)


@login_required
def loan_disburse(request, pk):
    """Disburse an approved loan"""
    user_company = get_user_company(request.user)
    loan = get_object_or_404(Loan, pk=pk, company=user_company, status='approved')
    
    if request.method == 'POST':
        form = LoanDisbursementForm(request.POST, instance=loan)
        if form.is_valid():
            loan = form.save(commit=False)
            loan.status = 'active'
            loan.updated_by = request.user
            loan.save()
            
            messages.success(request, f'Loan {loan.loan_number} disbursed successfully.')
            return redirect('loans_core:loan_detail', pk=loan.pk)
    else:
        form = LoanDisbursementForm(instance=loan)
        # Set default dates
        form.fields['disbursement_date'].initial = timezone.now().date()
    
    return render(request, 'loans_core/loan_disbursement.html', {
        'form': form,
        'loan': loan,
    })


# Legacy showcase views for backward compatibility
@login_required
def showcase_dashboard(request):
    """Redirect to new dashboard"""
    return redirect('loans_core:dashboard')

@login_required
def showcase_applications(request):
    """Demo applications page - respects active company session"""
    from company.models import Company
    
    # Get company from session (same logic as reconciliation system)
    company_id = request.session.get('active_company_id')
    
    if company_id:
        try:
            user_company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            user_company = Company.objects.first()
            if user_company:
                request.session['active_company_id'] = user_company.id
    else:
        # Default to first company and set session
        user_company = Company.objects.first()
        if user_company:
            request.session['active_company_id'] = user_company.id
    
    if not user_company:
        return render(request, 'loans_core/application_list.html', {
            'page_obj': [],
            'stats': {
                'total_applications': 0,
                'pending_applications': 0,
                'approved_applications': 0,
                'rejected_applications': 0,
            }
        })
    
    # Optimized queryset with prefetching
    applications = LoanApplication.objects.filter(
        company=user_company
    ).select_related(
        'customer', 
        'loan_product'
    ).prefetch_related(
        'loan',  # Prefetch loan relationship
        'loan__payments'  # Prefetch payments for progress calculation (fixed: payments not payment_set)
    ).order_by('-created_at')
    
    # Add loan number and approval progress information to each application
    applications_with_loans = []
    for app in applications:
        loan_info = None
        progress_info = app.get_approval_progress()  # Use new method
        
        try:
            # Try to find the loan created from this application
            loan = Loan.objects.get(
                customer=app.customer,
                company=app.company,
                principal_amount=app.approved_amount or app.requested_amount
            )
            loan_info = {
                'loan_number': loan.loan_number,
                'status': loan.status,
                'current_balance': loan.current_balance
            }
        except (Loan.DoesNotExist, Loan.MultipleObjectsReturned):
            loan_info = None
        
        applications_with_loans.append({
            'application': app,
            'loan': loan_info,
            'progress': progress_info  # Add progress information
        })
    
    # Calculate comprehensive statistics
    all_applications = LoanApplication.objects.filter(company=user_company)
    stats = {
        'total_applications': all_applications.count(),
        'pending_applications': all_applications.filter(status__in=['submitted', 'under_review']).count(),
        'approved_applications': all_applications.filter(status='approved').count(),
        'rejected_applications': all_applications.filter(status='rejected').count(),
        'draft_applications': all_applications.filter(status='draft').count(),
        'cancelled_applications': all_applications.filter(status='cancelled').count(),
        'total_requested_amount': all_applications.aggregate(
            total=Sum('requested_amount')
        )['total'] or Decimal('0.00'),
        'total_approved_amount': all_applications.filter(
            status='approved'
        ).aggregate(total=Sum('approved_amount'))['total'] or Decimal('0.00'),
        'approval_rate': 0,
        'average_requested_amount': Decimal('0.00'),
    }
    
    # Calculate approval rate
    if stats['total_applications'] > 0:
        stats['approval_rate'] = round(
            (stats['approved_applications'] / stats['total_applications']) * 100, 1
        )
        stats['average_requested_amount'] = stats['total_requested_amount'] / stats['total_applications']
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    progress_filter = request.GET.get('progress')  # New progress filter
    
    if status_filter:
        applications = applications.filter(status=status_filter)
    
    # Re-create applications_with_loans after filtering
    applications_with_loans = []
    for app in applications:
        loan_info = None
        progress_info = app.get_approval_progress()
        
        # Apply progress filter
        if progress_filter and progress_filter != progress_info['status']:
            continue
        
        try:
            loan = Loan.objects.get(
                customer=app.customer,
                company=app.company,
                principal_amount=app.approved_amount or app.requested_amount
            )
            loan_info = {
                'loan_number': loan.loan_number,
                'status': loan.status,
                'current_balance': loan.current_balance
            }
        except (Loan.DoesNotExist, Loan.MultipleObjectsReturned):
            loan_info = None
        
        applications_with_loans.append({
            'application': app,
            'loan': loan_info,
            'progress': progress_info
        })

    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        applications = applications.filter(
            Q(customer__first_name__icontains=search_query) |
            Q(customer__last_name__icontains=search_query) |
            Q(application_id__icontains=search_query)
        )
        
        # Re-create applications_with_loans after search filtering
        filtered_applications_with_loans = []
        for item in applications_with_loans:
            app = item['application']
            if (search_query.lower() in app.customer.first_name.lower() or
                search_query.lower() in app.customer.last_name.lower() or
                search_query.lower() in app.application_id.lower()):
                filtered_applications_with_loans.append(item)
        
        applications_with_loans = filtered_applications_with_loans

    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(applications_with_loans, 25)  # Show 25 applications per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'loans_core/application_list.html', {
        'page_obj': page_obj,
        'applications': page_obj,
        'stats': stats,
        'search_query': search_query,
        'status_filter': status_filter,
        'progress_filter': progress_filter,  # Add progress filter
        'total_applications': stats['total_applications'],
        'pending_applications': stats['pending_applications'],
        'approved_applications': stats['approved_applications'],
        'rejected_applications': stats['rejected_applications'],
        'title': 'Loan Applications Showcase',
    })
    
    # Calculate average requested amount
    if stats['total_applications'] > 0:
        stats['average_requested_amount'] = stats['total_requested_amount'] / stats['total_applications']
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        applications = applications.filter(status=status_filter)
    
    # Filter by product
    product_filter = request.GET.get('product', '')
    if product_filter:
        applications = applications.filter(loan_product_id=product_filter)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        applications = applications.filter(
            Q(application_id__icontains=search_query) |
            Q(customer__first_name__icontains=search_query) |
            Q(customer__last_name__icontains=search_query) |
            Q(customer__email__icontains=search_query) |
            Q(customer__phone__icontains=search_query)
        )
    
    # Get loan products for filter dropdown
    loan_products = LoanProduct.objects.filter(company=user_company, is_active=True)
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(applications, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'loans_core/application_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'product_filter': product_filter,
        'status_choices': LoanApplication.APPLICATION_STATUS,
        'loan_products': loan_products,
        'stats': stats,
        # Individual stats for template backwards compatibility
        'total_applications': stats['total_applications'],
        'pending_applications': stats['pending_applications'],
        'approved_applications': stats['approved_applications'],
        'rejected_applications': stats['rejected_applications'],
    })

@login_required
def showcase_customers(request):
    """Redirect to customers page"""
    return redirect('loans_customers:customer_list')

@login_required
def showcase_payments(request):
    """Redirect to payments page"""
    return redirect('loans_payments:payment_list')

@login_required
def loan_reports(request):
    """Enhanced loan reports and analytics dashboard with dynamic data"""
    user_company = get_user_company(request.user)
    from datetime import datetime, timedelta
    
    # Mock enhanced portfolio statistics for demo
    portfolio_stats = {
        'total_portfolio_value': Decimal('2450000.00'),
        'active_loans_count': 47,
        'total_customers': 89,
        'pending_applications': 12,
        'overdue_loans': 3,
        'avg_loan_amount': Decimal('52127.00'),
        'collection_rate': Decimal('94.5'),
        'default_rate': Decimal('1.8'),
        'monthly_growth': Decimal('8.2'),
        'ytd_disbursements': Decimal('1850000.00'),
        'portfolio_yield': Decimal('12.3'),
        'risk_score': Decimal('2.1'),  # Low risk = good
    }
    
    # Mock monthly performance data for charts
    monthly_data = [
        {'month': 'Jan', 'disbursements': 180000, 'collections': 165000, 'applications': 15},
        {'month': 'Feb', 'disbursements': 220000, 'collections': 178000, 'applications': 18},
        {'month': 'Mar', 'disbursements': 195000, 'collections': 189000, 'applications': 14},
        {'month': 'Apr', 'disbursements': 240000, 'collections': 198000, 'applications': 21},
        {'month': 'May', 'disbursements': 285000, 'collections': 225000, 'applications': 25},
        {'month': 'Jun', 'disbursements': 310000, 'collections': 245000, 'applications': 22},
        {'month': 'Jul', 'disbursements': 275000, 'collections': 268000, 'applications': 19},
        {'month': 'Aug', 'disbursements': 320000, 'collections': 285000, 'applications': 28},
        {'month': 'Sep', 'disbursements': 295000, 'collections': 298000, 'applications': 24},
    ]
    
    # Mock loan product performance
    product_performance = [
        {'name': 'Personal Loans', 'total_amount': 980000, 'count': 18, 'avg_rate': 14.5, 'status': 'excellent'},
        {'name': 'Business Loans', 'total_amount': 750000, 'count': 12, 'avg_rate': 12.8, 'status': 'good'},
        {'name': 'Auto Loans', 'total_amount': 520000, 'count': 11, 'avg_rate': 9.2, 'status': 'good'},
        {'name': 'Home Loans', 'total_amount': 200000, 'count': 6, 'avg_rate': 8.5, 'status': 'fair'},
    ]
    
    # Mock aging analysis
    aging_analysis = {
        'current': {'amount': 2100000, 'count': 44, 'percentage': 85.7},
        'days_1_30': {'amount': 250000, 'count': 2, 'percentage': 10.2},
        'days_31_60': {'amount': 75000, 'count': 1, 'percentage': 3.1},
        'days_61_90': {'amount': 25000, 'count': 0, 'percentage': 1.0},
        'over_90': {'amount': 0, 'count': 0, 'percentage': 0.0},
    }
    
    # Mock top performing customers
    top_customers = [
        {'name': 'ABC Corporation', 'total_borrowed': 150000, 'payments_made': 24, 'score': 'A+'},
        {'name': 'Smith Enterprises', 'total_borrowed': 125000, 'payments_made': 18, 'score': 'A'},
        {'name': 'Johnson Holdings', 'total_borrowed': 98000, 'payments_made': 15, 'score': 'A-'},
        {'name': 'Davis Manufacturing', 'total_borrowed': 87000, 'payments_made': 12, 'score': 'B+'},
        {'name': 'Wilson Group', 'total_borrowed': 75000, 'payments_made': 9, 'score': 'B'},
    ]
    
    # Risk metrics
    risk_metrics = {
        'high_risk_loans': 2,
        'medium_risk_loans': 5,
        'low_risk_loans': 40,
        'provision_coverage': Decimal('125.5'),
        'npl_ratio': Decimal('2.3'),
        'loss_rate': Decimal('0.8'),
    }
    
    # For real data, uncomment below and comment above:
    # portfolio_stats = {
    #     'total_portfolio_value': Loan.objects.filter(
    #         company=user_company
    #     ).aggregate(total=Sum('principal_amount'))['total'] or Decimal('0.00'),
    #     'active_loans_count': Loan.objects.filter(
    #         company=user_company, status='active'
    #     ).count(),
    #     'total_customers': Customer.objects.filter(
    #         company=user_company
    #     ).count(),
    #     'pending_applications': LoanApplication.objects.filter(
    #         company=user_company, status='pending'
    #     ).count(),
    #     'overdue_loans': Loan.objects.filter(
    #         company=user_company, days_overdue__gt=0
    #     ).count(),
    #     'avg_loan_amount': Loan.objects.filter(
    #         company=user_company
    #     ).aggregate(avg=Avg('principal_amount'))['avg'] or Decimal('0.00'),
    # }
    
    return render(request, 'loans_core/reports_enhanced.html', {
        'portfolio_stats': portfolio_stats,
        'monthly_data': monthly_data,
        'product_performance': product_performance,
        'aging_analysis': aging_analysis,
        'top_customers': top_customers,
        'risk_metrics': risk_metrics,
        'title': 'Loan Reports & Analytics',
        'company': user_company,
    })

@login_required
def showcase_reports(request):
    """Redirect to reports page"""
    return redirect('loans_core:reports')


# AJAX Views for dynamic functionality
@login_required
def get_loan_product_details(request, pk):
    """Get loan product details for AJAX requests"""
    user_company = get_user_company(request.user)
    try:
        product = LoanProduct.objects.get(pk=pk, company=user_company)
        return JsonResponse({
            'success': True,
            'data': {
                'min_amount': float(product.min_amount),
                'max_amount': float(product.max_amount),
                'min_term_months': product.min_term_months,
                'max_term_months': product.max_term_months,
                'default_interest_rate': float(product.default_interest_rate),
                'allows_prepayment': product.allows_prepayment,
            }
        })
    except LoanProduct.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Product not found'})


@login_required
def calculate_loan_payment(request):
    """Calculate loan payment for AJAX requests"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            principal = Decimal(str(data.get('principal', 0)))
            rate = Decimal(str(data.get('annual_rate', 0))) / 100 / 12  # Monthly rate
            months = int(data.get('months', 0))
            
            if principal > 0 and rate > 0 and months > 0:
                # Calculate monthly payment using loan formula
                monthly_payment = principal * (rate * (1 + rate)**months) / ((1 + rate)**months - 1)
                total_payment = monthly_payment * months
                total_interest = total_payment - principal
                
                return JsonResponse({
                    'success': True,
                    'monthly_payment': float(monthly_payment),
                    'total_payment': float(total_payment),
                    'total_interest': float(total_interest),
                })
            else:
                return JsonResponse({'success': False, 'error': 'Invalid parameters'})
        except (ValueError, TypeError, KeyError):
            return JsonResponse({'success': False, 'error': 'Invalid data'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def application_progress(request, pk):
    """Show payment progress for any application with sufficient data - Scheduled vs Actual Payments"""
    try:
        # Get the application
        application = LoanApplication.objects.select_related(
            'customer', 'loan_product', 'company'
        ).get(pk=pk)
        
        # Check if application has minimum required data for analysis
        if not (application.interest_rate and application.term_months and application.requested_amount):
            messages.error(request, 'This application does not have sufficient data for payment analysis.')
            return redirect('loans_core:application_detail', pk=pk)
        
        # For non-approved applications, show projected analysis
        is_approved = application.status == 'approved'
        
        # Try to find the associated loan (only for approved applications)
        loan = None
        if is_approved:
            try:
                loan = Loan.objects.select_related('customer').get(application=application)
            except Loan.DoesNotExist:
                # If no loan exists, show a message but still display what we can
                loan = None
        
        # Generate comprehensive payment analysis
        from loans_payments.models import Payment
        from loans_schedule.models import ScheduledPayment
        from datetime import datetime, timedelta
        import calendar
        
        # Create loan info for display
        loan_info = {
            'loan_number': loan.loan_number if loan else f'APP-{application.application_id}',
            'customer_name': f"{application.customer.first_name} {application.customer.last_name}",
            'principal_amount': application.approved_amount or application.requested_amount,
            'interest_rate': application.interest_rate,
            'term_months': application.term_months,
            'disbursement_date': loan.disbursement_date if loan else application.created_at.date(),
            'current_balance': loan.current_balance if loan else (application.approved_amount or application.requested_amount),
            'application_id': application.application_id,
            'loan_product': application.loan_product.name,
        }
        
        # Calculate scheduled payment plan
        monthly_rate = loan_info['interest_rate'] / Decimal('100') / Decimal('12')
        
        # Calculate monthly payment using loan payment formula
        if monthly_rate > 0:
            numerator = loan_info['principal_amount'] * monthly_rate * ((1 + monthly_rate) ** loan_info['term_months'])
            denominator = ((1 + monthly_rate) ** loan_info['term_months']) - 1
            monthly_payment = (numerator / denominator).quantize(Decimal('0.01'))
        else:
            monthly_payment = loan_info['principal_amount'] / loan_info['term_months']
        
        # Generate scheduled payment plan
        scheduled_payments = []
        remaining_balance = loan_info['principal_amount']
        payment_date = loan_info['disbursement_date'] + timedelta(days=30)
        
        for month in range(1, loan_info['term_months'] + 1):
            interest_portion = (remaining_balance * monthly_rate).quantize(Decimal('0.01'))
            principal_portion = monthly_payment - interest_portion
            
            if month == loan_info['term_months']:  # Last payment
                principal_portion = remaining_balance
                total_payment = principal_portion + interest_portion
            else:
                total_payment = monthly_payment
                
            remaining_balance -= principal_portion
            
            # Determine status based on current date
            current_date = datetime.now().date()
            if payment_date < current_date:
                status = 'overdue'
            elif payment_date <= current_date + timedelta(days=7):
                status = 'due_soon'
            else:
                status = 'scheduled'
            
            scheduled_payments.append({
                'payment_number': month,
                'due_date': payment_date,
                'total_payment': total_payment,
                'principal_portion': principal_portion,
                'interest_portion': interest_portion,
                'late_fee_portion': Decimal('0.00'),  # Add late fee portion (initially 0)
                'remaining_balance': remaining_balance,
                'status': status,
                'actual_payment': None,  # Will be populated later
                'payment_difference': None,  # Will be calculated later
                'actual_payment_date': None,
                'actual_payment_method': None,
                'payment_id': None,  # Will be populated from actual Payment object
                'is_approved': False,  # Track approval status
                'actual_late_fee_portion': Decimal('0.00'),  # Actual late fees paid
            })
            
            # Next month
            if payment_date.month == 12:
                payment_date = payment_date.replace(year=payment_date.year + 1, month=1)
            else:
                next_month = payment_date.month + 1
                last_day = calendar.monthrange(payment_date.year, next_month)[1]
                payment_date = payment_date.replace(
                    month=next_month, 
                    day=min(payment_date.day, last_day)
                )
        
        # Get actual payments made
        actual_payments = []
        if loan:
            actual_payments_qs = Payment.objects.filter(
                loan=loan
            ).order_by('payment_date')
            
            for payment in actual_payments_qs:
                actual_payments.append({
                    'payment_date': payment.payment_date,
                    'amount': payment.payment_amount,
                    'method': payment.payment_method,
                    'reference': payment.reference_number,
                    'notes': payment.notes,
                    'payment_id': payment.id,  # Include payment ID for approval functionality
                })
        
        # Match actual payments with scheduled payments and calculate actual remaining balance
        actual_remaining_balance = loan_info['principal_amount']
        
        for i, scheduled in enumerate(scheduled_payments):
            # Find matching actual payment by position (1st payment matches 1st scheduled, etc.)
            if i < len(actual_payments):
                actual = actual_payments[i]
                scheduled['actual_payment'] = actual['amount']
                scheduled['actual_payment_date'] = actual['payment_date']
                scheduled['actual_payment_method'] = actual['method']
                scheduled['payment_difference'] = actual['amount'] - scheduled['total_payment']
                scheduled['payment_id'] = actual['payment_id']  # Add payment ID for approval functionality
                
                # Check if this payment has already been approved (has split journal)
                from journal.models import Journal
                # Get the actual Payment object to get its payment_id (payment code)
                payment_obj = Payment.objects.get(id=actual['payment_id'])
                has_split_journal = Journal.objects.filter(
                    company=loan.company,
                    reference=f"SPLIT-{payment_obj.payment_id}"  # Exact match for SPLIT-PAY2025XXXXXX
                ).exists()
                scheduled['is_approved'] = has_split_journal
                
                # Calculate payment timing with nuanced categories
                if actual['payment_date'] <= scheduled['due_date']:
                    scheduled['payment_timing'] = 'on_time'
                    scheduled['days_late'] = 0
                else:
                    days_late = (actual['payment_date'] - scheduled['due_date']).days
                    scheduled['days_late'] = days_late
                    
                    # Nuanced late payment categories
                    if days_late <= 7:
                        scheduled['payment_timing'] = 'slightly_late'  # 1-7 days
                    elif days_late <= 15:
                        scheduled['payment_timing'] = 'moderately_late'  # 8-15 days  
                    elif days_late <= 30:
                        scheduled['payment_timing'] = 'late'  # 16-30 days
                    else:
                        scheduled['payment_timing'] = 'severely_late'  # 30+ days
                
                # Calculate actual interest and principal portions using PaymentProcessor
                # This ensures consistency with journal entries created during approval
                from loans_payments.models import PaymentProcessor
                
                processor = PaymentProcessor(company=application.company)
                allocation = processor.calculate_allocation(loan, actual['amount'])
                
                # Use PaymentProcessor allocation (matches journal entries)
                actual_interest_portion = (allocation.get('accrued_interest', Decimal('0.00')) + 
                                         allocation.get('current_interest', Decimal('0.00'))).quantize(Decimal('0.01'))
                actual_principal_portion = (allocation.get('principal', Decimal('0.00')) + 
                                          allocation.get('prepayment', Decimal('0.00'))).quantize(Decimal('0.01'))
                actual_late_fee_portion = allocation.get('late_fees', Decimal('0.00')).quantize(Decimal('0.01'))
                
                # Ensure totals add up
                calculated_total = actual_interest_portion + actual_principal_portion + actual_late_fee_portion
                if abs(calculated_total - actual['amount']) > Decimal('0.01'):
                    # If there's a rounding difference, adjust principal
                    actual_principal_portion += (actual['amount'] - calculated_total)
                
                scheduled['actual_interest_portion'] = actual_interest_portion
                scheduled['actual_principal_portion'] = actual_principal_portion
                scheduled['actual_late_fee_portion'] = actual_late_fee_portion
                
                # Calculate differences for display
                scheduled['principal_difference'] = actual_principal_portion - scheduled['principal_portion']
                scheduled['interest_difference'] = actual_interest_portion - scheduled['interest_portion']
                
                # Update remaining balance with actual principal payment
                if actual_principal_portion > 0:
                    actual_remaining_balance -= actual_principal_portion
                    if actual_remaining_balance < 0:
                        actual_remaining_balance = Decimal('0.00')
                
                scheduled['actual_remaining_balance'] = actual_remaining_balance
            else:
                # No payment made for this scheduled payment
                if scheduled['status'] == 'overdue':
                    scheduled['payment_difference'] = -scheduled['total_payment']
                # Remaining balance stays the same if no payment made
                scheduled['actual_remaining_balance'] = actual_remaining_balance
                scheduled['actual_interest_portion'] = None
                scheduled['actual_principal_portion'] = None
        
        # Calculate comprehensive payment analysis
        current_date = datetime.now().date()
        scheduled_to_date = [p for p in scheduled_payments if p['due_date'] <= current_date]
        
        # Get only actual payments that correspond to scheduled payments to date
        actual_payments_to_date = actual_payments[:len(scheduled_to_date)]
        
        total_scheduled_to_date = sum(p['total_payment'] for p in scheduled_to_date)
        total_paid = sum(p['amount'] for p in actual_payments_to_date)
        
        payments_due_count = len(scheduled_to_date)
        payments_made_count = len(actual_payments_to_date)
        payment_variance = total_paid - total_scheduled_to_date
        
        # Calculate performance metrics with weighted scoring for late payment severity
        on_time_payments = 0
        slightly_late_payments = 0
        moderately_late_payments = 0
        late_payments = 0
        severely_late_payments = 0
        missed_payments = 0
        weighted_score = 0.0  # New weighted scoring system
        
        for i, scheduled in enumerate(scheduled_to_date):
            if scheduled.get('actual_payment_date'):
                # We have an actual payment - apply weighted scoring based on lateness
                timing = scheduled.get('payment_timing')
                if timing == 'on_time':
                    on_time_payments += 1
                    weighted_score += 1.0  # Full credit
                elif timing == 'slightly_late':  # 1-7 days
                    slightly_late_payments += 1
                    weighted_score += 0.8  # 80% credit - minor penalty
                elif timing == 'moderately_late':  # 8-15 days
                    moderately_late_payments += 1
                    weighted_score += 0.6  # 60% credit - moderate penalty
                elif timing == 'late':  # 16-30 days
                    late_payments += 1
                    weighted_score += 0.4  # 40% credit - major penalty
                elif timing == 'severely_late':  # 30+ days
                    severely_late_payments += 1
                    weighted_score += 0.2  # 20% credit - severe penalty
                else:
                    late_payments += 1
                    weighted_score += 0.5  # 50% credit - default late penalty
            else:
                # No payment made for this scheduled payment
                missed_payments += 1
                weighted_score += 0.0  # No credit for missed payments
        
        # Add any additional missed payments if we have fewer actual payments than scheduled
        if payments_made_count < payments_due_count:
            additional_missed = payments_due_count - payments_made_count
            missed_payments = additional_missed  # Replace the previous count with accurate count
        
        # Calculate loan performance score using weighted system
        if payments_due_count > 0:
            payment_score = (weighted_score / payments_due_count) * 100
        else:
            payment_score = 100
        
        # Calculate time-based variance context
        payments_behind_count = payments_due_count - payments_made_count
        time_variance_description = ""
        if payments_behind_count > 0:
            if payments_behind_count == 1:
                time_variance_description = "1 payment behind"
            elif payments_behind_count <= 3:
                time_variance_description = f"{payments_behind_count} payments behind"
            elif payments_behind_count <= 6:
                time_variance_description = f"{payments_behind_count} payments behind (~{payments_behind_count//3 + 1} months)"
            else:
                months_behind = payments_behind_count // 3 + 1
                time_variance_description = f"{months_behind}+ months behind"
        elif payments_made_count > payments_due_count:
            payments_ahead = payments_made_count - payments_due_count
            if payments_ahead == 1:
                time_variance_description = "1 payment ahead"
            elif payments_ahead <= 3:
                time_variance_description = f"{payments_ahead} payments ahead"
            else:
                months_ahead = payments_ahead // 3 + 1
                time_variance_description = f"{months_ahead}+ months ahead"
        else:
            time_variance_description = "on schedule"
        
        # Calculate percentage-based payment variance
        payment_variance_percentage = 0
        if total_scheduled_to_date > 0:
            payment_variance_percentage = (payment_variance / total_scheduled_to_date) * 100
        
        # Determine variance performance tier based on percentage
        if payment_variance_percentage >= 5:      # 5%+ ahead
            variance_tier = "excellent"
        elif payment_variance_percentage >= 0:    # 0-5% ahead
            variance_tier = "good"
        elif payment_variance_percentage >= -5:   # 0-5% behind
            variance_tier = "fair"
        elif payment_variance_percentage >= -15:  # 5-15% behind
            variance_tier = "poor"
        else:                                     # 15%+ behind
            variance_tier = "critical"
        
        analysis = {
            'total_scheduled_to_date': total_scheduled_to_date,
            'total_paid': total_paid,
            'payment_variance': payment_variance,
            'payment_variance_percentage': round(payment_variance_percentage, 1),
            'variance_tier': variance_tier,
            'payments_made': payments_made_count,
            'payments_due_to_date': payments_due_count,
            'payments_ahead_behind': payments_made_count - payments_due_count,
            'on_track': abs(payment_variance) < 500 and abs(payments_made_count - payments_due_count) <= 1,
            'on_time_payments': on_time_payments,
            'slightly_late_payments': slightly_late_payments,
            'moderately_late_payments': moderately_late_payments,
            'late_payments': late_payments,
            'severely_late_payments': severely_late_payments,
            'missed_payments': missed_payments,
            'payment_score': round(payment_score, 1),
            'time_variance_description': time_variance_description,
            'payments_behind_count': max(0, payments_behind_count),
            'next_payment_due': next((p for p in scheduled_payments if p['due_date'] > current_date), None),
        }
        
        # Find the latest payment with actual balance data for summary display
        latest_actual_balance_info = None
        for payment in reversed(scheduled_payments):
            if payment.get('actual_remaining_balance') is not None:
                latest_actual_balance_info = payment
                break
        
        return render(request, 'loans_core/application_progress.html', {
            'application': application,
            'loan': loan,
            'loan_info': loan_info,
            'scheduled_payments': scheduled_payments,
            'actual_payments': actual_payments,
            'analysis': analysis,
            'monthly_payment': monthly_payment,
            'latest_actual_balance_info': latest_actual_balance_info,
            'title': f'Payment Progress - {application.customer.full_name}',
        })
        
    except LoanApplication.DoesNotExist:
        messages.error(request, 'Application not found.')
        return redirect('loans_core:application_list')
    except Exception as e:
        messages.error(request, f'Error loading payment progress: {str(e)}')
        return redirect('loans_core:application_detail', pk=pk)


@login_required 
def dropdown_test(request):
    """Simple test view to diagnose dropdown issues"""
    from company.models import Company
    
    # Get first company
    user_company = Company.objects.first()
    
    # Get some applications for testing
    applications = LoanApplication.objects.filter(company=user_company)[:5] if user_company else []
    
    # Count applications by status
    status_counts = {}
    if user_company:
        all_apps = LoanApplication.objects.filter(company=user_company)
        for status, _ in LoanApplication.APPLICATION_STATUS:
            status_counts[status] = all_apps.filter(status=status).count()
    
    context = {
        'applications': applications,
        'status_counts': status_counts,
        'total_apps': applications.count() if applications else 0,
        'company': user_company,
    }
    
    return render(request, 'loans_core/dropdown_test.html', context)


def loan_application_bulk_upload(request):
    """Bulk upload loan applications from Excel/CSV file"""
    from .forms import LoanApplicationBulkUploadForm
    user_company = get_user_company(request.user)
    
    if request.method == 'POST':
        form = LoanApplicationBulkUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            file = request.FILES['file']
            
            try:
                # Import required libraries
                import pandas as pd
                from decimal import Decimal, InvalidOperation
                from loans_customers.models import Customer
                
                # Read the file
                if file.name.lower().endswith('.xlsx'):
                    df = pd.read_excel(file)
                else:  # CSV
                    # Handle UTF-8 encoding for Cyrillic characters
                    try:
                        df = pd.read_csv(file, encoding='utf-8')
                    except UnicodeDecodeError:
                        # Fallback to other encodings if UTF-8 fails
                        try:
                            df = pd.read_csv(file, encoding='cp1251')  # Common for Cyrillic
                        except UnicodeDecodeError:
                            df = pd.read_csv(file, encoding='latin-1')  # Last resort
                
                success_count = 0
                errors = []
                
                for index, row in df.iterrows():
                    try:
                        # Required fields validation
                        required_fields = {
                            'national_id': 'National ID (Cyrillic/Latin)',
                            'first_name': 'First Name',
                            'loan_product_code': 'Loan Product Code',
                            'requested_amount': 'Requested Amount',
                            'term_months': 'Term (Months)',
                            'interest_rate': 'Interest Rate',
                            'purpose': 'Purpose'
                        }
                        
                        missing_fields = []
                        for field, display_name in required_fields.items():
                            if pd.isna(row.get(field)) or str(row.get(field)).strip() == '':
                                missing_fields.append(display_name)
                        
                        if missing_fields:
                            errors.append(f"Row {index + 2}: Missing required fields: {', '.join(missing_fields)}")
                            continue
                        
                        # Find customer by national_id and first_name (supporting Cyrillic)
                        national_id = str(row['national_id']).strip()
                        first_name = str(row['first_name']).strip()
                        customer = None
                        
                        # Try to find by national_id and first_name combination (most accurate)
                        try:
                            customer = Customer.objects.get(
                                company=user_company,
                                national_id=national_id,
                                first_name=first_name
                            )
                        except Customer.DoesNotExist:
                            # Try to find by national_id only
                            try:
                                customer = Customer.objects.get(
                                    company=user_company,
                                    national_id=national_id
                                )
                                # Warn if first name doesn't match
                                if customer.first_name != first_name:
                                    errors.append(f"Row {index + 2}: Customer found with National ID {national_id} but first name doesn't match (Expected: {customer.first_name}, Got: {first_name}). Using found customer.")
                            except Customer.DoesNotExist:
                                # Try to find by customer_id as fallback (if column exists)
                                if 'customer_id' in row and not pd.isna(row.get('customer_id')):
                                    customer_id = str(row['customer_id']).strip()
                                    try:
                                        customer = Customer.objects.get(
                                            company=user_company,
                                            customer_id=customer_id
                                        )
                                    except Customer.DoesNotExist:
                                        pass
                                
                                if not customer:
                                    errors.append(f"Row {index + 2}: Customer not found with National ID: {national_id} and First Name: {first_name}")
                                    continue
                        
                        # Find loan product by code
                        product_code = str(row['loan_product_code']).strip()
                        try:
                            loan_product = LoanProduct.objects.get(
                                company=user_company,
                                code=product_code,
                                is_active=True
                            )
                        except LoanProduct.DoesNotExist:
                            errors.append(f"Row {index + 2}: Loan product not found or inactive: {product_code}")
                            continue
                        
                        # Validate and parse amounts
                        try:
                            requested_amount = Decimal(str(row['requested_amount']))
                            if requested_amount <= 0:
                                errors.append(f"Row {index + 2}: Requested amount must be greater than 0")
                                continue
                        except (ValueError, InvalidOperation):
                            errors.append(f"Row {index + 2}: Invalid requested amount: {row['requested_amount']}")
                            continue
                        
                        # Validate term months
                        try:
                            term_months = int(row['term_months'])
                            if term_months <= 0:
                                errors.append(f"Row {index + 2}: Term months must be greater than 0")
                                continue
                        except (ValueError, TypeError):
                            errors.append(f"Row {index + 2}: Invalid term months: {row['term_months']}")
                            continue
                        
                        # Validate interest rate
                        try:
                            interest_rate = Decimal(str(row['interest_rate']))
                            if interest_rate < 0 or interest_rate > 100:
                                errors.append(f"Row {index + 2}: Interest rate must be between 0 and 100")
                                continue
                        except (ValueError, InvalidOperation):
                            errors.append(f"Row {index + 2}: Invalid interest rate: {row['interest_rate']}")
                            continue
                        
                        # Parse optional fields
                        repayment_method = 'equal_payment'  # default
                        if not pd.isna(row.get('repayment_method')):
                            method_input = str(row['repayment_method']).strip().lower()
                            valid_methods = dict(LoanApplication.REPAYMENT_METHOD)
                            if method_input in valid_methods.keys():
                                repayment_method = method_input
                        
                        payment_frequency = 'monthly'  # default
                        if not pd.isna(row.get('payment_frequency')):
                            freq_input = str(row['payment_frequency']).strip().lower()
                            valid_frequencies = dict(LoanApplication.PAYMENT_FREQUENCY)
                            if freq_input in valid_frequencies.keys():
                                payment_frequency = freq_input
                        
                        grace_period_months = 0
                        if not pd.isna(row.get('grace_period_months')):
                            try:
                                grace_period_months = int(row['grace_period_months'])
                            except (ValueError, TypeError):
                                grace_period_months = 0
                        
                        # Parse first payment date
                        first_payment_date = None
                        if not pd.isna(row.get('first_payment_date')):
                            try:
                                if isinstance(row['first_payment_date'], str):
                                    first_payment_date = pd.to_datetime(row['first_payment_date']).date()
                                else:
                                    first_payment_date = row['first_payment_date']
                            except (ValueError, TypeError):
                                pass  # Keep as None if invalid
                        
                        # Parse disbursement date
                        disbursement_date = None
                        if not pd.isna(row.get('disbursement_date')):
                            try:
                                if isinstance(row['disbursement_date'], str):
                                    disbursement_date = pd.to_datetime(row['disbursement_date']).date()
                                else:
                                    disbursement_date = row['disbursement_date']
                            except (ValueError, TypeError):
                                pass  # Keep as None if invalid
                        
                        # Create the loan application
                        LoanApplication.objects.create(
                            company=user_company,
                            customer=customer,
                            loan_product=loan_product,
                            requested_amount=requested_amount,
                            term_months=term_months,
                            interest_rate=interest_rate,
                            repayment_method=repayment_method,
                            payment_frequency=payment_frequency,
                            grace_period_months=grace_period_months,
                            first_payment_date=first_payment_date,
                            disbursement_date=disbursement_date,
                            purpose=str(row['purpose']).strip(),
                            collateral_description=str(row.get('collateral_description', '')).strip(),
                            notes=str(row.get('notes', '')).strip(),
                            status='under_review',  # Changed from 'draft' to require review
                            created_by=request.user
                        )
                        
                        success_count += 1
                        
                    except Exception as e:
                        errors.append(f"Row {index + 2}: {str(e)}")
                        continue
                
                # Show results
                if success_count > 0:
                    from django.urls import reverse
                    review_url = reverse('loans_core:bulk_upload_review')
                    messages.success(
                        request, 
                        f'✅ Successfully created {success_count} loan applications! '
                        f'Applications are pending review. '
                        f'<a href="{review_url}" class="btn btn-sm btn-primary ms-2">'
                        f'<i class="fas fa-clipboard-check"></i> Review Applications</a>'
                    )
                
                if errors:
                    error_msg = f'⚠️ {len(errors)} errors occurred:\n' + '\n'.join(errors[:10])
                    if len(errors) > 10:
                        error_msg += f'\n... and {len(errors) - 10} more errors'
                    messages.error(request, error_msg)
                
            except ImportError:
                messages.error(request, '❌ Pandas library not installed. Cannot process Excel/CSV files.')
            except Exception as e:
                messages.error(request, f'❌ File processing error: {str(e)}')
        
        return redirect('loans_core:application_bulk_upload')
    
    else:
        form = LoanApplicationBulkUploadForm()
    
    return render(request, 'loans_core/loan_application_bulk_upload.html', {
        'form': form,
        'title': 'Bulk Upload Loan Applications',
        'company': user_company,
    })


def download_loan_application_template(request):
    """Download CSV template for loan application bulk upload with proper UTF-8 encoding"""
    import csv
    from django.http import HttpResponse
    
    # Create the HttpResponse object with CSV header and UTF-8 encoding
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="loan_application_upload_template.csv"'
    
    # Add BOM for UTF-8 to ensure Excel recognizes the encoding
    response.write('\ufeff')
    
    # Create CSV writer
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'national_id', 'first_name', 'loan_product_code', 'requested_amount', 
        'term_months', 'interest_rate', 'purpose', 'repayment_method', 
        'payment_frequency', 'grace_period_months', 'first_payment_date', 
        'disbursement_date', 'collateral_description', 'notes'
    ])
    
    # Write sample data with Cyrillic characters using valid loan product codes
    sample_data = [
        ['УБ12345001', 'Батбаяр', 'PL001', '500000', '24', '12.0', 'Бизнес өргөтгөл', 'equal_payment', 'monthly', '0', '2025-05-01', '2025-04-25', 'Business equipment', 'Good credit history'],
        ['МН87654002', 'Цэцэгмаа', 'AL001', '800000', '60', '10.0', 'Машин худалдан авах', 'equal_payment', 'monthly', '1', '2025-04-15', '2025-04-10', 'Honda Civic 2023', 'Existing customer'],
        ['АА98765003', 'Ганболд', 'ML001', '2000000', '120', '8.0', 'Гэр засвар', 'equal_payment', 'monthly', '0', '2025-06-01', '2025-05-20', 'Property deed', 'First time borrower'],
        ['БГ11223004', 'Сайнбаяр', 'PL001', '300000', '18', '12.0', 'Хувийн хэрэг', 'equal_payment', 'bi_weekly', '0', '2025-04-20', '', '', 'Salary verification provided'],
        ['ТҮ55443305', 'Оюунбилэг', 'SL001', '150000', '48', '6.0', 'Сургалтын зардал', 'equal_payment', 'monthly', '0', '2025-09-01', '2025-08-25', 'University acceptance letter', 'Student discount applied'],
        ['ЭР66778806', 'Баасандорж', 'BL001', '1500000', '36', '15.0', 'Бизнес санхүүжилт', 'equal_payment', 'monthly', '0', '2025-05-15', '2025-05-10', 'Equipment and inventory', 'SME expansion loan'],
        ['ХМ99887707', 'Мөнхбаяр', 'EL001', '80000', '12', '18.0', 'Яаралтай зардал', 'equal_payment', 'monthly', '0', '2025-04-01', '2025-03-28', 'Emergency medical', 'Fast processing needed'],
        ['УБ12345001', 'Батбаяр', 'CL001', '10000000', '120', '35.0', 'Том хөрөнгө оруулалт', 'equal_payment', 'monthly', '0', '2025-07-01', '2025-06-25', 'Real estate investment', 'Custom flexible terms']
    ]
    
    for row in sample_data:
        writer.writerow(row)
    
    return response


@login_required
def bulk_upload_review(request):
    """
    Review page for bulk uploaded loan applications that are in 'under_review' status.
    Allows approving, rejecting, or editing applications individually or in bulk.
    """
    user_company = get_user_company(request.user)
    if not user_company:
        messages.error(request, "No company assigned to your account.")
        return redirect('loans_core:application_list')
    
    # Get applications pending review (under_review status)
    applications = LoanApplication.objects.filter(
        company=user_company,
        status='under_review'
    ).select_related('customer', 'loan_product', 'created_by').order_by('-created_at')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        application_ids = request.POST.getlist('application_ids')
        
        if not application_ids:
            messages.error(request, "No applications selected.")
            return redirect('loans_core:bulk_upload_review')
        
        # Filter applications to ensure they belong to user's company and are under_review
        selected_applications = applications.filter(id__in=application_ids)
        
        if action == 'bulk_approve':
            # Bulk approve selected applications
            updated_count = selected_applications.update(
                status='approved',
                approval_date=timezone.now().date()
            )
            messages.success(request, f'✅ Successfully approved {updated_count} applications!')
            
        elif action == 'bulk_reject':
            rejection_reason = request.POST.get('rejection_reason', 'Bulk rejection from review')
            updated_count = selected_applications.update(
                status='rejected',
                rejection_reason=rejection_reason
            )
            messages.success(request, f'✅ Successfully rejected {updated_count} applications!')
            
        elif action == 'bulk_draft':
            # Move back to draft for further editing
            updated_count = selected_applications.update(status='draft')
            messages.success(request, f'✅ Successfully moved {updated_count} applications back to draft!')
            
        return redirect('loans_core:bulk_upload_review')
    
    context = {
        'applications': applications,
        'total_count': applications.count(),
        'title': 'Bulk Upload Review',
    }
    
    return render(request, 'loans_core/bulk_upload_review.html', context)


@login_required
def application_quick_action(request, pk):
    """
    Quick action for individual application review (approve/reject/draft)
    """
    user_company = get_user_company(request.user)
    if not user_company:
        return JsonResponse({'success': False, 'error': 'No company assigned'})
    
    try:
        application = LoanApplication.objects.get(
            id=pk, 
            company=user_company,
            status='under_review'
        )
    except LoanApplication.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Application not found or not reviewable'})
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            application.status = 'approved'
            application.approval_date = timezone.now().date()
            application.save()
            return JsonResponse({'success': True, 'message': 'Application approved successfully!'})
            
        elif action == 'reject':
            rejection_reason = request.POST.get('rejection_reason', 'Rejected during review')
            application.status = 'rejected'
            application.rejection_reason = rejection_reason
            application.save()
            return JsonResponse({'success': True, 'message': 'Application rejected successfully!'})
            
        elif action == 'draft':
            application.status = 'draft'
            application.save()
            return JsonResponse({'success': True, 'message': 'Application moved to draft successfully!'})
    
    return JsonResponse({'success': False, 'error': 'Invalid action'})


# =====================================================
# LOAN PROGRESS ENGINE APPROVAL FUNCTIONS
# =====================================================

@login_required
def approve_payment(request, pk):
    """Approve individual payment allocation using four-tier system"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        from loan_reconciliation_bridge.models import LoanGLConfiguration
        from loan_reconciliation_bridge.views import create_split_journal_entries
        from loans_payments.models import Payment, PaymentProcessor
        
        # Get the application and validate access
        application = get_object_or_404(LoanApplication, pk=pk)
        user_company = get_user_company(request.user)
        
        if application.company != user_company:
            return JsonResponse({'success': False, 'error': 'Access denied'})
        
        # Get payment ID from POST data
        payment_id = request.POST.get('payment_id')
        if not payment_id:
            return JsonResponse({'success': False, 'error': 'Payment ID required'})
        
        # Get the payment - handle both Django ID (integer) and payment_id (string)
        try:
            if payment_id.startswith('PAY'):
                # Custom payment_id like "PAY2025155628"
                payment = get_object_or_404(Payment, payment_id=payment_id, loan__application=application)
            else:
                # Django auto ID (integer)
                payment = get_object_or_404(Payment, id=int(payment_id), loan__application=application)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid payment ID format'})
        
        # Check for duplicate approval - prevent multiple split journals for same payment
        from journal.models import Journal
        existing_journals = Journal.objects.filter(
            company=user_company,
            reference=f"SPLIT-PAY{payment.payment_id}"  # Exact match for split journals
        )
        
        if existing_journals.exists():
            existing_ref = existing_journals.first().reference
            return JsonResponse({
                'success': False, 
                'error': f'Payment already approved with journal {existing_ref}. Duplicate approvals are not allowed.',
                'already_approved': True
            })
        
        # Get GL configuration
        try:
            config = LoanGLConfiguration.objects.get(company=user_company)
        except LoanGLConfiguration.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Four-tier payment allocation not configured. Please complete setup first.'})
        
        # Calculate allocation using PaymentProcessor
        processor = PaymentProcessor(company=user_company)
        allocation = processor.calculate_allocation(payment.loan, payment.payment_amount)
        
        # Create split journal entries using the preserved utility function
        journal = create_split_journal_entries(payment, allocation, config, request.user)
        
        # Update payment with approval info
        payment.notes = f"{payment.notes or ''}\n\nMANAGER APPROVED: Split allocation created in Journal {journal.reference}".strip()
        payment.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Payment allocation approved successfully!',
            'journal_reference': journal.reference
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required 
def edit_payment_allocation(request, pk):
    """Edit payment allocation with manual split entry"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        # Get the application and validate access
        application = get_object_or_404(LoanApplication, pk=pk)
        user_company = get_user_company(request.user)
        
        if application.company != user_company:
            return JsonResponse({'success': False, 'error': 'Access denied'})
        
        # Get payment data from POST
        payment_id = request.POST.get('payment_id')
        interest_amount = Decimal(str(request.POST.get('interest_amount', '0.00')))
        principal_amount = Decimal(str(request.POST.get('principal_amount', '0.00')))
        late_fee_amount = Decimal(str(request.POST.get('late_fee_amount', '0.00')))
        
        if not payment_id:
            return JsonResponse({'success': False, 'error': 'Payment ID required'})
        
        # Get the payment - handle both Django ID and payment_id
        from loans_payments.models import Payment
        try:
            if payment_id.startswith('PAY'):
                payment = get_object_or_404(Payment, payment_id=payment_id, loan__application=application)
            else:
                payment = get_object_or_404(Payment, id=int(payment_id), loan__application=application)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid payment ID format'})
        
        # Check for duplicate approval - prevent editing already approved payments
        from journal.models import Journal
        existing_journals = Journal.objects.filter(
            company=user_company,
            reference=f"SPLIT-PAY{payment.payment_id}"  # Exact match for split journals
        )
        
        if existing_journals.exists():
            existing_ref = existing_journals.first().reference
            return JsonResponse({
                'success': False, 
                'error': f'Cannot edit payment allocation. Payment already approved with journal {existing_ref}.',
                'already_approved': True
            })
        
        # Validate total matches payment amount
        calculated_total = interest_amount + principal_amount + late_fee_amount
        if abs(calculated_total - payment.payment_amount) > Decimal('0.01'):
            return JsonResponse({
                'success': False, 
                'error': f'Total allocation ({calculated_total}) must equal payment amount ({payment.payment_amount})'
            })
        
        # Update payment allocation (you might need to add these fields to Payment model)
        # For now, store in notes as structured data
        allocation_data = {
            'manual_split': True,
            'interest_amount': str(interest_amount),
            'principal_amount': str(principal_amount),
            'late_fee_amount': str(late_fee_amount),
            'updated_by': request.user.username,
            'updated_at': timezone.now().isoformat()
        }
        
        payment.notes = f"{payment.notes or ''}\n\nMANUAL ALLOCATION: {json.dumps(allocation_data)}".strip()
        payment.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Payment allocation updated successfully!'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def approve_entire_loan(request, pk):
    """Approve entire loan using four-tier system for all payments"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        from loan_reconciliation_bridge.models import LoanGLConfiguration
        from loan_reconciliation_bridge.views import create_split_journal_entries
        from loans_payments.models import Payment, PaymentProcessor
        from journal.models import Journal
        
        # Get the application and validate access
        application = get_object_or_404(LoanApplication, pk=pk)
        user_company = get_user_company(request.user)
        
        if application.company != user_company:
            return JsonResponse({'success': False, 'error': 'Access denied'})
        
        # Check if loan exists
        try:
            loan = application.loan
        except Exception:
            return JsonResponse({'success': False, 'error': 'Loan not found for this application'})
        
        # Get GL configuration
        try:
            config = LoanGLConfiguration.objects.get(company=user_company)
        except LoanGLConfiguration.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Four-tier payment allocation not configured. Please complete setup first.'})
        
        # Get all payments for this loan that haven't been approved yet
        payments = Payment.objects.filter(loan=loan)
        
        if not payments.exists():
            return JsonResponse({'success': False, 'error': 'No payments found for this loan'})
        
        # Initialize processor
        processor = PaymentProcessor(company=user_company)
        
        approved_count = 0
        journal_references = []
        
        # Process each payment
        for payment in payments:
            # Check if already approved (has split journal) - DUPLICATION DETECTION
            existing_journals = Journal.objects.filter(
                company=user_company,
                reference=f"SPLIT-PAY{payment.payment_id}"  # Exact match for split journals
            )
            
            if existing_journals.exists():
                continue  # Skip already approved payments
            
            # Calculate allocation
            allocation = processor.calculate_allocation(payment.loan, payment.payment_amount)
            
            # Create split journal entries
            journal = create_split_journal_entries(payment, allocation, config, request.user)
            
            # Update payment with approval info
            payment.notes = f"{payment.notes or ''}\n\nWHOLE LOAN APPROVAL: Split allocation created in Journal {journal.reference}".strip()
            payment.save()
            
            approved_count += 1
            journal_references.append(journal.reference)
        
        if approved_count == 0:
            return JsonResponse({'success': False, 'error': 'All payments have already been approved'})
        
        return JsonResponse({
            'success': True,
            'message': f'Entire loan approved successfully! {approved_count} payments processed.',
            'approved_count': approved_count,
            'journal_references': journal_references
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

