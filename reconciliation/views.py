from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .models import UploadedFile, BankTransaction, ProcessingLog
from .forms import CSVUploadForm


@login_required
def upload_csv(request):
    """Upload CSV bank statement file"""
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.save(commit=False)
            uploaded_file.uploaded_by = request.user
            uploaded_file.file_name = request.FILES['file'].name
            uploaded_file.file_size = request.FILES['file'].size
            uploaded_file.save()
            
            messages.success(
                request, 
                f'File "{uploaded_file.file_name}" uploaded successfully! You can now process it.'
            )
            return redirect('reconciliation:process_file', file_id=uploaded_file.id)
    else:
        form = CSVUploadForm()
    
    context = {
        'form': form,
        'title': 'Upload Bank Statement CSV'
    }
    return render(request, 'reconciliation/upload.html', context)


@login_required
def process_file(request, file_id):
    """Process uploaded CSV file and extract bank transactions"""
    try:
        uploaded_file = UploadedFile.objects.get(id=file_id, uploaded_by=request.user)
    except UploadedFile.DoesNotExist:
        messages.error(request, 'File not found or access denied.')
        return redirect('reconciliation:upload_csv')
    
    if uploaded_file.is_processed:
        messages.info(request, 'This file has already been processed.')
        return redirect('reconciliation:file_detail', file_id=file_id)
    
    if request.method == 'POST':
        # Process the CSV file
        success, error_message, stats = process_csv_file(uploaded_file)
        
        if success:
            uploaded_file.is_processed = True
            uploaded_file.processed_at = datetime.now()
            uploaded_file.save()
            
            messages.success(
                request,
                f'File processed successfully! {stats["imported"]} transactions imported.'
            )
            return redirect('reconciliation:file_detail', file_id=file_id)
        else:
            messages.error(request, f'Error processing file: {error_message}')
    
    context = {
        'uploaded_file': uploaded_file,
        'title': 'Process Bank Statement File'
    }
    return render(request, 'reconciliation/process.html', context)


def process_csv_file(uploaded_file):
    """Process CSV file and extract transactions"""
    try:
        # Create processing log
        log = ProcessingLog.objects.create(
            uploaded_file=uploaded_file,
            success=False,
            transactions_extracted=0,
            transactions_imported=0
        )
        
        # Read and parse CSV
        file_content = uploaded_file.file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(file_content))
        
        transactions_created = 0
        row_number = 0
        
        for row_number, row in enumerate(csv_reader, 1):
            try:
                # Parse date (try multiple formats)
                date_str = row.get('Date', '').strip()
                transaction_date = parse_date(date_str)
                
                # Parse amount
                amount_str = row.get('Amount', '').strip().replace(',', '').replace('$', '')
                try:
                    amount = Decimal(amount_str)
                except (InvalidOperation, ValueError):
                    continue  # Skip rows with invalid amounts
                
                # Create transaction
                BankTransaction.objects.create(
                    uploaded_file=uploaded_file,
                    row_number=row_number,
                    date=transaction_date,
                    amount=amount,
                    payee=row.get('Payee', '').strip()[:255],
                    description=row.get('Description', '').strip(),
                    reference=row.get('Reference', '').strip()[:100]
                )
                transactions_created += 1
                
            except Exception:
                # Log individual row errors but continue processing
                continue
        
        # Update log
        log.success = True
        log.transactions_extracted = row_number
        log.transactions_imported = transactions_created
        log.save()
        
        return True, None, {
            'extracted': row_number,
            'imported': transactions_created
        }
        
    except Exception as e:
        # Update log with error
        if 'log' in locals():
            log.error_message = str(e)
            log.save()
        
        return False, str(e), {
            'extracted': 0,
            'imported': 0
        }


def parse_date(date_str):
    """Parse date from various formats"""
    date_formats = [
        '%Y-%m-%d',
        '%d/%m/%Y',
        '%m/%d/%Y',
        '%d-%m-%Y',
        '%d %b %Y',
        '%d %B %Y'
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse date: {date_str}")


@login_required
def file_detail(request, file_id):
    """Show details of uploaded file and its transactions"""
    try:
        uploaded_file = UploadedFile.objects.get(id=file_id, uploaded_by=request.user)
        transactions = uploaded_file.transactions.all()[:20]  # Show first 20 transactions
        
        context = {
            'uploaded_file': uploaded_file,
            'transactions': transactions,
            'total_transactions': uploaded_file.transactions.count(),
            'title': f'File Details - {uploaded_file.file_name}'
        }
        return render(request, 'reconciliation/file_detail.html', context)
        
    except UploadedFile.DoesNotExist:
        messages.error(request, 'File not found or access denied.')
        return redirect('reconciliation:upload_csv')


@login_required
def file_list(request):
    """List all uploaded files for the current user"""
    print("DEBUG: Reconciliation file_list view called")
    
    try:
        files = UploadedFile.objects.filter(uploaded_by=request.user).prefetch_related('transactions')
        print(f"DEBUG: Found {files.count()} files")
        
        # Calculate statistics
        processed_count = sum(1 for file in files if file.is_processed)
        pending_count = sum(1 for file in files if not file.is_processed)
        total_transactions = sum(file.transactions.count() for file in files if file.is_processed)
        
        print(f"DEBUG: processed_count={processed_count}, pending_count={pending_count}, total_transactions={total_transactions}")
        
        context = {
            'files': files,
            'processed_count': processed_count,
            'pending_count': pending_count,
            'total_transactions': total_transactions,
            'title': 'My Bank Statement Files'
        }
        print(f"DEBUG: Context prepared with {len(context)} items")
        
        response = render(request, 'reconciliation/file_list_simple.html', context)
        print(f"DEBUG: Reconciliation template rendered, content length: {len(response.content)}")
        return response
        
    except Exception as e:
        print(f"DEBUG: Error in reconciliation file_list view: {e}")
        from django.http import HttpResponse
        return HttpResponse(f"Reconciliation view error: {str(e)}", status=500)


def health_check(request):
    """Simple health check endpoint for reconciliation module"""
    from django.http import JsonResponse
    return JsonResponse({
        'status': 'healthy',
        'module': 'reconciliation'
    })
