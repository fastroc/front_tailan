"""
AJAX endpoints for split transaction functionality
"""

import json
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from coa.models import Account
from bank_accounts.models import BankTransaction
from .reconciliation_service import ReconciliationService
from .models import TransactionMatch


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def create_split_transaction(request):
    """AJAX endpoint for creating split transactions"""
    try:
        data = json.loads(request.body)
        
        # Extract data from request
        transaction_id = data.get('transaction_id')
        contact = data.get('contact', '')
        description = data.get('description', '')
        splits = data.get('splits', [])
        
        # Validate required fields
        if not transaction_id:
            return JsonResponse({
                'success': False,
                'error': 'Missing required field: transaction_id'
            }, status=400)
        
        if not splits or len(splits) < 2:
            return JsonResponse({
                'success': False,
                'error': 'At least 2 splits are required for a split transaction'
            }, status=400)
        
        # Get the bank transaction
        try:
            bank_transaction = get_object_or_404(BankTransaction, id=transaction_id)
        except BankTransaction.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Bank transaction not found'
            }, status=404)
        
        # Validate splits
        total_amount = Decimal('0')
        for i, split in enumerate(splits):
            if not split.get('gl_account_id') or not split.get('amount'):
                return JsonResponse({
                    'success': False,
                    'error': f'Split {i+1}: Missing GL account or amount'
                }, status=400)
            
            try:
                amount = Decimal(str(split['amount']))
                total_amount += amount
            except (ValueError, TypeError):
                return JsonResponse({
                    'success': False,
                    'error': f'Split {i+1}: Invalid amount format'
                }, status=400)
            
            # Validate GL account exists
            try:
                get_object_or_404(Account, id=split['gl_account_id'])
            except Account.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'Split {i+1}: GL account not found'
                }, status=404)
        
        # Validate total amount matches bank transaction
        bank_amount = abs(bank_transaction.amount)
        if abs(total_amount - bank_amount) > Decimal('0.01'):
            return JsonResponse({
                'success': False,
                'error': f'Split total ({total_amount}) does not match transaction amount ({bank_amount})'
            }, status=400)
        
        # Get or create reconciliation session
        reconciliation_session = ReconciliationService.get_or_create_session(
            bank_transaction.coa_account, request.user
        )
        
        # Prepare split data
        split_data = {
            'contact': contact,
            'description': description,
            'splits': splits
        }
        
        # Use reconciliation service to create the split transaction
        match = ReconciliationService.create_split_transaction(
            bank_transaction=bank_transaction,
            reconciliation_session=reconciliation_session,
            split_data=split_data,
            user=request.user
        )
        
        if match:
            # Get split details for response
            split_details = []
            for split in match.splits.all():
                split_details.append({
                    'id': split.id,
                    'split_number': split.split_number,
                    'amount': float(split.amount),
                    'gl_account': split.gl_account.name,
                    'description': split.description,
                    'tax_rate': split.tax_rate,
                    'tax_amount': float(split.tax_amount),
                    'net_amount': float(split.net_amount)
                })
            
            return JsonResponse({
                'success': True,
                'message': 'Split transaction created successfully',
                'match_id': match.id,
                'journal_id': match.journal_entry.id if match.journal_entry else None,
                'splits': split_details,
                'total_splits': len(split_details),
                'balance_status': match.split_balance_status,
                'transaction': {
                    'id': bank_transaction.id,
                    'description': bank_transaction.description,
                    'amount': float(bank_transaction.amount),
                    'matched': True,
                    'is_split': True
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to create split transaction'
            }, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
        
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_transaction_splits(request, match_id):
    """AJAX endpoint for getting split details of a transaction"""
    try:
        # Get the transaction match
        try:
            match = get_object_or_404(TransactionMatch, id=match_id)
        except TransactionMatch.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Transaction match not found'
            }, status=404)
        
        if not match.is_split_transaction:
            return JsonResponse({
                'success': False,
                'error': 'Transaction is not a split transaction'
            }, status=400)
        
        # Get split details
        splits = []
        for split in match.splits.all():
            splits.append({
                'id': split.id,
                'split_number': split.split_number,
                'amount': float(split.amount),
                'contact': split.contact,
                'gl_account': {
                    'id': split.gl_account.id,
                    'code': split.gl_account.code,
                    'name': split.gl_account.name
                },
                'description': split.description,
                'tax_rate': split.tax_rate,
                'tax_amount': float(split.tax_amount),
                'net_amount': float(split.net_amount),
                'created_at': split.created_at.isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'match_id': match.id,
            'bank_transaction': {
                'id': match.bank_transaction.id,
                'amount': float(match.bank_transaction.amount),
                'description': match.bank_transaction.description
            },
            'splits': splits,
            'total_splits': len(splits),
            'total_amount': float(match.total_split_amount),
            'balance_status': match.split_balance_status,
            'remaining_amount': float(match.remaining_amount)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error getting split details: {str(e)}'
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def validate_split_balance(request):
    """AJAX endpoint for validating split transaction balance"""
    try:
        data = json.loads(request.body)
        
        transaction_amount = data.get('transaction_amount')
        splits = data.get('splits', [])
        
        if not transaction_amount:
            return JsonResponse({
                'success': False,
                'error': 'Missing transaction_amount'
            }, status=400)
        
        # Calculate total from splits
        total_amount = Decimal('0')
        split_details = []
        
        for i, split in enumerate(splits):
            try:
                amount = Decimal(str(split.get('amount', 0)))
                total_amount += amount
                
                split_details.append({
                    'split_number': i + 1,
                    'amount': float(amount),
                    'gl_account_id': split.get('gl_account_id'),
                    'valid': bool(amount > 0 and split.get('gl_account_id'))
                })
            except (ValueError, TypeError):
                split_details.append({
                    'split_number': i + 1,
                    'amount': 0,
                    'gl_account_id': split.get('gl_account_id'),
                    'valid': False,
                    'error': 'Invalid amount'
                })
        
        # Calculate balance
        bank_amount = abs(Decimal(str(transaction_amount)))
        difference = bank_amount - total_amount
        
        # Determine status
        if abs(difference) < Decimal('0.01'):
            status = 'balanced'
        elif total_amount < bank_amount:
            status = 'under_allocated'
        else:
            status = 'over_allocated'
        
        return JsonResponse({
            'success': True,
            'balance_check': {
                'transaction_amount': float(bank_amount),
                'total_allocated': float(total_amount),
                'difference': float(difference),
                'status': status,
                'is_valid': status == 'balanced',
                'splits': split_details,
                'split_count': len(splits)
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
            'error': f'Error validating balance: {str(e)}'
        }, status=500)
