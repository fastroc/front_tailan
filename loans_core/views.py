"""
Views for loan core functionality
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
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
    """Main loan dashboard with statistics"""
    user_company = get_user_company(request.user)
    
    # Get statistics
    stats = {
        'total_customers': Customer.objects.filter(company=user_company).count(),
        'active_loans': Loan.objects.filter(company=user_company, status='active').count(),
        'pending_applications': LoanApplication.objects.filter(
            company=user_company, status='pending'
        ).count(),
        'total_portfolio': Loan.objects.filter(
            company=user_company
        ).aggregate(total=Sum('principal_amount'))['total'] or Decimal('0.00'),
        'overdue_loans': Loan.objects.filter(
            company=user_company, days_overdue__gt=0
        ).count(),
    }
    
    # Recent applications
    recent_applications = LoanApplication.objects.filter(
        company=user_company
    ).select_related('customer', 'loan_product').order_by('-created_at')[:5]
    
    # Recent loans
    recent_loans = Loan.objects.filter(
        company=user_company
    ).select_related('customer', 'loan_product').order_by('-created_at')[:5]
    
    return render(request, 'loans_core/dashboard.html', {
        'stats': stats,
        'recent_applications': recent_applications,
        'recent_loans': recent_loans,
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
    """Approve or reject a loan application with full contract creation"""
    from decimal import Decimal
    import datetime
    from django.utils import timezone
    
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
                disbursement_date = datetime.datetime.strptime(
                    request.POST.get('disbursement_date'), '%Y-%m-%d'
                ).date()
                first_payment_date = datetime.datetime.strptime(
                    request.POST.get('first_payment_date'), '%Y-%m-%d'
                ).date()
                
                # Optional fields
                payment_frequency = request.POST.get('payment_frequency', 'monthly')
                grace_period_days = int(request.POST.get('grace_period_days', '0'))
                late_fee_percentage = Decimal(request.POST.get('late_fee_percentage', '0'))
                allows_prepayment = request.POST.get('allows_prepayment') == 'on'
                prepayment_penalty = Decimal(request.POST.get('prepayment_penalty', '0'))
                contract_conditions = request.POST.get('contract_conditions', '')
                notes = request.POST.get('notes', '')
                
                # Calculate monthly payment
                if payment_frequency == 'monthly':
                    monthly_rate = interest_rate / Decimal('100') / Decimal('12')
                    if monthly_rate > 0:
                        monthly_payment = approved_amount * (
                            monthly_rate * (1 + monthly_rate) ** term_months
                        ) / ((1 + monthly_rate) ** term_months - 1)
                    else:
                        monthly_payment = approved_amount / term_months
                else:
                    # For other frequencies, calculate proportionally
                    monthly_payment = approved_amount / term_months  # Simplified
                
                # Calculate maturity date
                maturity_date = first_payment_date
                for _ in range(term_months - 1):
                    if maturity_date.month == 12:
                        maturity_date = maturity_date.replace(year=maturity_date.year + 1, month=1)
                    else:
                        maturity_date = maturity_date.replace(month=maturity_date.month + 1)
                
                # Update application
                application.status = 'approved'
                application.approved_amount = approved_amount
                application.interest_rate = interest_rate
                application.term_months = term_months
                application.approval_date = timezone.now().date()
                application.disbursement_date = disbursement_date
                application.first_payment_date = first_payment_date
                application.notes = notes
                application.updated_by = request.user
                application.save()
                
                # Create loan with full contract details
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
                
                messages.success(
                    request, 
                    f'Application approved! Loan {loan.loan_number} created with disbursement scheduled for {disbursement_date}.'
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
            # Handle other form submissions (original form)
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
    """View loan details"""
    user_company = get_user_company(request.user)
    loan = get_object_or_404(
        Loan.objects.select_related('customer', 'loan_product', 'application'),
        pk=pk, company=user_company
    )
    
    return render(request, 'loans_core/loan_detail.html', {
        'loan': loan,
    })


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
    """Demo applications page without authentication"""
    # For demo purposes, use the first company
    from company.models import Company
    user_company = Company.objects.first()
    
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
    """Loan reports and analytics dashboard"""
    user_company = get_user_company(request.user)
    
    # Calculate portfolio statistics
    from django.db.models import Sum, Count, Avg
    
    portfolio_stats = {
        'total_portfolio_value': Loan.objects.filter(
            company=user_company
        ).aggregate(total=Sum('principal_amount'))['total'] or Decimal('0.00'),
        
        'active_loans_count': Loan.objects.filter(
            company=user_company, status='active'
        ).count(),
        
        'total_customers': Customer.objects.filter(
            company=user_company
        ).count(),
        
        'pending_applications': LoanApplication.objects.filter(
            company=user_company, status='pending'
        ).count(),
        
        'overdue_loans': Loan.objects.filter(
            company=user_company, days_overdue__gt=0
        ).count(),
        
        'avg_loan_amount': Loan.objects.filter(
            company=user_company
        ).aggregate(avg=Avg('principal_amount'))['avg'] or Decimal('0.00'),
        
        'collection_rate': 98.5,  # This would be calculated based on payment data
        'default_rate': 1.8,     # This would be calculated based on defaulted loans
    }
    
    # Get recent loans for display
    recent_loans = Loan.objects.filter(
        company=user_company
    ).select_related('customer', 'loan_product').order_by('-created_at')[:10]
    
    # Get loan product distribution
    product_distribution = LoanProduct.objects.filter(
        company=user_company
    ).annotate(
        loan_count=Count('loan')
    ).values('name', 'loan_count', 'category')
    
    return render(request, 'loans_core/reports.html', {
        'portfolio_stats': portfolio_stats,
        'recent_loans': recent_loans,
        'product_distribution': product_distribution,
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
