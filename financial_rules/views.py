"""
Financial Rules Views

Provides both web interface and REST API endpoints for financial rule 
evaluation and management. Used by the reconciliation system to automatically 
split transactions and provides user-friendly interfaces for rule management.
"""

import json
import logging
from decimal import Decimal
from typing import Dict, Any
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse, HttpRequest
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView

from .models import BaseFinancialRule, RuleExecutionLog
from .engines.base_engine import RuleEngineFactory
from company.models import Company

logger = logging.getLogger(__name__)


class FinancialRulesAPIError(Exception):
    """Custom exception for Financial Rules API errors"""
    pass


def get_user_company(request):
    """
    Get the active company for the current user from session
    
    Returns:
        Company instance or None if no active company
    """
    company_id = request.session.get('active_company_id')
    if not company_id:
        return None
        
    try:
        return Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        return None


def validate_transaction_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate incoming transaction data for rule evaluation
    
    Args:
        data: Raw transaction data dictionary
        
    Returns:
        Validated and normalized transaction data
        
    Raises:
        FinancialRulesAPIError: If validation fails
    """
    required_fields = ['customer_name', 'transaction_amount']
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        raise FinancialRulesAPIError(f"Missing required fields: {', '.join(missing_fields)}")
    
    try:
        # Normalize transaction amount
        amount = data['transaction_amount']
        if isinstance(amount, str):
            amount = Decimal(amount.replace('$', '').replace(',', ''))
        else:
            amount = Decimal(str(amount))
        
        if amount <= 0:
            raise FinancialRulesAPIError("Transaction amount must be positive")
            
        normalized_data = {
            'customer_name': str(data['customer_name']).strip(),
            'transaction_amount': amount,
            'transaction_description': str(data.get('transaction_description', '')).strip(),
            'account_code': str(data.get('account_code', '')).strip(),
            'transaction_date': data.get('transaction_date'),
            'reference_number': str(data.get('reference_number', '')).strip(),
        }
        
        return normalized_data
        
    except (ValueError, TypeError) as e:
        raise FinancialRulesAPIError(f"Invalid transaction amount: {e}")


@method_decorator([login_required], name='dispatch')
class EvaluateRulesView(View):
    """
    API endpoint for evaluating financial rules against transaction data
    """
    
    def post(self, request: HttpRequest) -> JsonResponse:
        """
        Evaluate financial rules for a transaction
        
        Expected POST data:
        {
            "customer_name": "Customer Name",
            "transaction_amount": 100.50,
            "transaction_description": "Optional description",
            "account_code": "Optional account code",
            "rule_type": "loan_payment"  // Optional, defaults to all types
        }
        
        Returns:
        {
            "success": true,
            "split_data": [
                {
                    "description": "Interest Payment",
                    "account_code": "2100",
                    "amount": "50.25"
                }
            ],
            "total_allocated": "100.50",
            "rules_matched": 2,
            "execution_logs": ["log_id_1", "log_id_2"]
        }
        """
        try:
            # Get user's active company
            company = get_user_company(request)
            if not company:
                return JsonResponse({
                    'success': False,
                    'error_message': 'No active company found. Please select a company.',
                    'error_type': 'company_error'
                }, status=400)
            
            # Parse request data
            if request.content_type == 'application/json':
                data = json.loads(request.body.decode('utf-8'))
            else:
                data = request.POST.dict()
            
            # Validate transaction data
            transaction_data = validate_transaction_data(data)
            
            # Get rule type filter
            rule_type = data.get('rule_type', 'all')
            
            # Get appropriate rule engine
            rule_types = [rule_type] if rule_type != 'all' else None
            engine = RuleEngineFactory.create_engine(company.id, rule_types)
            
            # Evaluate rules
            result = engine.evaluate_transaction(
                transaction_data=transaction_data,
                rule_types=rule_types
            )
            
            # Prepare response
            response_data = {
                'success': True,
                'split_data': [
                    {
                        'description': line['description'],
                        'account_code': line['account_code'],
                        'amount': str(line['amount'])
                    }
                    for line in result.split_lines
                ],
                'total_allocated': str(result.total_allocated),
                'rules_matched': len(result.matched_rules),
                'execution_logs': [str(log.id) for log in result.execution_logs]
            }
            
            logger.info(f"Rule evaluation successful: {len(result.split_lines)} split lines generated")
            return JsonResponse(response_data)
            
        except FinancialRulesAPIError as e:
            logger.warning(f"Rule evaluation validation error: {e}")
            return JsonResponse({
                'success': False,
                'error_message': str(e),
                'error_type': 'validation_error'
            }, status=400)
            
        except Exception as e:
            logger.error(f"Rule evaluation unexpected error: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error_message': 'An unexpected error occurred during rule evaluation',
                'error_type': 'server_error'
            }, status=500)


@method_decorator([login_required], name='dispatch')
class TestRuleView(View):
    """
    API endpoint for testing a specific financial rule
    """
    
    def post(self, request: HttpRequest, rule_id: int) -> JsonResponse:
        """
        Test a specific financial rule with provided transaction data
        
        URL: /financial_rules/test/<rule_id>/
        """
        try:
            # Get user's active company
            company = get_user_company(request)
            if not company:
                return JsonResponse({
                    'success': False,
                    'error_message': 'No active company found. Please select a company.',
                    'error_type': 'company_error'
                }, status=400)
            
            # Get the rule
            rule = get_object_or_404(
                BaseFinancialRule,
                id=rule_id,
                company=company
            )
            
            # Parse test data
            if request.content_type == 'application/json':
                data = json.loads(request.body.decode('utf-8'))
            else:
                test_data_raw = request.POST.get('test_data', '{}')
                data = json.loads(test_data_raw)
            
            # Validate transaction data
            transaction_data = validate_transaction_data(data)
            
            # Get appropriate rule engine
            engine = RuleEngineFactory.create_engine(company.id, [rule.rule_type])
            
            # Test single rule
            result = engine.test_rule(rule.id, transaction_data)
            
            # Prepare response
            response_data = {
                'success': True,
                'rule_matched': result.rule_matched,
                'split_data': [
                    {
                        'description': line['description'],
                        'account_code': line['account_code'],
                        'amount': str(line['amount'])
                    }
                    for line in result.split_lines
                ],
                'total_allocated': str(result.total_allocated),
                'conditions_met': result.conditions_met,
                'execution_log': str(result.execution_logs[0].id) if result.execution_logs else None
            }
            
            return JsonResponse(response_data)
            
        except FinancialRulesAPIError as e:
            return JsonResponse({
                'success': False,
                'error_message': str(e),
                'error_type': 'validation_error'
            }, status=400)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error_message': 'Invalid JSON data provided',
                'error_type': 'json_error'
            }, status=400)
            
        except Exception as e:
            logger.error(f"Rule test unexpected error: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error_message': 'An unexpected error occurred during rule testing',
                'error_type': 'server_error'
            }, status=500)


@login_required
@require_http_methods(["GET"])
def get_available_rules(request: HttpRequest) -> JsonResponse:
    """
    Get list of available rules for the current company
    
    Returns:
    {
        "success": true,
        "rules": [
            {
                "id": 1,
                "name": "Rodriguez Loan Payments",
                "rule_type": "loan_payment",
                "is_active": true,
                "priority": 1,
                "conditions_count": 2,
                "actions_count": 3
            }
        ]
    }
    """
    try:
        # Get user's active company
        company = get_user_company(request)
        if not company:
            return JsonResponse({
                'success': False,
                'error_message': 'No active company found. Please select a company.',
                'error_type': 'company_error'
            }, status=400)
        
        rules = BaseFinancialRule.objects.filter(
            company=company
        ).order_by('rule_type', 'priority', 'name')
        
        rules_data = []
        for rule in rules:
            rules_data.append({
                'id': rule.id,
                'name': rule.name,
                'rule_type': rule.rule_type,
                'rule_type_display': rule.get_rule_type_display(),
                'is_active': rule.is_active,
                'priority': rule.priority,
                'conditions_count': rule.conditions.count(),
                'actions_count': rule.actions.count(),
                'created_date': rule.created_at.isoformat(),
                'last_used': rule.last_used.isoformat() if rule.last_used else None,
                'usage_count': rule.usage_count
            })
        
        return JsonResponse({
            'success': True,
            'rules': rules_data,
            'total_rules': len(rules_data)
        })
        
    except Exception as e:
        logger.error(f"Get available rules error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error_message': 'Failed to retrieve available rules',
            'error_type': 'server_error'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_rule_execution_logs(request: HttpRequest) -> JsonResponse:
    """
    Get recent rule execution logs for monitoring and debugging
    
    Query parameters:
    - limit: Number of logs to return (default: 50, max: 500)
    - rule_id: Filter by specific rule ID
    - status: Filter by execution status (success/error)
    """
    try:
        # Get user's active company
        company = get_user_company(request)
        if not company:
            return JsonResponse({
                'success': False,
                'error_message': 'No active company found. Please select a company.',
                'error_type': 'company_error'
            }, status=400)
        
        # Parse query parameters
        limit = min(int(request.GET.get('limit', 50)), 500)
        rule_id = request.GET.get('rule_id')
        status = request.GET.get('status')
        
        # Build query
        logs = RuleExecutionLog.objects.filter(
            rule__company=company
        ).select_related('rule', 'user').order_by('-executed_at')
        
        if rule_id:
            logs = logs.filter(rule_id=rule_id)
        
        if status:
            logs = logs.filter(success=(status == 'success'))
        
        logs = logs[:limit]
        
        # Prepare response
        logs_data = []
        for log in logs:
            logs_data.append({
                'id': str(log.id),
                'rule_name': log.rule.name,
                'rule_id': log.rule.id,
                'user': log.user.username if log.user else 'System',
                'success': log.success,
                'executed_at': log.executed_at.isoformat(),
                'execution_time_ms': log.execution_time_ms,
                'transaction_data': log.transaction_data,
                'result_data': log.result_data,
                'error_message': log.error_message
            })
        
        return JsonResponse({
            'success': True,
            'logs': logs_data,
            'total_logs': len(logs_data)
        })
        
    except Exception as e:
        logger.error(f"Get execution logs error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error_message': 'Failed to retrieve execution logs',
            'error_type': 'server_error'
        }, status=500)


# Legacy support for existing reconciliation integration
@csrf_exempt
@login_required
def auto_split_transaction(request: HttpRequest) -> JsonResponse:
    """
    Legacy endpoint for auto-splitting transactions
    
    This endpoint provides backward compatibility with existing
    reconciliation system while using the new financial rules engine.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'})
    
    try:
        # Get user's active company
        company = get_user_company(request)
        if not company:
            return JsonResponse({
                'success': False,
                'error': 'No active company found. Please select a company.'
            })
        
        # Parse transaction data from reconciliation system format
        customer_name = request.POST.get('customer_name', '')
        amount_str = request.POST.get('amount', '0')
        description = request.POST.get('description', '')
        
        # Convert to standard format
        transaction_data = {
            'customer_name': customer_name,
            'transaction_amount': amount_str,
            'transaction_description': description
        }
        
        # Validate data
        normalized_data = validate_transaction_data(transaction_data)
        
        # Use loan payment engine as default for legacy compatibility
        engine = RuleEngineFactory.create_engine(company.id, ['loan_payment'])
        
        # Evaluate rules
        result = engine.evaluate_transaction(
            transaction_data=normalized_data,
            rule_types=['loan_payment']
        )
        
        # Format response for reconciliation system compatibility
        split_lines = []
        for line in result.split_lines:
            split_lines.append({
                'description': line['description'],
                'account': line['account_code'],
                'amount': float(line['amount'])
            })
        
        return JsonResponse({
            'success': True,
            'split_lines': split_lines,
            'total_amount': float(result.total_allocated)
        })
        
    except FinancialRulesAPIError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
        
    except Exception as e:
        logger.error(f"Auto split transaction error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to auto-split transaction'
        })


# ===================== WEB INTERFACE VIEWS =====================

class RuleListView(LoginRequiredMixin, ListView):
    """List view for financial rules with filtering"""
    model = BaseFinancialRule
    template_name = 'financial_rules/rule_list.html'
    context_object_name = 'rules'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = BaseFinancialRule.objects.select_related('company').prefetch_related(
            'conditions', 'actions'
        ).order_by('-is_active', 'priority', 'name')
        
        # Filter by company
        if self.request.GET.get('company'):
            queryset = queryset.filter(company_id=self.request.GET.get('company'))
        
        # Filter by rule type
        if self.request.GET.get('rule_type'):
            queryset = queryset.filter(rule_type=self.request.GET.get('rule_type'))
        
        # Filter by status
        if self.request.GET.get('is_active'):
            is_active = self.request.GET.get('is_active').lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
        
        # Search by name
        if self.request.GET.get('search'):
            from django.db.models import Q
            search_term = self.request.GET.get('search')
            queryset = queryset.filter(
                Q(name__icontains=search_term) | 
                Q(description__icontains=search_term)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['companies'] = Company.objects.all()
        return context


class RuleDetailView(LoginRequiredMixin, DetailView):
    """Detail view for a single financial rule"""
    model = BaseFinancialRule
    template_name = 'financial_rules/rule_detail.html'
    context_object_name = 'rule'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get recent execution logs
        context['recent_logs'] = RuleExecutionLog.objects.filter(
            rule=self.object
        ).order_by('-executed_at')[:10]
        return context


class RuleCreateView(LoginRequiredMixin, CreateView):
    """Create view for financial rules"""
    model = BaseFinancialRule
    template_name = 'financial_rules/rule_form.html'
    fields = ['name', 'description', 'company', 'rule_type', 'priority', 'is_active', 'condition_logic']
    success_url = reverse_lazy('financial_rules:rule_list')
    
    def form_valid(self, form):
        from django.contrib import messages
        messages.success(self.request, f'Rule "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class RuleUpdateView(LoginRequiredMixin, UpdateView):
    """Update view for financial rules"""
    model = BaseFinancialRule
    template_name = 'financial_rules/rule_form.html'
    fields = ['name', 'description', 'company', 'rule_type', 'priority', 'is_active', 'condition_logic']
    
    def get_success_url(self):
        return reverse_lazy('financial_rules:rule_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        from django.contrib import messages
        messages.success(self.request, f'Rule "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class RuleDeleteView(LoginRequiredMixin, DeleteView):
    """Delete view for financial rules"""
    model = BaseFinancialRule
    template_name = 'financial_rules/rule_confirm_delete.html'
    success_url = reverse_lazy('financial_rules:rule_list')
    
    def delete(self, request, *args, **kwargs):
        from django.contrib import messages
        rule_name = self.get_object().name
        result = super().delete(request, *args, **kwargs)
        messages.success(request, f'Rule "{rule_name}" deleted successfully!')
        return result


class TestRulesView(LoginRequiredMixin, TemplateView):
    """Test rules interface"""
    template_name = 'financial_rules/test_rules.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['companies'] = Company.objects.all()
        context['active_rules'] = BaseFinancialRule.objects.filter(
            is_active=True
        ).select_related('company').order_by('priority')[:10]
        context['today'] = datetime.now().strftime('%Y-%m-%d')
        return context


# ===================== ADDITIONAL API ENDPOINTS =====================

@login_required
@require_http_methods(["POST"])
def evaluate_rules(request):
    """
    Evaluate rules for a transaction (used by test interface)
    """
    try:
        data = json.loads(request.body)
        
        # Get company
        company_id = data.get('company')
        if not company_id:
            return JsonResponse({
                'success': False,
                'error': 'Company is required'
            })
        
        company = get_object_or_404(Company, id=company_id)
        
        # Prepare transaction data
        transaction_data = {
            'amount': Decimal(str(data.get('amount', 0))),
            'description': data.get('description', ''),
            'contact': data.get('contact', ''),
            'reference': data.get('reference', ''),
            'transaction_date': data.get('transaction_date', datetime.now().strftime('%Y-%m-%d'))
        }
        
        # Get rule types to test
        rule_types = []
        if data.get('rule_type'):
            rule_types = [data.get('rule_type')]
        
        # Create engine
        engine = RuleEngineFactory.create_engine(company.id, rule_types or None)
        
        # Evaluate rules
        result = engine.evaluate_transaction(
            transaction_data=transaction_data,
            rule_types=rule_types or None
        )
        
        # Format response
        return JsonResponse({
            'success': True,
            'data': result.split_lines,
            'debug': result.debug_info if data.get('debug_mode') else None
        })
        
    except Exception as e:
        logger.error(f"Error evaluating rules: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["POST"])
def test_rule(request, rule_id):
    """
    Test a specific rule with transaction data
    """
    try:
        rule = get_object_or_404(BaseFinancialRule, id=rule_id)
        data = json.loads(request.body)
        
        # Prepare transaction data
        transaction_data = {
            'amount': Decimal(str(data.get('amount', 0))),
            'description': data.get('description', ''),
            'contact': data.get('contact', ''),
            'reference': data.get('reference', '')
        }
        
        # Create engine for this rule's company
        engine = RuleEngineFactory.create_engine(rule.company.id, [rule.rule_type])
        
        # Test the specific rule
        matches = engine._check_rule_conditions(rule, transaction_data)
        
        if matches:
            result = engine._apply_rule_actions(rule, transaction_data)
            return JsonResponse({
                'success': True,
                'data': result.split_lines
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Rule conditions not met for this transaction'
            })
            
    except Exception as e:
        logger.error(f"Error testing rule {rule_id}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["POST"])
def toggle_rule_status(request, rule_id):
    """
    Toggle the active status of a rule
    """
    try:
        rule = get_object_or_404(BaseFinancialRule, id=rule_id)
        rule.is_active = not rule.is_active
        rule.save()
        
        return JsonResponse({
            'success': True,
            'is_active': rule.is_active
        })
        
    except Exception as e:
        logger.error(f"Error toggling rule {rule_id}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
