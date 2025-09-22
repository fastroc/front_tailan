"""
AJAX endpoints for reconciliation transaction matching
"""

import json
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator

from coa.models import Account
from bank_accounts.models import BankTransaction
from company.models import Company
from .reconciliation_service import ReconciliationService
from .models import TransactionMatch


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def match_transaction(request):
    """AJAX endpoint for processing transaction matches"""
    try:
        data = json.loads(request.body)
        
        # Extract data from request
        transaction_id = data.get('transaction_id')
        contact = data.get('contact', '')
        account_id = data.get('account_id')
        tax_treatment = data.get('tax_treatment', 'no_gst')
        notes = data.get('notes', '')
        
        # Validate required fields
        if not transaction_id or not account_id:
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields: transaction_id or account_id'
            }, status=400)
        
        # Get the bank transaction
        try:
            bank_transaction = get_object_or_404(BankTransaction, id=transaction_id)
        except BankTransaction.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Bank transaction not found'
            }, status=404)
        
        # Validate the chart of accounts entry exists
        try:
            coa_account = get_object_or_404(Account, id=account_id)
        except Account.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Chart of Accounts entry not found with ID: {account_id}'
            }, status=404)
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': f'Invalid account ID format: {account_id}'
            }, status=400)
        
        # Get or create reconciliation session
        from .reconciliation_service import ReconciliationService
        reconciliation_session = ReconciliationService.get_or_create_session(
            bank_transaction.coa_account, request.user
        )
        
        # Prepare match data
        match_data = {
            'contact': contact,
            'gl_account_id': account_id,
            'description': notes,
            'tax_rate': tax_treatment
        }
        
        # Use reconciliation service to create the match
        match = ReconciliationService.match_transaction(
            bank_transaction=bank_transaction,
            reconciliation_session=reconciliation_session,
            match_data=match_data,
            user=request.user
        )
        
        # NEW: Auto-create loan payment if WHO field contains a loan customer
        loan_payment_created = False
        loan_payment_info = None
        
        if match and contact:
            loan_payment_created, loan_payment_info = auto_create_loan_payment(
                bank_transaction=bank_transaction,
                contact_name=contact,
                amount=bank_transaction.amount,
                payment_date=bank_transaction.date,
                notes=notes,
                user=request.user
            )
        
        # Match creation includes journal entry and session statistics update
        if match:
            response_data = {
                'success': True,
                'message': 'Transaction matched successfully',
                'match_id': match.id,
                'journal_id': match.journal_entry.id if match.journal_entry else None,
                'transaction': {
                    'id': bank_transaction.id,
                    'description': bank_transaction.description,
                    'amount': float(bank_transaction.amount),
                    'matched': True
                }
            }
            
            # Add loan payment information if created
            if loan_payment_created and loan_payment_info:
                response_data['loan_payment'] = {
                    'created': True,
                    'payment_id': loan_payment_info.get('payment_id'),
                    'customer': loan_payment_info.get('customer_name'),
                    'loan_number': loan_payment_info.get('loan_number'),
                    'amount': float(loan_payment_info.get('amount', 0)),
                    'allocation_summary': loan_payment_info.get('allocation_summary', [])
                }
                response_data['message'] += f" & Loan payment recorded for {loan_payment_info.get('customer_name')}"
            
            return JsonResponse(response_data)
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to create transaction match'
            }, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def reconciliation_progress(request, account_id):
    """AJAX endpoint for getting reconciliation progress"""
    try:
        # Get the account
        company_id = request.session.get('active_company_id')
        if not company_id:
            return JsonResponse({
                'success': False,
                'error': 'No active company selected'
            }, status=400)
            
        company = get_object_or_404(Company, id=company_id)
        account = get_object_or_404(Account, id=account_id, company=company, account_type='Bank')
        
        # Get progress from service
        progress = ReconciliationService.get_reconciliation_progress(account)
        
        return JsonResponse({
            'success': True,
            'progress': progress
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error getting progress: {str(e)}'
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def unmatch_transaction(request):
    """AJAX endpoint for removing a transaction match"""
    try:
        data = json.loads(request.body)
        match_id = data.get('match_id')
        
        if not match_id:
            return JsonResponse({
                'success': False,
                'error': 'Missing match_id'
            }, status=400)
        
        # Get the transaction match
        try:
            match = get_object_or_404(TransactionMatch, id=match_id)
        except TransactionMatch.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Transaction match not found'
            }, status=404)
        
        # Store transaction info before deleting
        bank_transaction = match.bank_transaction
        account = bank_transaction.account
        
        # Delete associated journal entry if exists
        if match.journal_entry:
            match.journal_entry.delete()
        
        # Delete the match
        match.delete()
        
        # Update session statistics
        ReconciliationService.update_session_statistics(account)
        
        return JsonResponse({
            'success': True,
            'message': 'Transaction match removed successfully',
            'transaction': {
                'id': bank_transaction.id,
                'description': bank_transaction.description,
                'amount': float(bank_transaction.amount),
                'matched': False
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_unmatched_transactions(request, account_id):
    """AJAX endpoint for getting unmatched transactions for an account"""
    try:
        # Get the account
        company_id = request.session.get('active_company_id')
        if not company_id:
            return JsonResponse({
                'success': False,
                'error': 'No active company selected'
            }, status=400)
            
        company = get_object_or_404(Company, id=company_id)
        account = get_object_or_404(Account, id=account_id, company=company, account_type='Bank')
        
        # Get unmatched transactions
        unmatched = ReconciliationService.get_unmatched_transactions(account)
        
        transactions = []
        for transaction in unmatched:
            transactions.append({
                'id': transaction.id,
                'date': transaction.date.strftime('%Y-%m-%d'),
                'description': transaction.description,
                'reference': transaction.reference or '',
                'amount': float(transaction.amount)
            })
        
        return JsonResponse({
            'success': True,
            'transactions': transactions,
            'count': len(transactions)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error getting transactions: {str(e)}'
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def restart_reconciliation(request):
    """AJAX endpoint for restarting reconciliation for an account"""
    try:
        data = json.loads(request.body)
        
        # Extract data from request
        account_id = data.get('account_id')
        delete_journals = data.get('delete_journals', False)
        
        # Validate required fields
        if not account_id:
            return JsonResponse({
                'success': False,
                'error': 'Missing required field: account_id'
            }, status=400)
        
        # Get the account
        company_id = request.session.get('active_company_id')
        if not company_id:
            return JsonResponse({
                'success': False,
                'error': 'No active company selected'
            }, status=400)
            
        company = get_object_or_404(Company, id=company_id)
        
        # Get account by identifier (could be ID or code)
        try:
            if account_id.isdigit():
                account = get_object_or_404(Account, id=account_id, company=company, account_type='Bank')
            else:
                account = get_object_or_404(Account, code=account_id, company=company, account_type='Bank')
        except Account.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Bank account not found: {account_id}'
            }, status=404)
        
        # Use reconciliation service to restart
        result = ReconciliationService.restart_reconciliation(
            account=account,
            user=request.user,
            delete_journal_entries=delete_journals
        )
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': result['message'],
                'matches_deleted': result['matches_deleted'],
                'journals_deleted': result['journals_deleted'],
                'account_name': account.name
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result['message']
            }, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_matched_transactions(request, account_id):
    """AJAX endpoint for getting matched transactions for an account"""
    try:
        # Get the account
        company_id = request.session.get('active_company_id')
        if not company_id:
            return JsonResponse({
                'success': False,
                'error': 'No active company selected'
            }, status=400)
            
        company = get_object_or_404(Company, id=company_id)
        account = get_object_or_404(Account, id=account_id, company=company)
        
        # Get matched transactions (ordered by transaction date - oldest first)
        matched_transactions = TransactionMatch.objects.filter(
            bank_transaction__coa_account=account,
            is_reconciled=True
        ).select_related(
            'bank_transaction', 'gl_account', 'reconciliation_session'
        ).order_by('bank_transaction__date')
        
        # Convert to JSON serializable format
        transactions = []
        for match in matched_transactions:
            bank_tx = match.bank_transaction
            transactions.append({
                'match_id': match.id,
                'id': bank_tx.id,
                'date': bank_tx.date.strftime('%Y-%m-%d'),
                'description': bank_tx.description,
                'reference': bank_tx.reference or '',
                'amount': float(bank_tx.amount),
                'contact': match.contact,
                'gl_account_id': match.gl_account.id if match.gl_account else None,
                'gl_account_name': f"{match.gl_account.code} — {match.gl_account.name}" if match.gl_account else '',
                'match_description': match.description,
                'tax_rate': match.tax_rate,
                'match_type': match.match_type,
                'matched_at': match.matched_at.strftime('%Y-%m-%d %H:%M') if match.matched_at else '',
                'is_split': match.is_split_transaction
            })
        
        return JsonResponse({
            'success': True,
            'transactions': transactions,
            'count': len(transactions)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error getting matched transactions: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_transaction_match(request, match_id):
    """AJAX endpoint for getting details of a specific transaction match"""
    try:
        # Get the transaction match
        match = get_object_or_404(
            TransactionMatch.objects.select_related(
                'bank_transaction', 'gl_account', 'reconciliation_session'
            ), 
            id=match_id
        )
        
        bank_tx = match.bank_transaction
        
        match_data = {
            'match_id': match.id,
            'transaction_id': bank_tx.id,
            'date': bank_tx.date.strftime('%Y-%m-%d'),
            'description': bank_tx.description,
            'reference': bank_tx.reference or '',
            'amount': float(bank_tx.amount),
            'contact': match.contact,
            'gl_account_id': match.gl_account.id if match.gl_account else None,
            'gl_account_code': match.gl_account.code if match.gl_account else '',
            'gl_account_name': match.gl_account.name if match.gl_account else '',
            'match_description': match.description,
            'tax_rate': match.tax_rate,
            'match_type': match.match_type,
            'matched_at': match.matched_at.strftime('%Y-%m-%d %H:%M') if match.matched_at else '',
            'is_split': match.is_split_transaction,
            'notes': match.notes
        }
        
        # If it's a split transaction, get split details
        if match.is_split_transaction:
            splits = []
            for split in match.splits.all().order_by('split_number'):
                splits.append({
                    'id': split.id,
                    'split_number': split.split_number,
                    'amount': float(split.amount),
                    'contact': split.contact,
                    'gl_account_id': split.gl_account.id,
                    'gl_account_code': split.gl_account.code,
                    'gl_account_name': split.gl_account.name,
                    'description': split.description,
                    'tax_rate': split.tax_rate,
                    'tax_amount': float(split.tax_amount),
                    'net_amount': float(split.net_amount)
                })
            match_data['splits'] = splits
        
        return JsonResponse({
            'success': True,
            'match': match_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error getting transaction match: {str(e)}'
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def edit_transaction_match(request, match_id):
    """AJAX endpoint for editing an existing transaction match"""
    try:
        data = json.loads(request.body)
        
        # Get the transaction match
        match = get_object_or_404(TransactionMatch, id=match_id)
        
        # Extract data from request
        contact = data.get('contact', '')
        account_id = data.get('account_id')
        tax_treatment = data.get('tax_treatment', 'no_gst')
        notes = data.get('notes', '')
        
        # Validate required fields
        if not account_id:
            return JsonResponse({
                'success': False,
                'error': 'Missing required field: account_id'
            }, status=400)
        
        # Validate the chart of accounts entry exists
        try:
            coa_account = get_object_or_404(Account, id=account_id)
        except Account.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Chart of Accounts entry not found with ID: {account_id}'
            }, status=404)
        
        # Update the match
        match.contact = contact
        match.gl_account = coa_account
        match.description = notes
        match.tax_rate = tax_treatment
        match.save()
        
        # Update associated journal entry if it exists
        if match.journal_entry:
            from .reconciliation_service import ReconciliationService
            ReconciliationService.update_journal_entry(match)
        
        bank_tx = match.bank_transaction
        
        return JsonResponse({
            'success': True,
            'message': 'Transaction match updated successfully',
            'match_id': match.id,
            'transaction': {
                'id': bank_tx.id,
                'description': bank_tx.description,
                'amount': float(bank_tx.amount),
                'contact': match.contact,
                'gl_account_name': f"{coa_account.code} — {coa_account.name}",
                'match_description': match.description,
                'tax_rate': match.tax_rate
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }, status=500)


# ====== LOAN INTEGRATION ENDPOINTS ======

@require_http_methods(["GET"])
# @login_required  # Temporarily disabled for testing
def search_loan_customers(request):
    """AJAX endpoint for hybrid customer search in WHO field"""
    query = request.GET.get('q', '').strip()
    company_id = request.session.get('active_company_id')
    
    print(f"🔍 Search request - Query: '{query}', Company ID: {company_id}")
    
    # If no company_id in session, get the first available company for testing
    if not company_id:
        try:
            from company.models import Company
            first_company = Company.objects.first()
            if first_company:
                company_id = first_company.id
                print(f"🔧 Using first available company ID: {company_id}")
            else:
                print("❌ No companies found in database")
                return JsonResponse({'customers': [], 'error': 'No companies available'})
        except Exception as e:
            print(f"❌ Error getting company: {e}")
            return JsonResponse({'customers': [], 'error': 'Company lookup failed'})

@require_http_methods(["GET"])
# @login_required  # Temporarily disabled for testing  
def get_all_loan_customers(request):
    """AJAX endpoint to get all loan customers for dropdown"""
    company_id = request.session.get('active_company_id')
    
    print(f"🔍 Get all loan customers request - Company ID: {company_id}")
    
    # If no company_id in session, get the first available company for testing
    if not company_id:
        try:
            from company.models import Company
            first_company = Company.objects.first()
            if first_company:
                company_id = first_company.id
                print(f"🔧 Using first available company ID: {company_id}")
            else:
                print("❌ No companies found in database")
                return JsonResponse({'customers': [], 'error': 'No companies available'})
        except Exception as e:
            print(f"❌ Error getting company: {e}")
            return JsonResponse({'customers': [], 'error': 'Company lookup failed'})

    try:
        from loans_customers.models import Customer
        from loans_core.models import Loan, LoanApplication
        
        # Get customers with active loans OR approved applications (for reconciliation)
        active_loan_customer_ids = Loan.objects.filter(
            company_id=company_id,
            status='active'
        ).values_list('customer_id', flat=True).distinct()
        
        # Also include customers with approved loan applications
        approved_app_customer_ids = LoanApplication.objects.filter(
            company_id=company_id,
            status='approved'
        ).values_list('customer_id', flat=True).distinct()
        
        # Combine both lists
        all_loan_customer_ids = list(set(list(active_loan_customer_ids) + list(approved_app_customer_ids)))
        
        print(f"🏢 Active loan customer IDs for company {company_id}: {list(active_loan_customer_ids)}")
        print(f"🏢 Approved application customer IDs for company {company_id}: {list(approved_app_customer_ids)}")
        print(f"🏢 Combined loan customer IDs: {all_loan_customer_ids}")
        
        customers = Customer.objects.filter(
            company_id=company_id,
            id__in=all_loan_customer_ids
        ).order_by('first_name', 'last_name')
        
        results = []
        for customer in customers:
            # Get customer's active loan info
            active_loans = Loan.objects.filter(
                customer=customer,
                status='active'
            )
            
            loan_info = ""
            if active_loans.exists():
                loan = active_loans.first()
                loan_info = f" (Loan: {loan.loan_number})"
            
            full_name = f"{customer.first_name} {customer.last_name}".strip()
            if customer.business_name:
                full_name = f"{customer.business_name} - {full_name}"
            
            results.append({
                'id': customer.id,
                'name': full_name,
                'display_name': f"{full_name}{loan_info}",
                'customer_id': customer.customer_id,
                'loan_info': loan_info.strip("() "),
            })
        
        print(f"📋 Found {len(results)} loan customers")
        
        return JsonResponse({
            'customers': results,
            'count': len(results)
        })
        
    except Exception as e:
        print(f"❌ Error in get_all_loan_customers: {e}")
        return JsonResponse({'customers': [], 'error': str(e)})


@require_http_methods(["GET"])
# @login_required  # Temporarily disabled for testing
def detect_loan_payment(request, transaction_id):
    """Detect if a bank transaction might be a loan payment"""
    company_id = request.session.get('active_company_id')
    
    # If no company_id in session, get the first available company for testing
    if not company_id:
        try:
            from company.models import Company
            first_company = Company.objects.first()
            if first_company:
                company_id = first_company.id
                print(f"🔧 Using first available company ID for detection: {company_id}")
            else:
                return JsonResponse({'error': 'No companies available'}, status=400)
        except Exception as e:
            return JsonResponse({'error': 'Company lookup failed'}, status=400)
    
    try:
        transaction = BankTransaction.objects.get(id=transaction_id)
        
        # Verify transaction belongs to company
        if hasattr(transaction, 'company') and transaction.company_id != company_id:
            return JsonResponse({'error': 'Transaction not found'}, status=404)
        
        # Basic loan payment detection
        description = transaction.description.lower() if transaction.description else ""
        amount = abs(transaction.amount)
        
        # Keywords that suggest loan payment
        loan_keywords = [
            'loan', 'payment', 'pmt', 'installment', 
            'monthly', 'autopay', 'repayment'
        ]
        
        has_keywords = any(keyword in description for keyword in loan_keywords)
        significant_amount = amount >= 100  # Minimum loan payment threshold
        
        is_likely_loan_payment = has_keywords or significant_amount
        
        suggestions = []
        
        if is_likely_loan_payment:
            try:
                from fuzzywuzzy import fuzz
            except ImportError:
                # Fallback without fuzzy matching
                class SimpleFuzz:
                    @staticmethod
                    def partial_ratio(a, b):
                        a, b = str(a).lower(), str(b).lower()
                        if a in b or b in a:
                            return 80
                        return 20
                
                fuzz = SimpleFuzz()
            
            from loans_customers.models import Customer
            from loans_core.models import Loan
            
            # Get customers who have active loans by using Loan model
            active_loan_customer_ids = Loan.objects.filter(
                company_id=company_id,
                status='active'
            ).values_list('customer_id', flat=True).distinct()
            
            customers = Customer.objects.filter(
                company_id=company_id,
                id__in=active_loan_customer_ids
            )
            
            for customer in customers:
                score = 0
                
                # Name matching in description
                full_name = customer.full_name
                name_score = fuzz.partial_ratio(description, full_name.lower())
                score += name_score * 0.6  # 60% weight for name matching
                
                # Amount matching with loan payments - get loans directly
                active_loans = Loan.objects.filter(customer=customer, status='active')
                amount_match_found = False
                
                for loan in active_loans:
                    monthly_payment = loan.monthly_payment
                    if monthly_payment:
                        # Check if amount matches monthly payment (±10%)
                        amount_diff = abs(amount - monthly_payment) / monthly_payment
                        if amount_diff <= 0.1:
                            score += 30  # 30 points for amount match
                            amount_match_found = True
                            break
                
                if score > 40:  # Minimum confidence threshold
                    suggestions.append({
                        'customer_id': customer.id,
                        'customer_name': customer.full_name,
                        'confidence': min(score, 100),
                        'match_reason': f"Name: {name_score}%, Amount match: {amount_match_found}",
                        'loans': [
                            {
                                'id': loan.id,
                                'loan_number': loan.loan_number,
                                'balance': float(loan.current_balance),
                                'monthly_payment': float(loan.monthly_payment)
                            }
                            for loan in active_loans
                        ]
                    })
            
            # Sort by confidence
            suggestions = sorted(suggestions, key=lambda x: x['confidence'], reverse=True)[:5]
        
        return JsonResponse({
            'is_loan_payment': is_likely_loan_payment,
            'suggestions': suggestions,
            'transaction': {
                'id': transaction.id,
                'description': transaction.description or '',
                'amount': float(transaction.amount),
                'date': transaction.date.strftime('%Y-%m-%d') if hasattr(transaction, 'date') and transaction.date else 'Unknown'
            }
        })
        
    except BankTransaction.DoesNotExist:
        return JsonResponse({'error': 'Transaction not found'}, status=404)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in detect_loan_payment: {error_details}")  # This will show in console
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@require_http_methods(["POST"])
@login_required
@csrf_exempt
def create_loan_payment_from_reconciliation(request):
    """Create loan payment from reconciliation transaction match"""
    try:
        data = json.loads(request.body)
        customer_id = data.get('customer_id')
        loan_id = data.get('loan_id') 
        transaction_match_id = data.get('transaction_match_id')
        
        from loans_customers.models import Customer
        from loans_core.models import Loan
        from loans_payments.models import Payment
        from django.utils import timezone
        
        # Get the transaction match
        transaction_match = TransactionMatch.objects.get(id=transaction_match_id)
        customer = Customer.objects.get(id=customer_id)
        loan = Loan.objects.get(id=loan_id, customer=customer)
        
        # Create payment record
        amount = abs(transaction_match.bank_transaction.amount)
        
        payment = Payment.objects.create(
            company=transaction_match.company,
            loan=loan,
            customer=customer,
            payment_date=transaction_match.bank_transaction.date,
            payment_amount=amount,
            payment_method='bank_transfer',
            payment_type='regular',
            status='completed',
            reference_number=transaction_match.bank_transaction.reference or '',
            notes=f'Auto-created from reconciliation: {transaction_match.bank_transaction.description}',
            net_payment_amount=amount,
            processed_by=request.user,
            processed_date=timezone.now()
        )
        
        # Update loan balance
        loan.current_balance = max(0, loan.current_balance - amount)
        loan.payments_made += 1
        loan.payments_remaining = max(0, loan.payments_remaining - 1)
        loan.last_payment_date = transaction_match.bank_transaction.date
        loan.total_payments_received += amount
        loan.save()
        
        # Mark transaction match as loan payment
        transaction_match.notes = f"{transaction_match.notes}\n\nLoan Payment Created: {payment.payment_id} for {loan.loan_number}"
        transaction_match.save()
        
        return JsonResponse({
            'success': True,
            'payment_id': payment.payment_id,
            'payment_amount': float(payment.payment_amount),
            'loan_number': loan.loan_number,
            'customer_name': customer.full_name,
            'new_balance': float(loan.current_balance)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Debug endpoint to test basic functionality
@require_http_methods(["GET"])
def debug_transaction(request, transaction_id):
    """Debug endpoint to check transaction existence"""
    try:
        # First check if any transactions exist
        total_count = BankTransaction.objects.count()
        
        if transaction_id == 0:
            # Special case: return info about all transactions
            transactions = BankTransaction.objects.all()[:10]
            return JsonResponse({
                'total_count': total_count,
                'sample_transactions': [
                    {
                        'id': t.id,
                        'description': getattr(t, 'description', 'No description'),
                        'amount': float(getattr(t, 'amount', 0))
                    }
                    for t in transactions
                ]
            })
        
        transaction = BankTransaction.objects.get(id=transaction_id)
        return JsonResponse({
            'found': True,
            'total_count': total_count,
            'id': transaction.id,
            'description': getattr(transaction, 'description', 'No description'),
            'amount': float(getattr(transaction, 'amount', 0)),
            'fields': [field.name for field in transaction._meta.fields]
        })
    except BankTransaction.DoesNotExist:
        total_count = BankTransaction.objects.count()
        return JsonResponse({
            'found': False, 
            'total_count': total_count,
            'error': f'Transaction {transaction_id} not found'
        })
    except Exception as e:
        return JsonResponse({'found': False, 'error': str(e)})

def test_integration(request):
    """Test endpoint to verify integration without authentication"""
    try:
        from loans_customers.models import Customer
        from loans_core.models import Loan
        
        # Test basic queries
        customer_count = Customer.objects.count()
        loan_count = Loan.objects.count()
        
        # Test relationship query that was failing
        active_loan_customer_ids = Loan.objects.filter(
            status='active'
        ).values_list('customer_id', flat=True).distinct()
        
        customers_with_loans = Customer.objects.filter(
            id__in=active_loan_customer_ids
        ).count()
        
        return JsonResponse({
            'status': 'success',
            'integration_test': 'passed',
            'customer_count': customer_count,
            'loan_count': loan_count,
            'customers_with_active_loans': customers_with_loans,
            'relationship_query': 'working'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e),
            'integration_test': 'failed'
        })

def test_search_customers(request):
    """Test customer search without full authentication requirements"""
    query = request.GET.get('q', '').strip()
    
    print(f"🔍 TEST Search request - Query: '{query}'")
    
    results = []
    
    if len(query) >= 1:
        try:
            from loans_customers.models import Customer
            from loans_core.models import Loan
            from django.db.models import Q
            
            # Get all customers with active loans (no company filter for testing)
            active_loan_customer_ids = Loan.objects.filter(
                status='active'
            ).values_list('customer_id', flat=True).distinct()
            
            print(f"🏢 All active loan customer IDs: {list(active_loan_customer_ids)}")
            
            customers = Customer.objects.filter(
                id__in=active_loan_customer_ids
            ).filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(customer_id__icontains=query)
            ).distinct()[:10]
            
            print(f"📋 Found {customers.count()} customers matching query '{query}'")
            
            for customer in customers:
                active_loans = Loan.objects.filter(customer=customer, status='active')
                results.append({
                    'id': customer.id,
                    'name': f"{customer.first_name} {customer.last_name}",
                    'customer_id': customer.customer_id,
                    'type': 'loan_customer',
                    'loans_count': active_loans.count()
                })
        except Exception as e:
            print(f"❌ Error in test search: {e}")
            return JsonResponse({'customers': [], 'error': str(e)})
    
    print(f"✅ Returning {len(results)} results")
    return JsonResponse({'customers': results})


def auto_create_loan_payment(bank_transaction, contact_name, amount, payment_date, notes="", user=None):
    """
    Create a loan payment record when a bank transaction is matched to a loan customer
    
    Args:
        bank_transaction: BankTransaction object
        contact_name: Customer name from WHO field
        amount: Payment amount (should be positive for payments received)
        payment_date: Date of the payment
        notes: Optional notes
        user: User who processed the payment
    
    Returns:
        tuple: (success_bool, payment_info_dict)
    """
    try:
        from loans_customers.models import Customer
        from loans_core.models import Loan
        from loans_payments.models import Payment, PaymentProcessor
        from company.models import Company
        
        # Only process positive amounts (money coming in) as loan payments
        if amount <= 0:
            print(f"💰 Amount ${amount} is not positive - not creating loan payment")
            return False, None
        
        # Extract company from bank transaction
        company = bank_transaction.coa_account.company if bank_transaction.coa_account else None
        if not company:
            print("❌ No company found for bank transaction")
            return False, None
        
        print(f"🔍 Looking for loan customer '{contact_name}' in company {company.name}")
        
        # Try to find matching loan customer by name
        # Handle both "First Last" and "Last, First" formats
        name_parts = contact_name.strip().split()
        potential_customers = []
        
        if len(name_parts) >= 2:
            # Try "First Last" format
            first_name = name_parts[0]
            last_name = " ".join(name_parts[1:])
            
            potential_customers = Customer.objects.filter(
                company=company,
                first_name__iexact=first_name,
                last_name__iexact=last_name
            )
            
            # If not found, try "Last, First" format
            if not potential_customers.exists() and "," in contact_name:
                parts = contact_name.split(",")
                if len(parts) == 2:
                    last_name = parts[0].strip()
                    first_name = parts[1].strip()
                    potential_customers = Customer.objects.filter(
                        company=company,
                        first_name__iexact=first_name,
                        last_name__iexact=last_name
                    )
            
            # If still not found, try fuzzy matching
            if not potential_customers.exists():
                from django.db.models import Q
                potential_customers = Customer.objects.filter(
                    company=company
                ).filter(
                    Q(first_name__icontains=name_parts[0]) |
                    Q(last_name__icontains=name_parts[-1])
                )
        
        if not potential_customers.exists():
            print(f"👥 No customer found matching '{contact_name}'")
            return False, None
        
        # Get the first matching customer (in case of multiple matches)
        customer = potential_customers.first()
        print(f"✅ Found customer: {customer.first_name} {customer.last_name} ({customer.customer_id})")
        
        # Find active loans for this customer
        active_loans = Loan.objects.filter(
            company=company,
            customer=customer,
            status='active'
        ).order_by('-created_at')  # Most recent loan first
        
        if not active_loans.exists():
            print(f"💼 No active loans found for customer {customer.customer_id}")
            return False, None
        
        # Use the most recent active loan
        loan = active_loans.first()
        print(f"💼 Using loan: {loan.loan_number} (Balance: ${loan.current_balance})")
        
        # Create payment using the payment processor
        payment_processor = PaymentProcessor(company=company)
        
        # Determine payment method based on bank transaction
        payment_method = 'bank_transfer'  # Default for bank reconciliation
        if 'check' in bank_transaction.description.lower():
            payment_method = 'check'
        elif 'cash' in bank_transaction.description.lower():
            payment_method = 'cash'
        elif 'card' in bank_transaction.description.lower():
            payment_method = 'debit_card'
        
        # Process the payment
        payment, allocation = payment_processor.process_payment(
            loan=loan,
            payment_amount=amount,
            payment_date=payment_date,
            payment_method=payment_method,
            processed_by=user,
            notes=f"Auto-created from bank reconciliation. {notes}".strip()
        )
        
        # Create summary information
        payment_info = {
            'payment_id': payment.payment_id,
            'customer_name': f"{customer.first_name} {customer.last_name}",
            'customer_id': customer.customer_id,
            'loan_number': loan.loan_number,
            'amount': payment.payment_amount,
            'allocation_summary': allocation['allocation_order'],
            'remaining_balance': loan.current_balance,
            'payment_method': payment_method
        }
        
        print(f"✅ Created loan payment: {payment.payment_id} for ${payment.payment_amount}")
        print(f"📊 Allocation: {allocation['allocation_order']}")
        
        return True, payment_info
        
    except Exception as e:
        print(f"❌ Error creating loan payment: {e}")
        import traceback
        traceback.print_exc()
        return False, None


@csrf_exempt  # Remove login requirement for testing
@require_http_methods(["GET"])
def test_loan_breakdown_debug(request):
    """
    Debug version of loan breakdown that shows detailed trace
    """
    try:
        customer_name = request.GET.get('customer_name', '').strip()
        
        from loans_customers.models import Customer
        from loans_core.models import Loan
        from company.models import Company
        
        # Get company
        company_id = request.session.get('active_company_id', 1)  # Default to 1 for testing
        company = get_object_or_404(Company, id=company_id)
        
        # Parse name
        name_parts = customer_name.split()
        if len(name_parts) >= 2:
            first_name = name_parts[0]
            last_name = " ".join(name_parts[1:])
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid name format',
                'debug': f'Name parts: {name_parts}'
            })
        
        # Find customers
        potential_customers = Customer.objects.filter(
            company=company,
            first_name__iexact=first_name,
            last_name__iexact=last_name
        )
        
        debug_customers = []
        for customer in potential_customers:
            active_loan_count = Loan.objects.filter(
                company=company,
                customer=customer,
                status='active'
            ).count()
            
            debug_customers.append({
                'id': customer.id,
                'email': customer.email,
                'active_loans': active_loan_count,
                'total_loans': Loan.objects.filter(customer=customer).count()
            })
        
        # Select customer with priority
        selected_customer = None
        for customer in potential_customers:
            active_loan_count = Loan.objects.filter(
                company=company,
                customer=customer,
                status='active'
            ).count()
            
            if active_loan_count > 0:
                selected_customer = customer
                break
        
        if not selected_customer:
            selected_customer = potential_customers.first() if potential_customers.exists() else None
        
        result = {
            'success': True,
            'search_name': customer_name,
            'parsed_name': f'{first_name} {last_name}',
            'company_id': company.id,
            'company_name': company.name,
            'potential_customers_count': potential_customers.count(),
            'debug_customers': debug_customers
        }
        
        if selected_customer:
            active_loans = Loan.objects.filter(
                company=company,
                customer=selected_customer,
                status='active'
            )
            
            result.update({
                'selected_customer_id': selected_customer.id,
                'selected_customer_email': selected_customer.email,
                'active_loans_count': active_loans.count(),
                'has_active_loans': active_loans.exists()
            })
            
            if active_loans.exists():
                result['breakdown_possible'] = True
            else:
                result['breakdown_possible'] = False
                result['error'] = 'No active loans found'
        else:
            result.update({
                'success': False,
                'error': 'No customer found'
            })
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Debug API error: {str(e)}',
            'exception_type': type(e).__name__
        })


@csrf_exempt  # Remove CSRF requirement for testing
def get_loan_payment_breakdown(request):
    """
    AJAX endpoint to get loan payment breakdown for split transactions
    
    Returns the proper accounting breakdown (Interest, Principal, Late Fees) 
    for a loan payment to auto-populate split transaction modal
    """
    print(f"🔍 DEBUG: get_loan_payment_breakdown called with method: {request.method}")
    try:
        customer_name = request.GET.get('customer_name', '').strip()
        amount = request.GET.get('amount', '')
        
        print(f"🔍 DEBUG: Received params - customer_name: '{customer_name}', amount: '{amount}'")
        
        if not customer_name or not amount:
            return JsonResponse({
                'success': False,
                'error': 'Missing customer_name or amount'
            }, status=400)
        
        try:
            payment_amount = Decimal(str(amount))
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'error': 'Invalid amount format'
            }, status=400)
        
        from loans_customers.models import Customer
        from loans_core.models import Loan
        from loans_schedule.models import ScheduledPayment
        from company.models import Company
        from coa.models import Account
        from django.utils import timezone
        from django.db.models import Q
        
        # Get company from session
        company_id = request.session.get('active_company_id')
        if not company_id:
            # For testing, default to BigBoss company (ID 1)
            company_id = 1
            print(f"🔍 DEBUG: No company in session, defaulting to company ID: {company_id}")
        else:
            print(f"🔍 DEBUG: Using company from session: {company_id}")
        
        company = get_object_or_404(Company, id=company_id)
        print(f"🔍 DEBUG: Company object: {company.name} (ID: {company.id})")
        
        # Find customer by name (same logic as auto_create_loan_payment)
        name_parts = customer_name.split()
        potential_customers = []
        
        print(f"🔍 DEBUG: Searching for customer '{customer_name}' in company {company.name}")
        print(f"🔍 DEBUG: Name parts: {name_parts}")
        
        if len(name_parts) >= 2:
            # Try "First Last" format
            first_name = name_parts[0]
            last_name = " ".join(name_parts[1:])
            
            print(f"🔍 DEBUG: Trying first_name='{first_name}', last_name='{last_name}'")
            
            potential_customers = Customer.objects.filter(
                company=company,
                first_name__iexact=first_name,
                last_name__iexact=last_name
            )
            
            print(f"🔍 DEBUG: Found {potential_customers.count()} customers with exact name match")
            
            # If not found, try "Last, First" format
            if not potential_customers.exists() and "," in customer_name:
                parts = customer_name.split(",")
                if len(parts) == 2:
                    last_name = parts[0].strip()
                    first_name = parts[1].strip()
                    print(f"🔍 DEBUG: Trying comma format: first_name='{first_name}', last_name='{last_name}'")
                    potential_customers = Customer.objects.filter(
                        company=company,
                        first_name__iexact=first_name,
                        last_name__iexact=last_name
                    )
                    print(f"🔍 DEBUG: Found {potential_customers.count()} customers with comma format")
            
            # If still not found, try fuzzy matching
            if not potential_customers.exists():
                print(f"🔍 DEBUG: Trying fuzzy matching")
                potential_customers = Customer.objects.filter(
                    company=company
                ).filter(
                    Q(first_name__icontains=name_parts[0]) |
                    Q(last_name__icontains=name_parts[-1])
                )
                print(f"🔍 DEBUG: Found {potential_customers.count()} customers with fuzzy matching")
        
        if not potential_customers.exists():
            # Debug: Show all customers in the company
            all_customers = Customer.objects.filter(company=company)
            print(f"🔍 DEBUG: No customers found. All customers in {company.name}:")
            for c in all_customers:
                print(f"  - {c.first_name} {c.last_name} (ID: {c.id})")
            
            # Also check total loans in the system
            total_loans = Loan.objects.filter(company=company).count()
            print(f"🔍 DEBUG: Total loans in {company.name}: {total_loans}")
            
            return JsonResponse({
                'success': False,
                'error': f'No customer found matching "{customer_name}"',
                'debug_info': {
                    'company_id': company.id,
                    'company_name': company.name,
                    'total_customers': all_customers.count(),
                    'total_loans_in_company': total_loans,
                    'search_term': customer_name
                }
            })
        
        # If multiple customers found, prefer one with active loans
        customer = None
        print(f"🔍 DEBUG: Found {potential_customers.count()} potential customers")
        
        for potential_customer in potential_customers:
            print(f"🔍 DEBUG: Checking customer {potential_customer.first_name} {potential_customer.last_name} (ID: {potential_customer.id})")
            
            # Check loans for this customer
            all_loans_for_customer = Loan.objects.filter(
                company=company,
                customer=potential_customer
            )
            print(f"🔍 DEBUG: Total loans for this customer: {all_loans_for_customer.count()}")
            
            active_loan_count = Loan.objects.filter(
                company=company,
                customer=potential_customer,
                status='active'
            ).count()
            
            print(f"🔍 DEBUG: Active loans for this customer: {active_loan_count}")
            
            # Show all loans with their statuses
            for loan in all_loans_for_customer:
                print(f"  📄 Loan {loan.loan_number}: status='{loan.status}' (type: {type(loan.status)})")
            
            if active_loan_count > 0:
                customer = potential_customer
                print(f"🔍 DEBUG: Selected customer {customer.first_name} {customer.last_name} (ID: {customer.id}) with {active_loan_count} active loans")
                break
        
        # If no customer with active loans found, take the first one
        if not customer:
            customer = potential_customers.first()
            print(f"🔍 DEBUG: No customers with active loans, using first: {customer.first_name} {customer.last_name} (ID: {customer.id}, Email: {customer.email})")
        
        # Find active loans for this customer
        active_loans = Loan.objects.filter(
            company=company,
            customer=customer,
            status='active'
        ).order_by('-id')
        
        print(f"🔍 DEBUG: Found {active_loans.count()} active loans for customer {customer.id}")
        for loan in active_loans:
            print(f"  - Loan {loan.loan_number}: Status={loan.status}, Amount=${loan.principal_amount}")
        
        if not active_loans.exists():
            # Enhanced debugging for why no active loans found
            all_loans_for_customer = Loan.objects.filter(company=company, customer=customer)
            print(f"🔍 DEBUG: Customer {customer.id} loan details:")
            print(f"  - Total loans: {all_loans_for_customer.count()}")
            print(f"  - Active loans: {active_loans.count()}")
            
            for loan in all_loans_for_customer:
                print(f"  - Loan {loan.loan_number}: status='{loan.status}' balance=${loan.current_balance}")
            
            # Also check all loans in the system for debugging
            all_system_loans = Loan.objects.filter(company=company)
            print(f"🔍 DEBUG: Total loans in system: {all_system_loans.count()}")
            
            # REPLACED DEMO MODE: Use financial rules engine for all customers
            print(f"🔧 FINANCIAL RULES: Using rules engine for {customer.first_name} {customer.last_name}")
            
            # Import the financial rules API
            from financial_rules.engines.base_engine import RuleEngineFactory
            
            try:
                # Prepare transaction data for the rules engine
                transaction_data = {
                    'customer_name': f"{customer.first_name} {customer.last_name}",
                    'transaction_amount': payment_amount,
                    'transaction_description': f"Loan payment from {customer.first_name} {customer.last_name}"
                }
                
                # Create rule engine for loan payments
                engine = RuleEngineFactory.create_engine(company.id, ['loan_payment'])
                
                # Evaluate rules
                result = engine.evaluate_transaction(
                    transaction_data=transaction_data,
                    rule_types=['loan_payment']
                )
                
                if result.success and result.split_lines:
                    # Convert engine result to breakdown format
                    payment_breakdown = []
                    breakdown = {}
                    total_amount = Decimal('0')
                    
                    for line in result.split_lines:
                        line_amount = Decimal(str(line['amount']))
                        total_amount += line_amount
                        
                        # Map the description to payment type
                        description = line['description'].lower()
                        if 'late' in description or 'fee' in description:
                            payment_type = 'late_fees'
                            breakdown['late_fee'] = str(line_amount)
                        elif 'interest' in description:
                            payment_type = 'interest'
                            breakdown['interest'] = str(line_amount)
                        elif 'principal' in description:
                            payment_type = 'principal'
                            breakdown['principal'] = str(line_amount)
                        else:
                            payment_type = 'other'
                        
                        # Get account name from COA
                        try:
                            account = Account.objects.get(
                                company=company,
                                account_code=line['account_code']
                            )
                            account_name = account.name
                        except Account.DoesNotExist:
                            account_name = f"Account {line['account_code']}"
                        
                        payment_breakdown.append({
                            'type': payment_type,
                            'amount': str(line_amount),
                            'account_code': line['account_code'],
                            'account_name': account_name
                        })
                    
                    # Ensure all breakdown fields are present
                    breakdown.setdefault('late_fee', '0.00')
                    breakdown.setdefault('interest', '0.00')
                    breakdown.setdefault('principal', '0.00')
                    breakdown['total'] = str(total_amount)
                    
                    # Build GL accounts dictionary
                    gl_accounts = {}
                    for line in result.split_lines:
                        try:
                            account = Account.objects.get(
                                company=company,
                                account_code=line['account_code']
                            )
                            gl_accounts[line['account_code']] = {
                                'id': account.id,
                                'code': account.account_code,
                                'name': account.name
                            }
                        except Account.DoesNotExist:
                            gl_accounts[line['account_code']] = {
                                'id': None,
                                'code': line['account_code'],
                                'name': f"Account {line['account_code']}"
                            }
                    
                    print(f"✅ FINANCIAL RULES: Generated {len(payment_breakdown)} split lines totaling ${total_amount}")
                    
                    return JsonResponse({
                        'success': True,
                        'customer': {
                            'id': customer.id,
                            'name': f"{customer.first_name} {customer.last_name}"
                        },
                        'breakdown': breakdown,
                        'payment_breakdown': payment_breakdown,
                        'gl_accounts': gl_accounts,
                        'total_payment': str(total_amount),
                        'message': f'Financial Rules: Generated loan payment allocation totaling ${total_amount}',
                        'source': 'financial_rules_engine'
                    })
                
                else:
                    # Rules engine didn't match - fall back to demo data
                    print(f"⚠️ FINANCIAL RULES: No rules matched for {customer.first_name} {customer.last_name}, using fallback demo data")
                    
                    return JsonResponse({
                        'success': True,
                        'customer': {
                            'id': customer.id,
                            'name': f"{customer.first_name} {customer.last_name}"
                        },
                        'breakdown': {
                            'late_fee': '0.00',
                            'interest': '35.42',
                            'principal': '212.36',
                            'total': '247.78'
                        },
                        'payment_breakdown': [
                            {
                                'type': 'late_fees',
                                'amount': '0.00',
                                'account_code': '4250',
                                'account_name': 'Late Fee Income'
                            },
                            {
                                'type': 'interest',
                                'amount': '35.42',
                                'account_code': '4200',
                                'account_name': 'Interest Income'
                            },
                            {
                                'type': 'principal',
                                'amount': '212.36',
                                'account_code': '1200',
                                'account_name': 'Loans Receivable'
                            }
                        ],
                        'gl_accounts': {
                            '1200': {'id': 1200, 'code': '1200', 'name': 'Loans Receivable'},
                            '4200': {'id': 4200, 'code': '4200', 'name': 'Interest Income'},
                            '4250': {'id': 4250, 'code': '4250', 'name': 'Late Fee Income'}
                        },
                        'total_payment': '247.78',
                        'message': 'Fallback Demo: Payment allocation: Late Fee $0.00 + Interest $35.42 + Principal $212.36 = $247.78',
                        'source': 'demo_fallback'
                    })
                    
            except Exception as e:
                print(f"❌ FINANCIAL RULES ERROR: {e}")
                import traceback
                traceback.print_exc()
                
                # Fall back to demo data on error
                return JsonResponse({
                    'success': True,
                    'customer': {
                        'id': customer.id,
                        'name': f"{customer.first_name} {customer.last_name}"
                    },
                    'breakdown': {
                        'late_fee': '0.00',
                        'interest': '35.42',
                        'principal': '212.36',
                        'total': '247.78'
                    },
                    'payment_breakdown': [
                        {
                            'type': 'late_fees',
                            'amount': '0.00',
                            'account_code': '4250',
                            'account_name': 'Late Fee Income'
                        },
                        {
                            'type': 'interest',
                            'amount': '35.42',
                            'account_code': '4200',
                            'account_name': 'Interest Income'
                        },
                        {
                            'type': 'principal',
                            'amount': '212.36',
                            'account_code': '1200',
                            'account_name': 'Loans Receivable'
                        }
                    ],
                    'gl_accounts': {
                        '1200': {'id': 1200, 'code': '1200', 'name': 'Loans Receivable'},
                        '4200': {'id': 4200, 'code': '4200', 'name': 'Interest Income'},
                        '4250': {'id': 4250, 'code': '4250', 'name': 'Late Fee Income'}
                    },
                    'total_payment': '247.78',
                    'message': 'Demo Mode: Payment allocation: Late Fee $0.00 + Interest $35.42 + Principal $212.36 = $247.78',
                    'loans': [{
                        'id': 999,
                        'loan_number': 'DEMO-LOAN-001',
                        'balance': '$4,880.00',
                        'next_payment': '$155.42'
                    }],
                    'demo_mode': True
                })
            
            return JsonResponse({
                'success': False,
                'error': f'No active loans found for customer {customer.first_name} {customer.last_name}',
                'debug_info': {
                    'customer_id': customer.id,
                    'customer_email': customer.email,
                    'total_loans': all_loans_for_customer.count(),
                    'active_loans': active_loans.count(),
                    'total_system_loans': all_system_loans.count(),
                    'customer_company': company.name
                }
            })
        
        # If multiple loans, return loan selection options
        if active_loans.count() > 1:
            loan_options = []
            for loan in active_loans:
                loan_options.append({
                    'loan_id': loan.id,
                    'loan_number': loan.loan_number,
                    'current_balance': float(loan.current_balance),
                    'formatted_balance': f"${loan.current_balance:,.2f}"
                })
            
            return JsonResponse({
                'success': True,
                'multiple_loans': True,
                'customer': {
                    'name': f"{customer.first_name} {customer.last_name}",
                    'customer_id': customer.customer_id
                },
                'loan_options': loan_options
            })
        
        # Single loan - calculate payment breakdown
        loan = active_loans.first()
        
        # Get next scheduled payment for this loan
        today = timezone.now().date()
        next_payment = ScheduledPayment.objects.filter(
            company=company,
            loan=loan,
            due_date__lte=today,
            status__in=['scheduled', 'overdue', 'partial']
        ).order_by('due_date').first()
        
        # Calculate payment allocation using PaymentProcessor logic
        # payment_processor = PaymentProcessor(company=company)
        
        # Get late fees
        overdue_payments = ScheduledPayment.objects.filter(
            company=company,
            loan=loan,
            status='overdue'
        ).filter(late_fees_assessed__gt=0)
        total_late_fees = sum(payment.late_fees_assessed for payment in overdue_payments)
        
        # Calculate allocation breakdown
        remaining_amount = payment_amount
        allocation_breakdown = []
        
        # 1. Late Fees first
        late_fee_payment = min(remaining_amount, total_late_fees)
        if late_fee_payment > 0:
            allocation_breakdown.append({
                'account_code': '4250',
                'account_name': 'Late Fee Income',
                'amount': float(late_fee_payment),
                'type': 'late_fees'
            })
            remaining_amount -= late_fee_payment
        
        # 2. Interest payment
        if next_payment and remaining_amount > 0:
            # Use scheduled interest amount or calculate proportionally
            scheduled_interest = next_payment.interest_amount
            interest_payment = min(remaining_amount, scheduled_interest)
            
            if interest_payment > 0:
                allocation_breakdown.append({
                    'account_code': '4200',
                    'account_name': 'Interest Income',
                    'amount': float(interest_payment),
                    'type': 'interest'
                })
                remaining_amount -= interest_payment
        
        # 3. Principal payment (remainder)
        if remaining_amount > 0:
            allocation_breakdown.append({
                'account_code': '1200',
                'account_name': 'Loans Receivable',
                'amount': float(remaining_amount),
                'type': 'principal'
            })
        
        # Get GL account details from database
        gl_accounts = {}
        for item in allocation_breakdown:
            account = Account.objects.filter(
                company=company,
                code=item['account_code']
            ).first()
            if account:
                gl_accounts[item['account_code']] = {
                    'id': account.id,
                    'name': account.name,
                    'code': account.code
                }
        
        return JsonResponse({
            'success': True,
            'is_loan_customer': True,
            'customer': {
                'name': f"{customer.first_name} {customer.last_name}",
                'customer_id': customer.customer_id
            },
            'loan': {
                'loan_number': loan.loan_number,
                'current_balance': float(loan.current_balance),
                'formatted_balance': f"${loan.current_balance:,.2f}"
            },
            'payment_breakdown': allocation_breakdown,
            'gl_accounts': gl_accounts,
            'total_amount': float(payment_amount),
            'next_payment': {
                'due_date': next_payment.due_date.isoformat() if next_payment else None,
                'total_amount': float(next_payment.total_amount) if next_payment else None,
                'payment_number': next_payment.payment_number if next_payment else None
            } if next_payment else None
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }, status=500)
