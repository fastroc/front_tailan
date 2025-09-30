"""
Payment processing functionality with industry-standard allocation logic
"""
from decimal import Decimal, InvalidOperation
import pandas as pd
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db import transaction
from django.db import models
from django.core.exceptions import ValidationError
import datetime

from company.models import Company
from loans_core.models import Loan
from .models import Payment, PaymentProcessor


def serialize_for_session(data):
    """Convert Decimal objects to float for JSON serialization in session"""
    if isinstance(data, dict):
        return {key: serialize_for_session(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [serialize_for_session(item) for item in data]
    elif isinstance(data, Decimal):
        return float(data)
    else:
        return data


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
    
    # Get active loans for dropdown (real data from database)
    active_loans = Loan.objects.filter(
        company=company,
        status__in=['active', 'disbursed', 'current']  # Only show loans that are disbursed and active
    ).select_related('customer', 'loan_product').order_by('loan_number')
    
    # Optimized: Get recent payments with proper relationships and pagination
    from django.core.paginator import Paginator
    
    payments_queryset = Payment.objects.filter(
        loan__company=company
    ).select_related(
        'loan', 
        'loan__customer', 
        'loan__loan_product',
        'loan__application'  # Include application data
    ).prefetch_related(
        'loan__customer'  # Prefetch customer data
    ).order_by('-payment_date', '-created_at')
    
    # Add pagination for performance - limit to 25 payments per page
    paginator = Paginator(payments_queryset, 25)
    page_number = request.GET.get('page')
    payments = paginator.get_page(page_number)
    
    # Base queryset: payments for this company's loans
    base_payments_queryset = Payment.objects.filter(
        loan__company=company  # ✅ FIX: Filter by loan's company field
    ).select_related('loan', 'loan__customer')
    
    # ✅ ADDITIONAL VALIDATION: Double-check that these are truly loan payments
    # Filter out any payments that might have been incorrectly created for non-loan GL accounts
    validated_payments = []
    for payment in base_payments_queryset:
        # Check if the payment's loan has a valid principal account
        try:
            # Get the loan's configured GL account (if any)
            from loan_reconciliation_bridge.models import LoanGLConfiguration
            gl_config = LoanGLConfiguration.objects.filter(company=company).first()
            
            # If there's a GL configuration, verify this loan uses proper loan accounts
            if gl_config:
                # This is a valid loan payment if it's linked to a properly configured loan
                validated_payments.append(payment.id)
            else:
                # No GL configuration - assume all loan payments are valid for now
                validated_payments.append(payment.id)
                
        except ImportError:
            # loan_reconciliation_bridge not available - include all payments
            validated_payments.append(payment.id)
    
    # Apply the validation filter
    all_payments_queryset = base_payments_queryset.filter(
        id__in=validated_payments
    ).order_by('-payment_date')
    
    # Paginate payments (50 per page for better performance)
    paginator = Paginator(all_payments_queryset, 50)
    page_number = request.GET.get('page', 1)
    all_payments = paginator.get_page(page_number)
    
    # Get payment source statistics (using the full queryset for stats)
    payment_source_stats = {
        'manual_count': all_payments_queryset.filter(data_source='manual').count(),
        'reconciliation_count': all_payments_queryset.filter(data_source='reconciliation').count(),
        'bulk_upload_count': all_payments_queryset.filter(data_source='bulk_upload').count(),
        'bank_verified_count': all_payments_queryset.filter(is_bank_verified=True).count(),
        'total_count': all_payments_queryset.count(),
    }
    
    return render(request, 'loans_payments/payment_list_hybrid.html', {
        'stats': stats,
        'active_loans': active_loans,
        'recent_payments': all_payments,  # Now contains all payments
        'payment_source_stats': payment_source_stats,  # Add source statistics
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
                    created_by=request.user,
                    # === THREE-TIER SYSTEM FIELDS ===
                    data_source='manual',
                    reconciliation_status='not_required',  # Manual payments don't need bank reconciliation
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


@login_required
def bulk_payment_upload(request):
    """Bulk payment upload from Excel file"""
    company = get_user_company(request.user)
    
    if request.method == 'POST':
        if 'excel_file' not in request.FILES:
            messages.error(request, 'Please select an Excel file to upload.')
            return redirect('loans_payments:bulk_payment_upload')
        
        excel_file = request.FILES['excel_file']
        
        # Validate file type
        if not excel_file.name.endswith(('.xlsx', '.xls')):
            messages.error(request, 'Please upload a valid Excel file (.xlsx or .xls).')
            return redirect('loans_payments:bulk_payment_upload')
        
        try:
            # Read Excel file
            df = pd.read_excel(excel_file)
            
            # Validate required columns
            required_columns = ['loan_number', 'payment_amount', 'payment_date', 'payment_method']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                messages.error(request, f'Missing required columns: {", ".join(missing_columns)}')
                return redirect('loans_payments:bulk_payment_upload')
            
            # Process payments
            results = process_bulk_payments(df, company, request.user)
            
            # Display results
            if results['success_count'] > 0:
                messages.success(request, f'Successfully processed {results["success_count"]} payments.')
            
            if results['error_count'] > 0:
                messages.warning(request, f'{results["error_count"]} payments failed to process.')
                
            # Store all results in session for display
            results_to_store = {
                'success_count': results['success_count'],
                'error_count': results['error_count'], 
                'duplicate_count': results['duplicate_count'],
                'review_count': results.get('review_count', 0),
                'errors': results['errors'],
                'duplicates': results.get('duplicates', [])
            }
            request.session['bulk_upload_results'] = serialize_for_session(results_to_store)
            
            return redirect('loans_payments:bulk_payment_results')
            
        except Exception as e:
            messages.error(request, f'Error processing file: {str(e)}')
            return redirect('loans_payments:bulk_payment_upload')
    
    # GET request - show upload form
    return render(request, 'loans_payments/bulk_payment_upload.html', {
        'title': 'Bulk Payment Upload',
        'company': company,
    })


@login_required
def bulk_payment_results(request):
    """Display bulk payment upload results"""
    company = get_user_company(request.user)
    
    # Get results from session (fallback to old method for backward compatibility)
    upload_results = request.session.pop('bulk_upload_results', {})
    errors = request.session.pop('bulk_upload_errors', upload_results.get('errors', []))
    
    return render(request, 'loans_payments/bulk_payment_results.html', {
        'title': 'Bulk Payment Results',
        'errors': errors,
        'success_count': upload_results.get('success_count', 0),
        'error_count': upload_results.get('error_count', 0),
        'duplicate_count': upload_results.get('duplicate_count', 0),
        'review_count': upload_results.get('review_count', 0),
        'duplicates': upload_results.get('duplicates', []),
        'company': company,
    })


@login_required
def download_payment_template(request):
    """Download Excel template for bulk payment upload"""
    company = get_user_company(request.user)
    
    # Get real loan numbers from the user's company
    from loans_core.models import Loan
    real_loans = Loan.objects.filter(company=company).order_by('-created_at')[:3]
    
    if real_loans.exists():
        loan_numbers = [loan.loan_number for loan in real_loans]
        customer_names = [loan.customer.first_name for loan in real_loans]
    else:
        # Fallback to sample data if no loans exist
        loan_numbers = ['LN2025276551', 'LN2025276552', 'LN2025276553']
        customer_names = ['Одончимэг', 'Батбаяр', 'Сарангэрэл']
    
    # Create sample data with real loan numbers
    sample_data = {
        'loan_number': loan_numbers,
        'first_name': customer_names,
        'payment_amount': [1500.00, 2000.00, 850.00],
        'payment_date': ['2025-01-15', '2025-01-15', '2025-01-16'],
        'payment_method': ['bank_transfer', 'cash', 'check'],
        'reference_number': ['TXN123456', '', 'CHK789'],
        'payment_type': ['regular', 'regular', 'prepayment'],
        'notes': ['Monthly payment', 'Cash payment received', 'Extra principal payment'],
    }
    
    # Create DataFrame
    df = pd.DataFrame(sample_data)
    
    # Create Excel file in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Payments', index=False)
        
        # Add instructions sheet
        instructions = pd.DataFrame({
            'Field': [
                'loan_number',
                'first_name',
                'payment_amount',
                'payment_date',
                'payment_method',
                'reference_number',
                'payment_type',
                'notes'
            ],
            'Required': [
                'YES',
                'NO',
                'YES', 
                'YES',
                'YES',
                'NO',
                'NO',
                'NO'
            ],
            'Description': [
                'Existing loan number (e.g., LN2025276551)',
                'Customer first name for verification (e.g., Одончимэг)',
                'Payment amount in decimal format (e.g., 1500.00)',
                'Payment date in YYYY-MM-DD, YYYY.MM.DD, MM/DD/YYYY, DD/MM/YYYY, or DD.MM.YYYY format',
                'One of: cash, check, bank_transfer, ach, credit_card, debit_card, money_order, wire_transfer, online, mobile_app',
                'Reference number, check number, transaction ID (optional)',
                'One of: regular, prepayment, late_payment, payoff, fee_payment, partial (default: regular)',
                'Additional notes about the payment (optional)'
            ]
        })
        instructions.to_excel(writer, sheet_name='Instructions', index=False)
    
    output.seek(0)
    
    # Create response
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="payment_upload_template.xlsx"'
    
    return response


def process_bulk_payments(df, company, user):
    """Process bulk payments from DataFrame with duplicate detection"""
    from .services import DuplicateDetectionService
    
    results = {
        'success_count': 0,
        'error_count': 0,
        'duplicate_count': 0,
        'review_count': 0,
        'errors': [],
        'duplicates': [],
        'review_items': [],
        'processed_payments': []
    }
    
    # Initialize duplicate detection
    duplicate_service = DuplicateDetectionService(company=company, strict_mode=True)
    
    # Define payment method choices for validation
    VALID_PAYMENT_METHODS = [
        'cash', 'check', 'bank_transfer', 'ach', 'credit_card', 
        'debit_card', 'money_order', 'wire_transfer', 'online', 'mobile_app'
    ]
    
    VALID_PAYMENT_TYPES = [
        'regular', 'prepayment', 'late_payment', 'payoff', 'fee_payment', 'partial'
    ]
    
    # Convert DataFrame to list for batch duplicate detection
    payment_data_list = []
    for index, row in df.iterrows():
        try:
            payment_data = {
                'row_number': index + 2,  # Excel row number (1-based + header)
                'loan_number': str(row['loan_number']).strip(),
                'payment_amount': Decimal(str(row['payment_amount'])),
                'payment_date': str(row['payment_date']).strip(),
                'payment_method': str(row['payment_method']).strip().lower(),
                'reference_number': str(row.get('reference_number', '')).strip(),
                'payment_type': str(row.get('payment_type', 'regular')).strip().lower(),
                'notes': str(row.get('notes', '')).strip(),
                'customer_first_name': str(row.get('first_name', '')).strip()
            }
            payment_data_list.append(payment_data)
        except Exception as e:
            results['error_count'] += 1
            results['errors'].append(f'Row {index + 2}: Data parsing error - {str(e)}')
    
    # Perform batch duplicate detection
    duplicate_results = duplicate_service.batch_duplicate_check(payment_data_list)
    
    # Process clean payments
    for payment_data in duplicate_results['clean_payments']:
        try:
            with transaction.atomic():
                # Extract and validate data
                loan_number = payment_data['loan_number']
                payment_amount = payment_data['payment_amount']
                payment_date_str = payment_data['payment_date']
                payment_method = payment_data['payment_method']
                reference_number = payment_data['reference_number']
                payment_type = payment_data['payment_type']
                notes = payment_data['notes']
                first_name = payment_data['customer_first_name']
                
                # Validate loan exists
                try:
                    loan = Loan.objects.get(loan_number=loan_number, company=company)
                except Loan.DoesNotExist:
                    raise ValidationError(f'Loan {loan_number} not found')
                
                # Optional customer verification
                if first_name:
                    customer = loan.customer
                    if hasattr(customer, 'first_name'):
                        if customer.first_name.lower() != first_name.lower():
                            raise ValidationError(f'Customer verification failed for loan {loan_number}: First name mismatch: expected {customer.first_name}, got {first_name}')
                
                # Validate payment amount
                if payment_amount <= 0:
                    raise ValidationError('Payment amount must be greater than zero')
                
                # Validate and parse payment date
                try:
                    if payment_date_str.lower() in ['today', 'now']:
                        payment_date = timezone.now().date()
                    else:
                        # Try different date formats
                        try:
                            payment_date = datetime.datetime.strptime(payment_date_str, '%Y-%m-%d').date()
                        except ValueError:
                            try:
                                payment_date = datetime.datetime.strptime(payment_date_str, '%Y.%m.%d').date()
                            except ValueError:
                                try:
                                    payment_date = datetime.datetime.strptime(payment_date_str, '%m/%d/%Y').date()
                                except ValueError:
                                    try:
                                        payment_date = datetime.datetime.strptime(payment_date_str, '%d/%m/%Y').date()
                                    except ValueError:
                                        try:
                                            payment_date = datetime.datetime.strptime(payment_date_str, '%d.%m.%Y').date()
                                        except ValueError:
                                            raise ValidationError(f'Invalid date format: {payment_date_str}. Use YYYY-MM-DD, YYYY.MM.DD, MM/DD/YYYY, DD/MM/YYYY, or DD.MM.YYYY')
                except Exception:
                    raise ValidationError(f'Invalid date: {payment_date_str}')
                
                # Validate payment method
                if payment_method not in VALID_PAYMENT_METHODS:
                    raise ValidationError(f'Invalid payment method: {payment_method}. Must be one of: {", ".join(VALID_PAYMENT_METHODS)}')
                
                # Validate payment type
                if payment_type not in VALID_PAYMENT_TYPES:
                    raise ValidationError(f'Invalid payment type: {payment_type}. Must be one of: {", ".join(VALID_PAYMENT_TYPES)}')
                
                # Create payment
                payment = Payment.objects.create(
                    company=company,
                    loan=loan,
                    customer=loan.customer,
                    payment_amount=payment_amount,
                    payment_date=payment_date,
                    payment_method=payment_method,
                    payment_type=payment_type,
                    reference_number=reference_number,
                    notes=notes,
                    processed_by=user,
                    created_by=user,
                    status='completed',  # Mark as completed for bulk uploads
                    # === THREE-TIER SYSTEM FIELDS ===
                    data_source='bulk_upload',
                    reconciliation_status='pending',  # Bulk uploads may need bank verification later
                )
                
                results['processed_payments'].append({
                    'payment_id': payment.payment_id,
                    'loan_number': loan_number,
                    'amount': payment_amount,
                    'date': payment_date,
                    'row_number': payment_data['row_number'],
                    'needs_review': payment_data.get('needs_review', False)
                })
                
                if payment_data.get('needs_review', False):
                    results['review_count'] += 1
                    results['review_items'].append({
                        'payment_id': payment.payment_id,
                        'row_number': payment_data['row_number'],
                        'loan_number': loan_number,
                        'reason': 'Potential duplicate detected - review recommended'
                    })
                else:
                    results['success_count'] += 1
                    
        except Exception as e:
            results['error_count'] += 1
            error_msg = f'Row {payment_data["row_number"]}: {str(e)}'
            results['errors'].append(error_msg)
            continue
    
    # Handle duplicates
    for duplicate in duplicate_results['duplicates_found']:
        results['duplicate_count'] += 1
        results['duplicates'].append({
            'row_number': duplicate['row_number'],
            'loan_number': duplicate.get('loan_number', 'Unknown'),
            'amount': duplicate.get('payment_amount', 0),
            'duplicate_type': duplicate.get('duplicate_type', 'UNKNOWN'),
            'reason': duplicate.get('reason', 'Duplicate detected'),
            'confidence': duplicate.get('duplicate_check', {}).get('confidence', 0.0),
            'matching_payments': [
                p.payment_id for p in duplicate.get('duplicate_check', {}).get('matching_payments', [])
            ]
        })
    
    # Handle internal duplicates
    for internal_dup in duplicate_results['internal_duplicates']:
        results['duplicate_count'] += 1
        results['duplicates'].append({
            'row_number': internal_dup['row_number'],
            'loan_number': internal_dup.get('loan_number', 'Unknown'),
            'amount': internal_dup.get('payment_amount', 0),
            'duplicate_type': 'INTERNAL',
            'reason': 'Duplicate within uploaded data',
            'confidence': 1.0
        })
    
    # Add summary statistics
    results['batch_summary'] = {
        'total_rows': len(payment_data_list),
        'clean_payments': len(duplicate_results['clean_payments']),
        'external_duplicates': duplicate_results['summary']['external_duplicates'],
        'internal_duplicates': duplicate_results['summary']['internal_duplicates'],
        'processing_errors': results['error_count']
    }
    
    return results


@login_required
def payment_edit(request, pk):
    """Edit an existing payment"""
    company = get_user_company(request.user)
    payment = get_object_or_404(Payment, pk=pk, company=company)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Extract form data
                payment_amount = Decimal(request.POST.get('payment_amount', '0'))
                payment_date_str = request.POST.get('payment_date', '')
                payment_method = request.POST.get('payment_method', '').strip().lower()
                reference_number = request.POST.get('reference_number', '').strip()
                notes = request.POST.get('notes', '').strip()
                
                # Validate amount
                if payment_amount <= 0:
                    raise ValidationError('Payment amount must be greater than zero')
                
                # Parse date
                try:
                    if payment_date_str.lower() in ['today', 'now']:
                        payment_date = timezone.now().date()
                    else:
                        # Try different date formats
                        try:
                            payment_date = datetime.datetime.strptime(payment_date_str, '%Y-%m-%d').date()
                        except ValueError:
                            try:
                                payment_date = datetime.datetime.strptime(payment_date_str, '%m/%d/%Y').date()
                            except ValueError:
                                try:
                                    payment_date = datetime.datetime.strptime(payment_date_str, '%d/%m/%Y').date()
                                except ValueError:
                                    raise ValidationError(f'Invalid date format: {payment_date_str}')
                except Exception:
                    raise ValidationError(f'Invalid date: {payment_date_str}')
                
                # Update payment
                payment.payment_amount = payment_amount
                payment.payment_date = payment_date
                payment.payment_method = payment_method
                payment.reference_number = reference_number
                payment.notes = notes
                payment.save()
                
                # Create history record
                from .models import PaymentHistory
                PaymentHistory.objects.create(
                    company=company,
                    payment=payment,
                    action_type='updated',
                    performed_by=request.user,
                    description=f'Payment updated by {request.user.username}'
                )
                
                messages.success(request, f'Payment {payment.payment_id} updated successfully!')
                return redirect('loans_payments:payment_detail', pk=payment.pk)
                
        except ValidationError as e:
            messages.error(request, f'Error updating payment: {str(e)}')
        except Exception as e:
            messages.error(request, f'Unexpected error: {str(e)}')
    
    # Get active loans for dropdown
    active_loans = Loan.objects.filter(company=company, status='active').select_related('customer')
    
    context = {
        'title': f'Edit Payment {payment.payment_id}',
        'payment': payment,
        'active_loans': active_loans,
        'payment_methods': [
            ('cash', 'Cash'),
            ('check', 'Check'),
            ('bank_transfer', 'Bank Transfer'),
            ('ach', 'ACH/Direct Debit'),
            ('credit_card', 'Credit Card'),
            ('debit_card', 'Debit Card'),
            ('money_order', 'Money Order'),
            ('wire_transfer', 'Wire Transfer'),
            ('online', 'Online Payment'),
            ('mobile_app', 'Mobile App'),
        ]
    }
    
    return render(request, 'loans_payments/payment_edit.html', context)


@login_required
@require_POST
def payment_delete(request, pk):
    """Delete a payment with confirmation"""
    company = get_user_company(request.user)
    payment = get_object_or_404(Payment, pk=pk, company=company)
    
    # Check if this is a reconciled transaction
    if payment.data_source == 'reconciliation':
        messages.warning(
            request, 
            f'⚠️ Cannot delete reconciled payment {payment.payment_id}. '
            'Reconciled transactions are automatically managed by the system. '
            'To remove this payment, you must delete the source reconciliation file '
            'or restart the reconciliation process, which will automatically delete '
            'all associated payments.'
        )
        return redirect('loans_payments:payment_list')
    
    try:
        with transaction.atomic():
            # Create history record before deletion
            from .models import PaymentHistory
            PaymentHistory.objects.create(
                company=company,
                payment=payment,
                action_type='cancelled',
                performed_by=request.user,
                description=f'Payment deleted by {request.user.username}',
                old_amount=payment.payment_amount
            )
            
            # Store payment info for message
            payment_id = payment.payment_id
            loan_number = payment.loan.loan_number
            amount = payment.payment_amount
            
            # Delete the payment
            payment.delete()
            
            messages.success(request, f'Payment {payment_id} for loan {loan_number} (${amount}) has been deleted.')
            
    except Exception as e:
        messages.error(request, f'Error deleting payment: {str(e)}')
    
    return redirect('loans_payments:payment_list')


@login_required
@require_POST
def payments_clear_all(request):
    """Clear all payments with confirmation"""
    company = get_user_company(request.user)
    
    # Check for confirmation
    if request.POST.get('confirm_clear') != 'yes':
        messages.error(request, 'Confirmation required to clear all payments.')
        return redirect('loans_payments:payment_list')
    
    try:
        with transaction.atomic():
            # Get count before deletion
            payment_count = Payment.objects.filter(company=company).count()
            
            if payment_count == 0:
                messages.info(request, 'No payments to clear.')
                return redirect('loans_payments:payment_list')
            
            # Create backup using our cleanup service
            from .services import PaymentDataCleanupService
            cleanup_service = PaymentDataCleanupService(company=company)
            backup_file = cleanup_service.create_backup_before_cleanup(f"clear_all_backup_{timezone.now().strftime('%Y%m%d_%H%M%S')}")
            
            # Delete all payments
            Payment.objects.filter(company=company).delete()
            
            messages.success(request, f'Successfully cleared {payment_count} payment{"s" if payment_count != 1 else ""}. Backup created: {backup_file}')
            
    except Exception as e:
        messages.error(request, f'Error clearing payments: {str(e)}')
    
    return redirect('loans_payments:payment_list')
