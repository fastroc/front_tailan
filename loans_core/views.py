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
    """Enhanced loan dashboard with dynamic statistics and improved UX"""
    user_company = get_user_company(request.user)
    
    # Get real statistics from database
    today = timezone.now().date()
    
    # Calculate real statistics
    total_customers = Customer.objects.filter(company=user_company).count()
    active_loans_count = Loan.objects.filter(company=user_company, status='active').count()
    pending_applications_count = LoanApplication.objects.filter(
        company=user_company, status__in=['pending', 'under_review']
    ).count()
    
    # Portfolio calculations
    total_portfolio = Loan.objects.filter(
        company=user_company, status='active'
    ).aggregate(total=Sum('principal_amount'))['total'] or Decimal('0.00')
    
    total_outstanding = Loan.objects.filter(
        company=user_company, status='active'
    ).aggregate(total=Sum('current_balance'))['total'] or Decimal('0.00')
    
    # Overdue calculations
    overdue_loans = Loan.objects.filter(
        company=user_company, 
        status='active',
        next_payment_date__lt=today
    )
    overdue_amount = overdue_loans.aggregate(total=Sum('current_balance'))['total'] or Decimal('0.00')
    
    # Monthly disbursements (current month)
    monthly_disbursements = Loan.objects.filter(
        company=user_company,
        disbursement_date__year=today.year,
        disbursement_date__month=today.month
    ).aggregate(total=Sum('principal_amount'))['total'] or Decimal('0.00')
    
    # Collection rate calculation (simple approximation)
    total_payments_received = Loan.objects.filter(
        company=user_company
    ).aggregate(total=Sum('total_payments_received'))['total'] or Decimal('0.00')
    
    if total_portfolio > 0:
        collection_rate = (total_payments_received / total_portfolio * 100).quantize(Decimal('0.1'))
    else:
        collection_rate = Decimal('0.0')
    
    # Average loan size
    if active_loans_count > 0:
        avg_loan_size = (total_portfolio / active_loans_count).quantize(Decimal('0.01'))
    else:
        avg_loan_size = Decimal('0.00')
    
    stats = {
        'total_portfolio': total_portfolio,
        'active_loans': active_loans_count,
        'pending_applications': pending_applications_count,
        'overdue_amount': overdue_amount,
        'monthly_disbursements': monthly_disbursements,
        'collection_rate': collection_rate,
        'avg_loan_size': avg_loan_size,
        'total_customers': total_customers,
    }
    
    # If no real data exists, show some demo data
    if total_customers == 0 and active_loans_count == 0:
        stats = {
            'total_portfolio': Decimal('2450000.00'),  # Mock: $2.45M portfolio
            'active_loans': 47,  # Mock: 47 active loans
            'pending_applications': 12,  # Mock: 12 pending applications
            'overdue_amount': Decimal('85000.00'),  # Mock: $85K overdue
            'monthly_disbursements': Decimal('320000.00'),  # Mock: $320K this month
            'collection_rate': Decimal('94.5'),  # Mock: 94.5% collection rate
            'avg_loan_size': Decimal('52127.00'),  # Mock: average loan size
            'total_customers': 89,  # Mock: 89 customers
        }
    
    # Get recent applications (real data)
    recent_applications = LoanApplication.objects.filter(
        company=user_company
    ).select_related('customer').order_by('-application_date')[:5]
    
    # If no real applications, show mock data
    if not recent_applications.exists():
        class MockApplication:
            def __init__(self, customer_name, amount, status, date, id):
                self.id = id
                self.customer = type('Customer', (), {'full_name': customer_name})()
                self.requested_amount = amount
                self.status = status
                self.application_date = date
        
        from datetime import timedelta
        recent_applications = [
            MockApplication('John Smith', Decimal('15000.00'), 'pending', today, 1),
            MockApplication('Sarah Johnson', Decimal('25000.00'), 'approved', today - timedelta(days=1), 2),
            MockApplication('Michael Brown', Decimal('8000.00'), 'pending', today - timedelta(days=1), 3),
            MockApplication('Emily Davis', Decimal('30000.00'), 'approved', today - timedelta(days=2), 4),
            MockApplication('David Wilson', Decimal('12000.00'), 'under_review', today - timedelta(days=2), 5),
        ]
    
    # Get active loans (real data)
    active_loans = Loan.objects.filter(
        company=user_company, status='active'
    ).select_related('customer').order_by('-disbursement_date')[:5]
    
    # If no real loans, show mock data
    if not active_loans.exists():
        class MockLoan:
            def __init__(self, loan_number, customer_name, amount, balance, status, next_payment):
                self.loan_number = loan_number
                self.customer = type('Customer', (), {'full_name': customer_name})()
                self.principal_amount = amount
                self.current_balance = balance  # Use current_balance instead of outstanding_balance
                self.status = status
                self.next_payment_date = next_payment
        
        from datetime import timedelta
        active_loans = [
            MockLoan('DL2025001', 'John Smith', Decimal('15000.00'), Decimal('12500.00'), 'current', today + timedelta(days=5)),
            MockLoan('DL2025002', 'Sarah Johnson', Decimal('25000.00'), Decimal('18750.00'), 'current', today + timedelta(days=8)),
            MockLoan('DL2025003', 'Michael Brown', Decimal('8000.00'), Decimal('6400.00'), 'overdue', today - timedelta(days=3)),
            MockLoan('DL2025004', 'Emily Davis', Decimal('30000.00'), Decimal('27500.00'), 'current', today + timedelta(days=12)),
            MockLoan('DL2025005', 'David Wilson', Decimal('12000.00'), Decimal('9800.00'), 'current', today + timedelta(days=15)),
        ]
    # 
    # active_loans = Loan.objects.filter(
    #     company=user_company,
    #     status='active'
    # ).select_related('customer').order_by('-disbursement_date')[:5]
    
    return render(request, 'loans_core/dashboard_enhanced.html', {
        'stats': stats,
        'recent_applications': recent_applications,
        'active_loans': active_loans,
        'title': 'Loan Management Dashboard',
        'company': user_company,
        'today_date': today,
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
                
                # Create loan record
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
                    current_date = first_payment_date
                    for i, payment_data in enumerate(schedule_data):
                        # Parse payment data safely
                        principal_amount = Decimal(str(payment_data.get('principal', 0)))
                        interest_amount = Decimal(str(payment_data.get('interest', 0)))
                        payment_amount = Decimal(str(payment_data.get('payment', 0)))
                        balance = Decimal(str(payment_data.get('balance', 0)))
                        
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
                            due_date=current_date,
                            principal_amount=principal_amount,
                            interest_amount=interest_amount,
                            total_amount=payment_amount,
                            beginning_balance=beginning_balance,
                            ending_balance=balance,
                            is_custom_amount=True,  # Mark as custom since user edited principals
                            status='scheduled',
                            created_by=request.user
                        )
                        
                        # Move to next month
                        if current_date.month == 12:
                            current_date = current_date.replace(year=current_date.year + 1, month=1)
                        else:
                            current_date = current_date.replace(month=current_date.month + 1)
                
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
    
    return render(request, 'loans_core/application_approval.html', {
        'form': form,
        'application': application,
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
    
    # Base queryset without prefetch first to test loading
    applications = LoanApplication.objects.filter(
        company=user_company
    ).select_related(
        'customer', 
        'loan_product'
    ).order_by('-created_at')
    
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
    if status_filter:
        applications = applications.filter(status=status_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        applications = applications.filter(
            Q(customer__first_name__icontains=search_query) |
            Q(customer__last_name__icontains=search_query) |
            Q(application_id__icontains=search_query)
        )
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(applications, 25)  # Show 25 applications per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'loans_core/application_list.html', {
        'page_obj': page_obj,
        'applications': page_obj,
        'stats': stats,
        'search_query': search_query,
        'status_filter': status_filter,
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
                'remaining_balance': remaining_balance,
                'status': status,
                'actual_payment': None,  # Will be populated later
                'payment_difference': None,  # Will be calculated later
                'actual_payment_date': None,
                'actual_payment_method': None
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
                
                # Calculate actual interest and principal portions
                # Interest is calculated on the current remaining balance
                actual_interest_portion = (actual_remaining_balance * monthly_rate).quantize(Decimal('0.01'))
                actual_principal_portion = actual['amount'] - actual_interest_portion
                
                # Ensure principal portion is not negative
                if actual_principal_portion < 0:
                    actual_principal_portion = Decimal('0.00')
                    actual_interest_portion = actual['amount']
                
                scheduled['actual_interest_portion'] = actual_interest_portion
                scheduled['actual_principal_portion'] = actual_principal_portion
                
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
        
        total_scheduled_to_date = sum(p['total_payment'] for p in scheduled_to_date)
        total_paid = sum(p['amount'] for p in actual_payments)
        
        payments_due_count = len(scheduled_to_date)
        payments_made_count = len(actual_payments)
        payment_variance = total_paid - total_scheduled_to_date
        
        # Calculate performance metrics
        on_time_payments = 0
        late_payments = 0
        
        for scheduled in scheduled_to_date:
            # Find matching actual payment within 30 days of due date
            matching_payment = None
            for actual in actual_payments:
                if (scheduled['due_date'] <= actual['payment_date'] <= 
                    scheduled['due_date'] + timedelta(days=30)):
                    matching_payment = actual
                    break
            
            if matching_payment:
                if matching_payment['payment_date'] <= scheduled['due_date']:
                    on_time_payments += 1
                else:
                    late_payments += 1
        
        # Calculate loan performance score
        if payments_due_count > 0:
            payment_score = (on_time_payments / payments_due_count) * 100
        else:
            payment_score = 100
        
        analysis = {
            'total_scheduled_to_date': total_scheduled_to_date,
            'total_paid': total_paid,
            'payment_variance': payment_variance,
            'payments_made': payments_made_count,
            'payments_due_to_date': payments_due_count,
            'payments_ahead_behind': payments_made_count - payments_due_count,
            'on_track': abs(payment_variance) < 500 and abs(payments_made_count - payments_due_count) <= 1,
            'on_time_payments': on_time_payments,
            'late_payments': late_payments,
            'missed_payments': max(0, payments_due_count - payments_made_count),
            'payment_score': round(payment_score, 1),
            'next_payment_due': next((p for p in scheduled_payments if p['due_date'] > current_date), None),
        }
        
        return render(request, 'loans_core/application_progress.html', {
            'application': application,
            'loan': loan,
            'loan_info': loan_info,
            'scheduled_payments': scheduled_payments,
            'actual_payments': actual_payments,
            'analysis': analysis,
            'monthly_payment': monthly_payment,
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
