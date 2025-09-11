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
        
        # Match creation includes journal entry and session statistics update
        if match:
            return JsonResponse({
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
            })
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
        
        # Convert to JSON serializable format
        transactions = []
        for transaction in unmatched:
            transactions.append({
                'id': transaction.id,
                'date': transaction.date.strftime('%Y-%m-%d'),
                'description': transaction.description,
                'reference': transaction.reference or '',
                'memo': transaction.memo or '',
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
