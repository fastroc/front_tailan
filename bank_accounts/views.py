from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
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
    
    # Show only CURRENT_ASSET accounts that are specifically designated as bank accounts
    # Not ALL current asset accounts - only the ones manually marked as bank accounts
    accounts = Account.objects.filter(
        company=company,
        account_type='CURRENT_ASSET',
        is_bank_account=True  # Only show accounts specifically marked as bank accounts
    ).order_by('code')
    
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
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip()
            
            # Validate name
            if not name:
                messages.error(request, "Account name is required.")
                return render(request, 'bank_accounts/add_account.html', {'company': company})
            
            # Validate and suggest code if provided
            if code:
                # Check if code already exists
                existing_account = Account.objects.filter(
                    company=company,
                    code=code
                ).first()
                
                if existing_account:
                    # Generate suggestion
                    suggested_code = _generate_bank_code_suggestion(code, company)
                    messages.warning(
                        request, 
                        f'⚠️ Account code "{code}" is already used by "{existing_account.name}". '
                        f'Try "{suggested_code}" instead.'
                    )
                    return render(request, 'bank_accounts/add_account.html', {
                        'company': company,
                        'form_data': {
                            'name': name,
                            'code': code,
                            'suggested_code': suggested_code
                        }
                    })
            
            # Create the account
            account = Account.objects.create(
                company=company,
                name=name,
                account_type='CURRENT_ASSET',  # Use proper account type instead of 'Bank'
                code=code if code else _generate_auto_bank_code(company),
                is_bank_account=True,  # Mark this as a bank account
                created_by=request.user,
                updated_by=request.user,
                ytd_balance=0.00,
                current_balance=0.00
            )
            
            messages.success(request, f"Bank account '{account.name}' created successfully!")
            return redirect('bank_accounts:dashboard')
            
        except Exception as e:
            messages.error(request, f"Error creating bank account: {str(e)}")
            return render(request, 'bank_accounts/add_account.html', {
                'company': company,
                'form_data': {
                    'name': request.POST.get('name', ''),
                    'code': request.POST.get('code', '')
                }
            })
    
    return render(request, 'bank_accounts/add_account.html', {'company': company})


def _generate_bank_code_suggestion(attempted_code, company):
    """Generate a suggested alternative code for bank accounts."""
    try:
        base_num = int(attempted_code)
        for i in range(1, 10):
            suggested_code = str(base_num + i)
            if not Account.objects.filter(company=company, code=suggested_code).exists():
                return suggested_code
    except ValueError:
        for suffix in ['A', 'B', 'C', '1', '2']:
            suggested_code = f"{attempted_code}{suffix}"[:10]
            if not Account.objects.filter(company=company, code=suggested_code).exists():
                return suggested_code
    
    return f"{attempted_code[:8]}01"


def _generate_auto_bank_code(company):
    """Auto-generate a bank account code."""
    # Find the next available code in 10xx series
    for code_num in range(1001, 1100):
        code = str(code_num)
        if not Account.objects.filter(company=company, code=code).exists():
            return code
    
    # Fallback to 11xx series
    for code_num in range(1101, 1200):
        code = str(code_num)
        if not Account.objects.filter(company=company, code=code).exists():
            return code
    
    return "1999"  # Last resort


@login_required
def convert_account(request):
    """Convert existing CURRENT_ASSET account to bank account"""
    company_id = request.session.get('active_company_id')
    if not company_id:
        messages.error(request, "Please select a company first to convert accounts.")
        return redirect('bank_accounts:dashboard')
    
    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        messages.error(request, "Please select a company first to convert accounts.")
        return redirect('bank_accounts:dashboard')
    
    if request.method == 'POST':
        account_id = request.POST.get('account_id')
        try:
            account = Account.objects.get(
                id=account_id,
                company=company,
                account_type='CURRENT_ASSET',
                is_bank_account=False  # Must not already be a bank account
            )
            
            # Convert to bank account
            account.is_bank_account = True
            account.updated_by = request.user
            account.save()
            
            messages.success(request, f"Successfully converted '{account.name}' to a bank account!")
            return redirect('bank_accounts:dashboard')
            
        except Account.DoesNotExist:
            messages.error(request, "Account not found or cannot be converted.")
        except Exception as e:
            messages.error(request, f"Error converting account: {str(e)}")
    
    # Get CURRENT_ASSET accounts that are not already bank accounts
    available_accounts = Account.objects.filter(
        company=company,
        account_type='CURRENT_ASSET',
        is_bank_account=False,  # Not already a bank account
        is_active=True
    ).order_by('code')
    
    context = {
        'company': company,
        'available_accounts': available_accounts
    }
    
    return render(request, 'bank_accounts/convert_account.html', context)


@login_required
def bank_statement(request, account_id):
    """Display bank statement lines similar to Xero format"""
    company_id = request.session.get('active_company_id')
    if not company_id:
        messages.error(request, "Please select a company first.")
        return redirect('dashboard')
        
    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        messages.error(request, "Please select a company first.")
        return redirect('dashboard')
    
    # Get account
    account = get_object_or_404(
        Account, 
        id=account_id, 
        company=company, 
        account_type='CURRENT_ASSET',
        is_bank_account=True  # Only allow bank accounts
    )
    
    # Get all transactions for this account, ordered by date (newest first)
    transactions = BankTransaction.objects.filter(
        coa_account=account
    ).order_by('-date', '-id')
    
    # Calculate running balance (like Xero)
    # Start with opening balance from conversion system
    opening_balance = Decimal('0')
    try:
        from conversion.models import ConversionBalance
        conversion_balance = ConversionBalance.objects.filter(
            company=company,
            account=account
        ).order_by('-as_at_date').first()
        
        if conversion_balance:
            # For bank accounts, typically credit balances are positive
            opening_balance = conversion_balance.credit_amount - conversion_balance.debit_amount
    except ImportError:
        pass
    
    # Prepare transactions with running balance
    transaction_list = []
    
    # Process transactions in chronological order to calculate running balance correctly
    transactions_chronological = list(transactions.order_by('date', 'id'))
    running_balance = opening_balance
    
    for bank_transaction in transactions_chronological:
        running_balance += bank_transaction.amount
        
        # Determine transaction type
        if bank_transaction.amount > 0:
            trans_type = "Credit"
            spent = None
            received = abs(bank_transaction.amount)
        else:
            trans_type = "Debit" 
            spent = abs(bank_transaction.amount)
            received = None
        
        transaction_list.append({
            'transaction': bank_transaction,
            'type': trans_type,
            'spent': spent,
            'received': received,
            'balance': running_balance,
            'status': 'Imported',  # Could be enhanced with actual reconciliation status
            'reconciled': False,   # Could be enhanced with actual reconciliation data
        })
    
    # Reverse to show newest first (like Xero)
    transaction_list.reverse()
    
    # Get upload information
    uploads = UploadedFile.objects.filter(account=account).order_by('-uploaded_at')
    
    # Calculate summary stats
    total_debits = sum(abs(t.amount) for t in transactions if t.amount < 0)
    total_credits = sum(t.amount for t in transactions if t.amount > 0)
    current_balance = running_balance
    
    context = {
        'account': account,
        'company': company,
        'transactions': transaction_list,
        'opening_balance': opening_balance,
        'current_balance': current_balance,
        'total_debits': total_debits,
        'total_credits': total_credits,
        'transaction_count': transactions.count(),
        'uploads': uploads,
        'page_title': f'Bank Statement - {account.name}'
    }
    
    return render(request, 'bank_accounts/bank_statement.html', context)


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
    
    # Get account - only allow accounts specifically marked as bank accounts
    account = get_object_or_404(
        Account, 
        id=account_id, 
        company=company, 
        account_type='CURRENT_ASSET',
        is_bank_account=True  # Only allow bank accounts
    )
    
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
                company=company,
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
            
            # Read and process CSV - detect delimiter (comma or semicolon)
            decoded_file = file_content.decode('utf-8')
            
            # Try to detect delimiter by checking the first line
            first_line = decoded_file.split('\n')[0] if decoded_file else ''
            delimiter = ';' if ';' in first_line and first_line.count(';') > first_line.count(',') else ','
            
            csv_data = csv.DictReader(io.StringIO(decoded_file), delimiter=delimiter)
            
            transactions_created = 0
            duplicates_skipped = 0
            errors = []
            total_rows = 0
            
            with transaction.atomic():
                for row_num, row in enumerate(csv_data, start=2):  # Start at 2 because of header
                    total_rows += 1
                    try:
                        # Create case-insensitive column lookup
                        row_lower = {k.lower(): v for k, v in row.items()}
                        
                        # Check if required columns exist (case-insensitive)
                        if 'date' not in row_lower:
                            errors.append(f"Row {row_num}: Missing 'Date' column. Found columns: {list(row.keys())}")
                            continue
                        if 'amount' not in row_lower:
                            errors.append(f"Row {row_num}: Missing 'Amount' column. Found columns: {list(row.keys())}")
                            continue
                        
                        # Parse date with more flexible formats
                        date_str = row_lower['date'].strip()
                        transaction_date = None
                        
                        # Try multiple date formats
                        date_formats = [
                            '%d/%m/%Y',     # DD/MM/YYYY
                            '%m/%d/%Y',     # MM/DD/YYYY  
                            '%Y-%m-%d',     # YYYY-MM-DD
                            '%Y.%m.%d',     # YYYY.MM.DD
                            '%d-%m-%Y',     # DD-MM-YYYY
                            '%m-%d-%Y',     # MM-DD-YYYY
                            '%d.%m.%Y',     # DD.MM.YYYY
                            '%Y/%m/%d',     # YYYY/MM/DD
                        ]
                        
                        for date_format in date_formats:
                            try:
                                transaction_date = datetime.strptime(date_str, date_format).date()
                                break
                            except ValueError:
                                continue
                        
                        if transaction_date is None:
                            errors.append(f"Row {row_num}: Invalid date format '{date_str}'. Supported formats: DD/MM/YYYY, MM/DD/YYYY, YYYY-MM-DD, DD-MM-YYYY, etc.")
                            continue
                        
                        # Parse amount
                        amount_str = row_lower['amount'].strip().replace(',', '').replace('$', '').replace('€', '').replace('£', '')
                        try:
                            amount = Decimal(amount_str)
                        except (ValueError, InvalidOperation):
                            errors.append(f"Row {row_num}: Invalid amount '{amount_str}'")
                            continue
                        
                        # Get other fields with defaults for missing columns (case-insensitive)
                        description = row_lower.get('description', '').strip()
                        reference = row_lower.get('reference', '').strip()
                        
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
                            company=company,
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
        # Get account - only allow accounts specifically marked as bank accounts
        account = get_object_or_404(
            Account, 
            id=account_id, 
            company=company, 
            account_type='CURRENT_ASSET',
            is_bank_account=True  # Only allow bank accounts
        )
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
