"""
Bank Rules Views
----------------
CRUD interface for managing bank reconciliation rules.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction as db_transaction
from company.views import get_active_company
from coa.models import Account
from bank_accounts.models import BankTransaction
from .models import BankRule, BankRuleCondition
from .services import RuleEngineService


@login_required
def list_rules(request):
    """List all bank rules for current company"""
    # Get current company using the standard utility function
    company = get_active_company(request)
    
    rules = BankRule.objects.filter(company=company).prefetch_related('conditions').order_by('-priority', '-created_at')
    
    context = {
        'rules': rules,
        'company': company,
    }
    
    return render(request, 'bank_rules/rules_list.html', context)


@login_required
def create_rule(request):
    """Create new bank rule"""
    company = get_active_company(request)
    
    if request.method == 'POST':
        try:
            with db_transaction.atomic():
                # Create rule
                rule = BankRule.objects.create(
                    company=company,
                    name=request.POST.get('name'),
                    description=request.POST.get('description', ''),
                    match_logic=request.POST.get('match_logic', 'ALL'),
                    priority=int(request.POST.get('priority', 0)),
                    is_active=request.POST.get('is_active') == 'on',
                    created_by=request.user,
                    suggested_who_text=request.POST.get('suggested_who_text', ''),
                    suggested_coa_id=request.POST.get('suggested_coa') or None
                )
                
                # Create conditions
                fields = request.POST.getlist('field[]')
                operators = request.POST.getlist('operator[]')
                values = request.POST.getlist('value[]')
                
                for i, (field, operator, value) in enumerate(zip(fields, operators, values)):
                    if field and operator:  # Skip empty conditions
                        BankRuleCondition.objects.create(
                            rule=rule,
                            field=field,
                            operator=operator,
                            value=value,
                            order=i
                        )
                
                messages.success(request, f'Rule "{rule.name}" created successfully!')
                return redirect('bank_rules:list')
                
        except Exception as e:
            messages.error(request, f'Error creating rule: {e}')
    
    # Get data for form
    coa_accounts = Account.objects.filter(company=company).order_by('code')
    
    context = {
        'company': company,
        'coa_accounts': coa_accounts,
        'field_choices': BankRuleCondition.FIELD_CHOICES,
        'operator_choices': BankRuleCondition.OPERATOR_CHOICES,
    }
    
    return render(request, 'bank_rules/rule_form.html', context)


@login_required
def edit_rule(request, rule_id):
    """Edit existing bank rule"""
    company = get_active_company(request)
    rule = get_object_or_404(BankRule, id=rule_id, company=company)
    
    if request.method == 'POST':
        try:
            with db_transaction.atomic():
                # Update rule
                rule.name = request.POST.get('name')
                rule.description = request.POST.get('description', '')
                rule.match_logic = request.POST.get('match_logic', 'ALL')
                rule.priority = int(request.POST.get('priority', 0))
                rule.is_active = request.POST.get('is_active') == 'on'
                
                # Update suggested actions
                rule.suggested_who_text = request.POST.get('suggested_who_text', '')
                rule.suggested_coa_id = request.POST.get('suggested_coa') or None
                
                rule.save()
                
                # Delete old conditions and create new ones
                rule.conditions.all().delete()
                
                fields = request.POST.getlist('field[]')
                operators = request.POST.getlist('operator[]')
                values = request.POST.getlist('value[]')
                
                for i, (field, operator, value) in enumerate(zip(fields, operators, values)):
                    if field and operator:
                        BankRuleCondition.objects.create(
                            rule=rule,
                            field=field,
                            operator=operator,
                            value=value,
                            order=i
                        )
                
                messages.success(request, f'Rule "{rule.name}" updated successfully!')
                return redirect('bank_rules:list')
                
        except Exception as e:
            messages.error(request, f'Error updating rule: {e}')
    
    # Get data for form
    coa_accounts = Account.objects.filter(company=company).order_by('code')
    
    context = {
        'rule': rule,
        'company': company,
        'coa_accounts': coa_accounts,
        'field_choices': BankRuleCondition.FIELD_CHOICES,
        'operator_choices': BankRuleCondition.OPERATOR_CHOICES,
    }
    
    return render(request, 'bank_rules/rule_form.html', context)


@login_required
def delete_rule(request, rule_id):
    """Delete bank rule"""
    company = get_active_company(request)
    rule = get_object_or_404(BankRule, id=rule_id, company=company)
    
    if request.method == 'POST':
        rule_name = rule.name
        rule.delete()
        messages.success(request, f'Rule "{rule_name}" deleted successfully!')
        return redirect('bank_rules:list')
    
    return render(request, 'bank_rules/rule_confirm_delete.html', {'rule': rule})


@login_required
def toggle_rule(request, rule_id):
    """Toggle rule active status"""
    company = get_active_company(request)
    rule = get_object_or_404(BankRule, id=rule_id, company=company)
    
    rule.is_active = not rule.is_active
    rule.save()
    
    status = "enabled" if rule.is_active else "disabled"
    messages.success(request, f'Rule "{rule.name}" {status}!')
    
    return redirect('bank_rules:list')


@login_required
def test_rule(request, rule_id):
    """Test rule against recent transactions"""
    company = get_active_company(request)
    rule = get_object_or_404(BankRule, id=rule_id, company=company)
    
    # Get recent transactions (last 100) - filter by company directly
    recent_transactions = BankTransaction.objects.filter(
        company=company
    ).order_by('-date', '-id')[:100]
    
    # Test rule against each transaction
    matches = []
    for trans in recent_transactions:
        # Convert to dict format expected by rule engine
        trans_dict = {
            'id': trans.id,
            'description': trans.description or '',
            'amount': float(trans.amount),
            'correspondent_account': trans.related_account or '',
            'transaction_date': trans.date,
            'reference_number': trans.reference or '',
            'debit_credit': 'debit' if trans.amount < 0 else 'credit',
        }
        
        if RuleEngineService._rule_matches(trans_dict, rule):
            matches.append(trans)
    
    context = {
        'rule': rule,
        'matches': matches,
        'total_tested': recent_transactions.count(),
        'match_count': len(matches),
    }
    
    return render(request, 'bank_rules/rule_test.html', context)

