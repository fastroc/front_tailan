"""
Upload viewlogger = logging.getLogger(__name__)


# # @login_required
@require_http_methods(["GET", "POST"])
def upload_csv_view(request):g Resilient Architecture.
Follows Service Layer pattern with error isolation.
"""
import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from ..forms import CSVUploadForm
from ..services.orchestrator import ReconciliationOrchestrator
from ..utils.exceptions import ReconciliationBaseException
from ..utils.feature_flags import check_feature_enabled

logger = logging.getLogger(__name__)


# @login_required
@require_http_methods(["GET", "POST"])
def upload_csv(request):
    """
    Upload CSV file view with resilient architecture.
    Uses orchestrator pattern and feature flags.
    """
    # Check if upload feature is enabled
    if not check_feature_enabled('FILE_UPLOAD_ENABLED'):
        messages.warning(
            request, 
            'File upload is temporarily disabled. Please try again later.'
        )
        return redirect('reconciliation:file_list')
    
    orchestrator = ReconciliationOrchestrator()
    
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Use orchestrator for coordinated operation
                result = orchestrator.upload_and_process_file(
                    file=request.FILES['file'],
                    user=request.user,
                    bank_account_name=form.cleaned_data.get('bank_account_name'),
                    statement_period=form.cleaned_data.get('statement_period'),
                    auto_process=False  # Manual processing workflow
                )
                
                if result['success']:
                    messages.success(
                        request,
                        f'File "{result["uploaded_file"].file_name}" uploaded successfully! '
                        'You can now process it.'
                    )
                    return redirect('reconciliation:process_file', file_id=result['uploaded_file'].id)
                else:
                    messages.error(request, f'Upload failed: {result["error"]}')
                    
            except ReconciliationBaseException as e:
                logger.error(f"Upload error for user {request.user.id}: {e}")
                messages.error(request, f'Upload failed: {e.message}')
            except Exception as e:
                logger.error(f"Unexpected upload error: {e}")
                messages.error(request, 'An unexpected error occurred. Please try again.')
    else:
        form = CSVUploadForm()
    
    context = {
        'form': form,
        'title': 'Upload Bank Statement CSV',
        'upload_enabled': check_feature_enabled('FILE_UPLOAD_ENABLED'),
        'processing_enabled': check_feature_enabled('CSV_PROCESSING_ENABLED')
    }
    return render(request, 'reconciliation/upload.html', context)


# @login_required
@require_http_methods(["GET", "POST"])
def process_file(request, file_id):
    """
    Process uploaded CSV file view with resilient architecture.
    """
    # Check if processing feature is enabled
    if not check_feature_enabled('CSV_PROCESSING_ENABLED'):
        messages.warning(
            request,
            'File processing is temporarily disabled. Please try again later.'
        )
        return redirect('reconciliation:file_list')
    
    orchestrator = ReconciliationOrchestrator()
    
    try:
        # Get file using upload service (with access control)
        uploaded_file = orchestrator.upload_service.get_file_by_id(file_id, request.user)
        
        if uploaded_file.is_processed:
            messages.info(request, 'This file has already been processed.')
            return redirect('reconciliation:file_detail', file_id=file_id)
        
        if request.method == 'POST':
            try:
                # Use process service
                stats = orchestrator.process_service.process_file(uploaded_file)
                
                messages.success(
                    request,
                    f'File processed successfully! {stats["imported"]} transactions imported '
                    f'out of {stats["extracted"]} rows processed.'
                )
                return redirect('reconciliation:file_detail', file_id=file_id)
                
            except ReconciliationBaseException as e:
                logger.error(f"Processing error for file {file_id}: {e}")
                messages.error(request, f'Processing failed: {e.message}')
            except Exception as e:
                logger.error(f"Unexpected processing error: {e}")
                messages.error(request, 'Processing failed due to an unexpected error.')
    
    except ReconciliationBaseException as e:
        messages.error(request, f'File access error: {e.message}')
        return redirect('reconciliation:file_list')
    except Exception as e:
        logger.error(f"Unexpected error accessing file {file_id}: {e}")
        messages.error(request, 'File not found or access denied.')
        return redirect('reconciliation:file_list')
    
    context = {
        'uploaded_file': uploaded_file,
        'title': 'Process Bank Statement File',
        'processing_enabled': check_feature_enabled('CSV_PROCESSING_ENABLED')
    }
    return render(request, 'reconciliation/process.html', context)


def file_list(request):
    """
    List all uploaded files - simplified working version.
    """
    try:
        from ..models import UploadedFile
        
        # Get all files to show something
        files = UploadedFile.objects.all().prefetch_related('transactions')
        
        # Calculate statistics
        processed_count = sum(1 for file in files if file.is_processed) if files else 0
        pending_count = sum(1 for file in files if not file.is_processed) if files else 0
        total_transactions = sum(file.transactions.count() for file in files if file.is_processed) if files else 0
        
        context = {
            'files': files,
            'processed_count': processed_count,
            'pending_count': pending_count,
            'total_transactions': total_transactions,
            'title': 'Bank Reconciliation Dashboard'
        }
        
        return render(request, 'reconciliation/file_list_simple.html', context)
        
    except Exception as e:
        # Return simple error page instead of server error
        context = {
            'files': [],
            'processed_count': 0,
            'pending_count': 0,
            'total_transactions': 0,
            'title': 'Bank Reconciliation Dashboard',
            'error_message': f'Error loading data: {str(e)}'
        }
        return render(request, 'reconciliation/file_list_simple.html', context)


# @login_required
def file_detail(request, file_id):
    """
    Show file details and transactions with resilient data loading.
    """
    orchestrator = ReconciliationOrchestrator()
    
    try:
        # Get file using service
        uploaded_file = orchestrator.upload_service.get_file_by_id(file_id, request.user)
        
        # Get processing stats
        processing_stats = orchestrator.process_service.get_processing_stats(uploaded_file)
        
        # Get transactions (with error isolation)
        transactions = []
        total_transactions = 0
        try:
            transactions = uploaded_file.transactions.all()[:20]  # First 20
            total_transactions = uploaded_file.transactions.count()
        except Exception as e:
            logger.warning(f"Failed to load transactions for file {file_id}: {e}")
        
        context = {
            'uploaded_file': uploaded_file,
            'transactions': transactions,
            'total_transactions': total_transactions,
            'processing_stats': processing_stats,
            'title': f'File Details - {uploaded_file.file_name}'
        }
        
    except ReconciliationBaseException as e:
        messages.error(request, f'File access error: {e.message}')
        return redirect('reconciliation:file_list')
    except Exception as e:
        logger.error(f"Unexpected error loading file {file_id}: {e}")
        messages.error(request, 'File not found or access denied.')
        return redirect('reconciliation:file_list')
    
    return render(request, 'reconciliation/file_detail.html', context)


# @login_required
def health_check(request):
    """
    System health check endpoint.
    """
    orchestrator = ReconciliationOrchestrator()
    health_status = orchestrator.health_check()
    
    return JsonResponse(health_status)


def showcase(request):
    """Showcase the reconciliation process with sample data"""
    context = {
        'title': 'Reconciliation Process Showcase'
    }
    return render(request, 'reconciliation/showcase.html', context)


def transaction_detail(request, transaction_id):
    """Show transaction detail with matching interface"""
    # Generate sample transactions for demonstration
    from datetime import datetime, timedelta
    
    sample_transactions = []
    base_date = datetime.now()
    
    # Create 25 sample transactions for demonstration
    transaction_data = [
        ("Salary Transfer 649", 250000, "Monthly salary payment", "PAYROLL"),
        ("Office Rent Payment", -12000, "Monthly office lease payment", "RENT-001"),
        ("Utility Bill - Electric", -850, "Monthly electricity bill payment", "UTIL-E-001"),
        ("Client Payment - ABC Corp", 45000, "Invoice #1001 payment received", "INV-1001"),
        ("Marketing Expenses", -3500, "Digital advertising campaign", "MKT-Q1-001"),
        ("Bank Service Charges", -25, "Monthly banking fees", "BANK-FEE"),
        ("Office Supplies Purchase", -450, "Stationery and office materials", "SUP-001"),
        ("Consultant Fee Payment", -8000, "Legal consultation services", "CONS-LEG-001"),
        ("Client Payment - XYZ Ltd", 32000, "Invoice #1002 payment received", "INV-1002"),
        ("Travel Reimbursement", -1200, "Employee travel expenses", "TRV-EMP-001"),
        ("Insurance Premium", -2800, "Quarterly business insurance", "INS-Q1-001"),
        ("Software License Fee", -599, "Monthly software subscription", "SOFT-001"),
        ("Petty Cash Withdrawal", -200, "Office petty cash replenishment", "CASH-001"),
        ("Client Payment - DEF Inc", 28500, "Invoice #1003 payment received", "INV-1003"),
        ("Internet Service Bill", -125, "Monthly internet connection", "UTIL-I-001"),
        ("Equipment Purchase", -5500, "New laptop and printer", "EQUIP-001"),
        ("Freelancer Payment", -2000, "Graphic design services", "FREE-GFX-001"),
        ("Client Refund", -750, "Service cancellation refund", "REF-001"),
        ("Phone Bill", -95, "Monthly business phone service", "UTIL-P-001"),
        ("Training Course Fee", -1500, "Employee skill development", "TRN-001"),
        ("Vendor Payment - Supplies", -680, "Monthly supplier payment", "VEN-SUP-001"),
        ("Interest Income", 125, "Bank account interest earned", "INT-001"),
        ("Parking Fees", -45, "Monthly parking space rental", "PARK-001"),
        ("Client Payment - GHI Corp", 19500, "Invoice #1004 payment received", "INV-1004"),
        ("Maintenance Service", -380, "Office equipment maintenance", "MAINT-001"),
    ]
    
    for i, (desc, amount, memo, ref) in enumerate(transaction_data):
        sample_transactions.append({
            'id': i + 1,
            'date': base_date - timedelta(days=i),
            'description': desc,
            'memo': memo,
            'reference': ref,
            'amount': amount,
        })
    
    # Current transaction being matched
    current_transaction = {
        'id': transaction_id,
        'date': datetime.now().date(),
        'description': 'Salary Transfer 649',
        'memo': 'Monthly salary payment for January 2025',
        'reference': 'PAYROLL-JAN-2025',
        'amount': 250000,
    }
    
    context = {
        'transaction': current_transaction,
        'transactions': sample_transactions,
        'title': 'Transaction Details & Matching',
        'transaction_id': transaction_id
    }
    return render(request, 'reconciliation/transaction_detail.html', context)
