from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from coa.models import Account
from company.models import Company
from .models import BankTransaction, UploadedFile
import csv
import io
import os
import hashlib
from datetime import datetime
from decimal import Decimal, InvalidOperation


@login_required
def dashboard(request):
    """Bank accounts landing page with overview"""
    # For now, show empty state if no company - don't redirect
    company_id = request.session.get('active_company_id')  # Use correct session key
    if not company_id:
        # Show empty state instead of redirecting - use empty queryset
        return render(request, 'bank_accounts/landing.html', {
            'accounts': Account.objects.none(),  # Empty queryset instead of list
            'company': None,
            'total_balance': 0,
            'no_company': True
        })
    
    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        # Show empty state instead of redirecting - use empty queryset
        return render(request, 'bank_accounts/landing.html', {
            'accounts': Account.objects.none(),  # Empty queryset instead of list
            'company': None,
            'total_balance': 0,
            'no_company': True
        })
    
    accounts = Account.objects.filter(
        company=company,
        account_type='Bank'
    ).order_by('code')  # Use 'code' instead of 'gl_code'
    
    # Add upload information for each account
    accounts_with_uploads = []
    total_transactions = 0
    total_upload_files = 0
    
    for account in accounts:
        # Get recent uploads for this account
        recent_uploads = UploadedFile.objects.filter(account=account).order_by('-uploaded_at')[:3]
        
        # Get transaction count
        transaction_count = BankTransaction.objects.filter(coa_account=account).count()
        total_transactions += transaction_count
        
        # Get last upload info
        last_upload = recent_uploads.first() if recent_uploads.exists() else None
        
        # Total uploads count
        total_uploads = UploadedFile.objects.filter(account=account).count()
        total_upload_files += total_uploads
        
        accounts_with_uploads.append({
            'account': account,
            'recent_uploads': recent_uploads,
            'transaction_count': transaction_count,
            'last_upload': last_upload,
            'total_uploads': total_uploads
        })
    
    # Calculate total balance
    total_balance = sum(account.current_balance or 0 for account in accounts)
    
    return render(request, 'bank_accounts/landing.html', {
        'accounts_data': accounts_with_uploads,
        'accounts': accounts,  # Keep for compatibility
        'company': company,
        'total_balance': total_balance,
        'total_transactions': total_transactions,
        'total_upload_files': total_upload_files
    })


@login_required 
def add_account(request):
    """Create new bank account (COA account with type=Bank)"""
    company_id = request.session.get('active_company_id')  # Use correct session key
    if not company_id:
        messages.error(request, "Please select a company first to add bank accounts.")
        return redirect('bank_accounts:dashboard')  # Redirect back to bank accounts instead of dashboard
    
    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        messages.error(request, "Please select a company first to add bank accounts.")
        return redirect('bank_accounts:dashboard')  # Redirect back to bank accounts instead of dashboard
    
    if request.method == 'POST':
        try:
            account = Account.objects.create(
                company=company,
                name=request.POST['name'],
                account_type='Bank',
                code=request.POST.get('code', ''),  # Use 'code' instead of 'gl_code'
                created_by=request.user
            )
            messages.success(request, f"Bank account '{account.name}' created successfully!")
            return redirect('bank_accounts:dashboard')
        except Exception as e:
            messages.error(request, f"Error creating bank account: {str(e)}")
    
    return render(request, 'bank_accounts/add_account.html', {'company': company})


@login_required
def upload_transactions(request, account_id):
    """Upload bank transactions for a specific account"""
    company_id = request.session.get('active_company_id')  # Use correct session key
    if not company_id:
        messages.error(request, "Please select a company first.")
        return redirect('dashboard')
        
    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        messages.error(request, "Please select a company first.")
        return redirect('dashboard')
    
    account = get_object_or_404(Account, id=account_id, company=company, account_type='Bank')
    
    if request.method == 'POST' and request.FILES.get('statement_file'):
        csv_file = request.FILES['statement_file']
        
        # Validate file type
        if not csv_file.name.endswith('.csv'):
            messages.error(request, "Please upload a CSV file.")
            return render(request, 'bank_accounts/upload.html', {'account': account, 'company': company})
        
        try:
            # Create file hash for duplicate detection
            csv_file.seek(0)
            file_content = csv_file.read()
            file_hash = hashlib.sha256(file_content).hexdigest()
            csv_file.seek(0)
            
            # Check if this exact file has been uploaded before
            if UploadedFile.objects.filter(account=account, file_hash=file_hash).exists():
                messages.warning(request, "This exact file has already been uploaded to this account.")
                return render(request, 'bank_accounts/upload.html', {'account': account, 'company': company})
            
            # Store file
            file_dir = f"bank_statements/{company.id}/{account.id}"
            os.makedirs(os.path.join('media', file_dir), exist_ok=True)
            stored_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{csv_file.name}"
            file_path = f"{file_dir}/{stored_filename}"
            
            # Save file to media directory
            full_path = os.path.join('media', file_path)
            with open(full_path, 'wb') as f:
                f.write(file_content)
            
            # Create UploadedFile record
            uploaded_file = UploadedFile.objects.create(
                account=account,
                original_filename=csv_file.name,
                stored_filename=stored_filename,
                file_size=len(file_content),
                file_hash=file_hash,
                uploaded_by=request.user,
                total_rows=0,
                imported_count=0,
                duplicate_count=0,
                error_count=0
            )
            
            # Read and process CSV
            decoded_file = file_content.decode('utf-8')
            csv_data = csv.DictReader(io.StringIO(decoded_file))
            
            transactions_created = 0
            duplicates_skipped = 0
            errors = []
            total_rows = 0
            
            with transaction.atomic():
                for row_num, row in enumerate(csv_data, start=2):  # Start at 2 because of header
                    total_rows += 1
                    try:
                        # Parse date (DD/MM/YYYY format)
                        date_str = row['Date'].strip()
                        try:
                            transaction_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                        except ValueError:
                            try:
                                transaction_date = datetime.strptime(date_str, '%m/%d/%Y').date()
                            except ValueError:
                                errors.append(f"Row {row_num}: Invalid date format '{date_str}'")
                                continue
                        
                        # Parse amount
                        amount_str = row['Amount'].strip().replace(',', '')
                        try:
                            amount = Decimal(amount_str)
                        except (ValueError, InvalidOperation):
                            errors.append(f"Row {row_num}: Invalid amount '{amount_str}'")
                            continue
                        
                        # Get other fields
                        description = row['Description'].strip()
                        reference = row['Reference'].strip()
                        
                        # Generate transaction hash for duplicate detection
                        hash_string = f"{transaction_date}{amount}{reference}{description}"
                        transaction_hash = hashlib.sha256(hash_string.encode()).hexdigest()
                        
                        # Check for duplicate
                        if BankTransaction.objects.filter(
                            coa_account=account,
                            transaction_hash=transaction_hash
                        ).exists():
                            duplicates_skipped += 1
                            continue
                        
                        # Create transaction
                        BankTransaction.objects.create(
                            date=transaction_date,
                            coa_account=account,
                            amount=amount,
                            description=description,
                            reference=reference,
                            transaction_hash=transaction_hash,
                            uploaded_file=uploaded_file.stored_filename,  # Keep old field for now
                            uploaded_by=request.user
                        )
                        transactions_created += 1
                        
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
                
                # Update UploadedFile with results
                uploaded_file.total_rows = total_rows
                uploaded_file.imported_count = transactions_created
                uploaded_file.duplicate_count = duplicates_skipped
                uploaded_file.error_count = len(errors)
                uploaded_file.save()
            
            # Show results
            result_messages = []
            if transactions_created > 0:
                result_messages.append(f"✅ Successfully imported {transactions_created} new transactions!")
                
                # Update account balance (simple sum of all transactions)
                total_amount = sum(t.amount for t in BankTransaction.objects.filter(coa_account=account))
                account.current_balance = total_amount
                account.save()
            
            if duplicates_skipped > 0:
                result_messages.append(f"📋 Skipped {duplicates_skipped} duplicate transactions")
                
            if errors:
                result_messages.append(f"⚠️ {len(errors)} errors occurred")
                
            for msg in result_messages:
                messages.success(request, msg)
                
            if errors:
                for error in errors[:5]:  # Show first 5 errors
                    messages.warning(request, error)
                if len(errors) > 5:
                    messages.warning(request, f"... and {len(errors) - 5} more errors.")
            
            return redirect('bank_accounts:dashboard')
            
        except Exception as e:
            messages.error(request, f"Error processing CSV file: {str(e)}")
    
    # Get recent uploads for this account
    recent_uploads = UploadedFile.objects.filter(account=account).order_by('-uploaded_at')[:5]
    
    return render(request, 'bank_accounts/upload.html', {
        'account': account,
        'company': company,
        'recent_uploads': recent_uploads
    })


@login_required
def delete_upload(request, account_id, upload_id):
    """Delete an uploaded file and all its associated transactions"""
    company_id = request.session.get('active_company_id')
    if not company_id:
        messages.error(request, "Please select a company first.")
        return redirect('dashboard')
        
    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        messages.error(request, "Please select a company first.")
        return redirect('dashboard')
    
    try:
        account = get_object_or_404(Account, id=account_id, company=company, account_type='Bank')
        uploaded_file = get_object_or_404(UploadedFile, id=upload_id, account=account)
        
        if request.method == 'POST':
            try:
                with transaction.atomic():
                    # Get the stored filename for proper transaction matching
                    stored_filename = uploaded_file.stored_filename
                    original_filename = uploaded_file.original_filename
                    
                    # Count transactions to be deleted (try multiple ways to ensure we get them all)
                    transactions_to_delete = BankTransaction.objects.filter(
                        coa_account=account,
                        uploaded_file=stored_filename
                    )
                    
                    # Also check for transactions that might have empty uploaded_file but match this upload
                    # (This is a backup in case there were issues during upload)
                    orphaned_transactions = BankTransaction.objects.filter(
                        coa_account=account,
                        uploaded_file__in=['', None]
                    )
                    
                    transaction_count = transactions_to_delete.count()
                    orphaned_count = orphaned_transactions.count()
                    
                    print(f"Deleting upload {upload_id}:")
                    print(f"  - Stored filename: {stored_filename}")
                    print(f"  - Transactions with filename: {transaction_count}")
                    print(f"  - Orphaned transactions: {orphaned_count}")
                    
                    # Delete transactions with matching filename
                    transactions_to_delete.delete()
                    
                    # If there are orphaned transactions and this is the only upload for this account,
                    # clean them up too (safety measure)
                    remaining_uploads = UploadedFile.objects.filter(account=account).exclude(id=upload_id).count()
                    if remaining_uploads == 0 and orphaned_count > 0:
                        print(f"  - Cleaning up {orphaned_count} orphaned transactions (no other uploads exist)")
                        orphaned_transactions.delete()
                        transaction_count += orphaned_count
                    
                    # Delete physical file if it exists
                    file_path = os.path.join('media', f"bank_statements/{company.id}/{account.id}/{stored_filename}")
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"  - Deleted physical file: {file_path}")
                    
                    # Delete the upload record
                    uploaded_file.delete()
                    
                    # Recalculate account balance from remaining transactions
                    remaining_transactions = BankTransaction.objects.filter(coa_account=account)
                    new_balance = sum(t.amount for t in remaining_transactions)
                    old_balance = account.current_balance
                    
                    account.current_balance = new_balance
                    account.save()
                    
                    print(f"  - Updated balance from ${old_balance} to ${new_balance}")
                    print(f"  - Remaining transactions: {remaining_transactions.count()}")
                    
                    messages.success(request, f"✅ Successfully deleted '{original_filename}' and removed {transaction_count} transactions.")
                    print(f"Successfully completed deletion of upload {upload_id}")
                    
            except Exception as e:
                messages.error(request, f"❌ Error deleting upload: {str(e)}")
                print(f"Error deleting upload {upload_id}: {str(e)}")
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        messages.error(request, f"❌ Upload not found or access denied: {str(e)}")
        print(f"Error accessing upload {upload_id}: {str(e)}")
    
    # Smart redirect based on referrer
    referrer = request.META.get('HTTP_REFERER', '')
    if 'bank_accounts/' in referrer and 'upload' not in referrer:
        # Came from dashboard, redirect back to dashboard
        return redirect('bank_accounts:dashboard')
    else:
        # Came from upload page, redirect back to upload page
        return redirect('bank_accounts:upload_transactions', account_id=account_id)
