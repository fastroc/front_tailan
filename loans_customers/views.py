"""
Views for customer management
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime
import traceback

from .models import Customer, CustomerDocument
from company.models import Company
from loans_core.models import LoanApplication, Loan
from .forms import (
    CustomerForm, QuickCustomerForm, CustomerDocumentForm,
    CustomerDocumentReviewForm
)


def get_user_company(user):
    """Helper function to get user's company"""
    # For now, just return the first company since UserProfile doesn't have company relationships
    return Company.objects.first()


@login_required
def customer_list(request):
    """List all customers"""
    user_company = get_user_company(request.user)
    customers = Customer.objects.filter(company=user_company).order_by('-created_at')
    
    # Calculate statistics
    total_customers = customers.count()
    individual_customers = customers.filter(customer_type='individual').count()
    business_customers = customers.filter(customer_type='business').count()
    active_customers = customers.filter(is_active=True).count()
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        customers = customers.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone_primary__icontains=search_query) |
            Q(customer_id__icontains=search_query) |
            Q(national_id__icontains=search_query)
        )
    
    # Filter by customer type
    customer_type = request.GET.get('type', '')
    if customer_type:
        customers = customers.filter(customer_type=customer_type)
    
    # Filter by status
    status = request.GET.get('status', '')
    if status:
        is_active = status == 'active'
        customers = customers.filter(is_active=is_active)
    
    paginator = Paginator(customers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'loans_customers/customer_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'customer_type': customer_type,
        'status': status,
        'customer_type_choices': Customer.CUSTOMER_TYPE,
        # Statistics
        'total_customers': total_customers,
        'individual_customers': individual_customers,
        'business_customers': business_customers,
        'active_customers': active_customers,
    })


@login_required
def customer_detail(request, pk):
    """View customer details"""
    user_company = get_user_company(request.user)
    customer = get_object_or_404(Customer, pk=pk, company=user_company)
    
    # Get customer statistics
    stats = {
        'total_applications': LoanApplication.objects.filter(
            company=user_company, customer=customer
        ).count(),
        'active_loans': Loan.objects.filter(
            company=user_company, customer=customer, status='active'
        ).count(),
        'total_documents': CustomerDocument.objects.filter(
            company=user_company, customer=customer
        ).count(),
    }
    
    # Recent applications
    recent_applications = LoanApplication.objects.filter(
        company=user_company, customer=customer
    ).select_related('loan_product').order_by('-created_at')[:5]
    
    # Active loans
    active_loans = Loan.objects.filter(
        company=user_company, customer=customer, status='active'
    ).select_related('loan_product').order_by('-created_at')[:5]
    
    # Recent documents
    recent_documents = CustomerDocument.objects.filter(
        company=user_company, customer=customer
    ).order_by('-created_at')[:10]
    
    return render(request, 'loans_customers/customer_detail.html', {
        'customer': customer,
        'stats': stats,
        'recent_applications': recent_applications,
        'active_loans': active_loans,
        'recent_documents': recent_documents,
    })


@login_required
def customer_create(request):
    """Create a new customer"""
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.company = get_user_company(request.user)
            customer.created_by = request.user
            customer.save()
            messages.success(request, f'Customer "{customer.full_name}" created successfully.')
            return redirect('loans_customers:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm()
    
    return render(request, 'loans_customers/customer_form.html', {
        'form': form,
        'title': 'Create Customer',
    })


@login_required
def customer_quick_create(request):
    """Quick customer creation form"""
    if request.method == 'POST':
        form = QuickCustomerForm(request.POST)
        if form.is_valid():
            try:
                customer = form.save(commit=False)
                customer.company = get_user_company(request.user)
                customer.created_by = request.user
                customer.save()
                
                # Return JSON response for AJAX calls
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'customer_id': customer.customer_id,
                        'customer_pk': customer.pk,
                        'customer_name': customer.full_name,
                        'message': f'Customer "{customer.full_name}" created successfully.'
                    })
                
                messages.success(request, f'Customer "{customer.full_name}" created successfully.')
                return redirect('loans_customers:customer_detail', pk=customer.pk)
                
            except Exception as e:
                # Handle any database errors (like duplicate email/national_id)
                error_msg = str(e)
                if 'UNIQUE constraint failed' in error_msg:
                    if 'email' in error_msg:
                        error_msg = 'A customer with this email already exists.'
                    elif 'national_id' in error_msg:
                        error_msg = 'A customer with this National ID already exists.'
                    else:
                        error_msg = 'A customer with these details already exists.'
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': error_msg
                    })
                
                messages.error(request, error_msg)
        else:
            # Form validation errors
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Please correct the errors below.',
                    'errors': form.errors
                })
    else:
        form = QuickCustomerForm()
    
    return render(request, 'loans_customers/customer_quick_form.html', {
        'form': form,
        'title': 'Quick Customer Creation',
    })


@login_required
def customer_edit(request, pk):
    """Edit a customer"""
    user_company = get_user_company(request.user)
    customer = get_object_or_404(Customer, pk=pk, company=user_company)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.updated_by = request.user
            customer.save()
            messages.success(request, f'Customer "{customer.full_name}" updated successfully.')
            return redirect('loans_customers:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm(instance=customer)
    
    return render(request, 'loans_customers/customer_form.html', {
        'form': form,
        'customer': customer,
        'title': 'Edit Customer',
    })


@login_required
def customer_documents(request, pk):
    """View customer documents"""
    user_company = get_user_company(request.user)
    customer = get_object_or_404(Customer, pk=pk, company=user_company)
    
    documents = CustomerDocument.objects.filter(
        company=user_company, customer=customer
    ).order_by('-created_at')
    
    # Filter by document type
    doc_type = request.GET.get('type', '')
    if doc_type:
        documents = documents.filter(document_type=doc_type)
    
    # Filter by status
    status = request.GET.get('status', '')
    if status:
        documents = documents.filter(status=status)
    
    paginator = Paginator(documents, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'loans_customers/customer_documents.html', {
        'customer': customer,
        'page_obj': page_obj,
        'doc_type': doc_type,
        'status': status,
        'document_type_choices': CustomerDocument.DOCUMENT_TYPE,
        'status_choices': CustomerDocument.DOCUMENT_STATUS,
    })


@login_required
def customer_document_upload(request, pk):
    """Upload a document for a customer"""
    user_company = get_user_company(request.user)
    customer = get_object_or_404(Customer, pk=pk, company=user_company)
    
    if request.method == 'POST':
        form = CustomerDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.company = user_company
            document.customer = customer
            document.uploaded_by = request.user
            document.save()
            messages.success(request, f'Document "{document.name}" uploaded successfully.')
            return redirect('loans_customers:customer_documents', pk=customer.pk)
    else:
        form = CustomerDocumentForm()
    
    return render(request, 'loans_customers/customer_document_form.html', {
        'form': form,
        'customer': customer,
        'title': 'Upload Document',
    })


@login_required
def customer_document_review(request, customer_pk, doc_pk):
    """Review a customer document"""
    user_company = get_user_company(request.user)
    customer = get_object_or_404(Customer, pk=customer_pk, company=user_company)
    document = get_object_or_404(
        CustomerDocument, pk=doc_pk, customer=customer, company=user_company
    )
    
    if request.method == 'POST':
        form = CustomerDocumentReviewForm(request.POST, instance=document)
        if form.is_valid():
            document = form.save(commit=False)
            document.reviewed_by = request.user
            document.reviewed_at = timezone.now()
            document.save()
            messages.success(request, f'Document "{document.name}" review updated.')
            return redirect('loans_customers:customer_documents', pk=customer.pk)
    else:
        form = CustomerDocumentReviewForm(instance=document)
    
    return render(request, 'loans_customers/customer_document_review.html', {
        'form': form,
        'customer': customer,
        'document': document,
        'title': 'Review Document',
    })






@login_required
def customer_search(request):
    """Search customers (AJAX endpoint)"""
    user_company = get_user_company(request.user)
    
    if request.method == 'GET':
        query = request.GET.get('query', '').strip()
        if query:
            customers = Customer.objects.filter(
                company=user_company
            ).filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query) |
                Q(customer_id__icontains=query) |
                Q(national_id__icontains=query)
            )[:10]  # Limit to 10 results
            
            customer_data = []
            for customer in customers:
                customer_data.append({
                    'id': customer.pk,
                    'name': customer.full_name,
                    'email': customer.email,
                    'phone': customer.phone_primary,
                    'customer_id': customer.customer_id,
                })
            
            return JsonResponse({
                'success': True,
                'customers': customer_data,
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def customer_toggle_status(request, pk):
    """Toggle customer active status"""
    user_company = get_user_company(request.user)
    customer = get_object_or_404(Customer, pk=pk, company=user_company)
    
    if request.method == 'POST':
        customer.is_active = not customer.is_active
        customer.updated_by = request.user
        customer.save()
        
        status = 'activated' if customer.is_active else 'deactivated'
        messages.success(request, f'Customer "{customer.full_name}" {status} successfully.')
        
        return JsonResponse({
            'success': True,
            'is_active': customer.is_active,
            'status': status,
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def customer_delete(request, pk):
    """Delete a customer and all associated data"""
    user_company = get_user_company(request.user)
    customer = get_object_or_404(Customer, pk=pk, company=user_company)
    
    if request.method == 'POST':
        try:
            customer_name = customer.full_name
            customer_id = customer.customer_id
            
            # Check if customer has active loans
            from loans_core.models import Loan
            active_loans = Loan.objects.filter(
                company=user_company, 
                customer=customer, 
                status__in=['pending', 'approved', 'active']
            ).count()
            
            if active_loans > 0:
                return JsonResponse({
                    'success': False,
                    'error': f'Cannot delete customer with {active_loans} active loan(s). Please close all loans first.'
                })
            
            # Delete the customer (this will cascade delete related documents, etc.)
            customer.delete()
            
            messages.success(request, f'Customer "{customer_name}" (ID: {customer_id}) deleted successfully.')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Customer "{customer_name}" deleted successfully.'
                })
            else:
                return redirect('loans_customers:customer_list')
                
        except Exception as e:
            error_msg = f'Error deleting customer: {str(e)}'
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                })
            else:
                messages.error(request, error_msg)
                return redirect('loans_customers:customer_detail', pk=pk)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

