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
    CustomerDocumentReviewForm, CustomerBulkUploadForm
)
from django.db import connection
from django.conf import settings


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
    
    # Get database backend information
    db_engine = settings.DATABASES['default']['ENGINE']
    db_name = settings.DATABASES['default']['NAME']
    
    # Simplify database engine name for display
    if 'postgresql' in db_engine:
        db_backend = 'PostgreSQL'
    elif 'sqlite' in db_engine:
        db_backend = 'SQLite'
    elif 'mysql' in db_engine:
        db_backend = 'MySQL'
    else:
        db_backend = db_engine.split('.')[-1].upper()
    
    # Get recent loan applications with their loan numbers
    recent_applications = LoanApplication.objects.filter(
        company=user_company
    ).select_related('customer').order_by('-created_at')[:10]
    
    # Create a list with application and corresponding loan info
    applications_with_loans = []
    for app in recent_applications:
        loan_info = None
        try:
            # Try to find the loan created from this application
            loan = Loan.objects.get(
                customer=app.customer,
                company=app.company,
                principal_amount=app.approved_amount or app.requested_amount
            )
            loan_info = {
                'loan_number': loan.loan_number,
                'status': loan.status
            }
        except (Loan.DoesNotExist, Loan.MultipleObjectsReturned):
            loan_info = None
        
        applications_with_loans.append({
            'application': app,
            'loan': loan_info
        })
    
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
        # Database info
        'db_backend': db_backend,
        'db_name': db_name,
        # Loan applications with loan numbers
        'applications_with_loans': applications_with_loans,
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


@login_required
def customer_bulk_upload(request):
    """Bulk upload customers from Excel/CSV file"""
    if request.method == 'POST':
        form = CustomerBulkUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            user_company = get_user_company(request.user)
            
            try:
                # Import pandas for file processing
                import pandas as pd
                from decimal import Decimal, InvalidOperation
                
                # Read the file
                if file.name.lower().endswith('.xlsx'):
                    df = pd.read_excel(file)
                else:  # CSV
                    df = pd.read_csv(file)
                
                success_count = 0
                errors = []
                
                for index, row in df.iterrows():
                    try:
                        # Validate required fields
                        required_fields = ['customer_type', 'first_name', 'last_name', 'email', 'phone', 'national_id']
                        missing_fields = []
                        
                        for field in required_fields:
                            value = row.get(field)
                            if pd.isna(value) or str(value).strip() == '':
                                missing_fields.append(field)
                        
                        if missing_fields:
                            errors.append(f"Row {index + 2}: Missing required fields: {', '.join(missing_fields)}")
                            continue
                        
                        # Handle optional fields
                        date_of_birth = None
                        if not pd.isna(row.get('date_of_birth')) and str(row.get('date_of_birth')).strip():
                            try:
                                date_of_birth = pd.to_datetime(row['date_of_birth']).date()
                            except (ValueError, TypeError, pd.errors.ParserError):
                                errors.append(f"Row {index + 2}: Invalid date format for date_of_birth (use YYYY-MM-DD)")
                                continue
                        
                        monthly_income = None
                        if not pd.isna(row.get('monthly_income')) and str(row.get('monthly_income')).strip():
                            try:
                                monthly_income = Decimal(str(row['monthly_income']))
                            except (ValueError, InvalidOperation):
                                errors.append(f"Row {index + 2}: Invalid monthly_income format (use numbers only)")
                                continue
                        
                        employment_type = None
                        if not pd.isna(row.get('employment_type')) and str(row.get('employment_type')).strip():
                            employment_type = str(row['employment_type']).strip().lower()
                            valid_employment_types = [choice[0] for choice in Customer.EMPLOYMENT_TYPE]
                            if employment_type not in valid_employment_types:
                                employment_type = None  # Set to null if invalid
                        
                        # Validate customer_type
                        customer_type = str(row['customer_type']).strip().lower()
                        if customer_type not in ['individual', 'business']:
                            errors.append(f"Row {index + 2}: Invalid customer_type. Use 'Individual' or 'Business'")
                            continue
                        
                        # Check for duplicate email in this company
                        email = str(row['email']).strip().lower()
                        if Customer.objects.filter(company=user_company, email=email).exists():
                            errors.append(f"Row {index + 2}: Customer with email '{email}' already exists")
                            continue
                        
                        # Check for duplicate national_id in this company
                        national_id = str(row['national_id']).strip()
                        if Customer.objects.filter(company=user_company, national_id=national_id).exists():
                            errors.append(f"Row {index + 2}: Customer with National ID '{national_id}' already exists")
                            continue
                        
                        # Create customer
                        customer = Customer.objects.create(
                            company=user_company,
                            created_by=request.user,
                            customer_type=customer_type,
                            first_name=str(row['first_name']).strip(),
                            last_name=str(row['last_name']).strip(),
                            email=email,
                            phone_primary=str(row['phone']).strip(),
                            national_id=national_id,
                            date_of_birth=date_of_birth,
                            monthly_income=monthly_income,
                            employment_type=employment_type,
                            # Set default address fields
                            street_address=str(row.get('address', '')).strip() or 'Not Provided',
                            city=str(row.get('city', '')).strip() or 'Not Provided',
                            state_province=str(row.get('state', '')).strip() or 'Not Provided',
                            postal_code=str(row.get('postal_code', '')).strip() or 'Not Provided',
                            country=str(row.get('country', 'United States')).strip(),
                            is_active=True
                        )
                        
                        success_count += 1
                        
                    except Exception as e:
                        errors.append(f"Row {index + 2}: {str(e)}")
                        continue
                
                # Show results
                if success_count > 0:
                    messages.success(request, f'✅ Successfully created {success_count} customers!')
                
                if errors:
                    error_msg = f'⚠️ {len(errors)} errors occurred:\n' + '\n'.join(errors[:10])
                    if len(errors) > 10:
                        error_msg += f'\n... and {len(errors) - 10} more errors'
                    messages.error(request, error_msg)
                
            except ImportError:
                messages.error(request, '❌ Pandas library not installed. Cannot process Excel/CSV files.')
            except Exception as e:
                messages.error(request, f'❌ File processing error: {str(e)}')
        
        return redirect('loans_customers:customer_bulk_upload')
    
    else:
        form = CustomerBulkUploadForm()
    
    return render(request, 'loans_customers/customer_bulk_upload.html', {
        'form': form,
        'title': 'Bulk Upload Customers',
    })

