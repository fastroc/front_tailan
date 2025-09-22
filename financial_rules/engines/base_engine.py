"""
Base Rule Engine

This module provides the core logic for evaluating financial rules and executing actions.
It serves as the foundation for specialized engines like loan_engine and contact_engine.
"""

from typing import List, Dict, Any
from decimal import Decimal
from ..models import BaseFinancialRule, RuleExecutionLog
import logging

logger = logging.getLogger(__name__)


class RuleEngineResult:
    """
    Container for rule engine execution results.
    """
    def __init__(self, success: bool, matched_rules: List = None, 
                 split_lines: List = None, error_message: str = None,
                 rule_matched: bool = None, conditions_met: bool = None,
                 execution_logs: List = None):
        self.success = success
        self.matched_rules = matched_rules or []
        self.split_lines = split_lines or []  # Changed from split_data to split_lines
        self.error_message = error_message
        self.total_allocated = Decimal('0')
        self.rule_matched = rule_matched if rule_matched is not None else success
        self.conditions_met = conditions_met if conditions_met is not None else success
        self.execution_logs = execution_logs or []
        
        # Calculate total allocated amount
        if self.split_lines:
            self.total_allocated = sum(
                Decimal(str(item.get('amount', 0))) for item in self.split_lines
            )
    
    def to_dict(self):
        """Convert result to dictionary for JSON serialization"""
        return {
            'success': self.success,
            'matched_rules': [rule.name for rule in self.matched_rules],
            'split_lines': self.split_lines,
            'error_message': self.error_message,
            'total_allocated': str(self.total_allocated),
            'rule_matched': self.rule_matched,
            'conditions_met': self.conditions_met,
        }


class BaseRuleEngine:
    """
    Base rule engine that provides core functionality for rule evaluation and execution.
    """
    
    def __init__(self, company_id: int):
        self.company_id = company_id
        self.debug_mode = False
        
    def enable_debug(self):
        """Enable debug logging for rule evaluation"""
        self.debug_mode = True
        
    def log_debug(self, message: str):
        """Log debug message if debug mode is enabled"""
        if self.debug_mode:
            logger.debug(f"[RuleEngine] {message}")
            
    def evaluate_transaction(self, transaction_data: Dict[str, Any], 
                           rule_types: List[str] = None) -> RuleEngineResult:
        """
        Main entry point for evaluating a transaction against rules.
        
        Args:
            transaction_data: Dictionary containing transaction information
            rule_types: Optional list of rule types to consider
            
        Returns:
            RuleEngineResult with matched rules and generated split data
        """
        try:
            self.log_debug(f"Evaluating transaction: {transaction_data}")
            
            # Get applicable rules
            rules = self._get_applicable_rules(rule_types)
            self.log_debug(f"Found {len(rules)} applicable rules")
            
            # Find matching rules
            matched_rules = []
            for rule in rules:
                if self._evaluate_rule_conditions(rule, transaction_data):
                    matched_rules.append(rule)
                    self.log_debug(f"Rule matched: {rule.name}")
                    
                    # Stop if rule says so
                    if rule.stop_on_match:
                        break
            
            if not matched_rules:
                self.log_debug("No rules matched")
                return RuleEngineResult(
                    success=False, 
                    error_message="No matching rules found"
                )
            
            # Execute actions for matched rules
            split_data = []
            for rule in matched_rules:
                rule_splits = self._execute_rule_actions(rule, transaction_data)
                split_data.extend(rule_splits)
                
                # Log execution
                self._log_rule_execution(rule, transaction_data, True, rule_splits)
                
                # Update usage statistics
                rule.increment_usage()
            
            # Validate and adjust split data
            split_data = self._validate_and_adjust_splits(
                split_data, 
                Decimal(str(transaction_data.get('transaction_amount', 0)))
            )
            
            self.log_debug(f"Generated {len(split_data)} split lines")
            
            return RuleEngineResult(
                success=True,
                matched_rules=matched_rules,
                split_lines=split_data
            )
            
        except Exception as e:
            logger.error(f"Rule engine error: {str(e)}")
            return RuleEngineResult(
                success=False,
                error_message=f"Rule engine error: {str(e)}"
            )
    
    def _get_applicable_rules(self, rule_types: List[str] = None) -> List[BaseFinancialRule]:
        """
        Get rules that could potentially apply to this transaction.
        """
        queryset = BaseFinancialRule.objects.filter(
            company_id=self.company_id,
            is_active=True
        ).prefetch_related('conditions', 'actions').order_by('-priority', 'name')
        
        if rule_types:
            queryset = queryset.filter(rule_type__in=rule_types)
            
        return list(queryset)
    
    def _evaluate_rule_conditions(self, rule: BaseFinancialRule, 
                                 transaction_data: Dict[str, Any]) -> bool:
        """
        Evaluate all conditions for a rule. All conditions must be true (AND logic).
        """
        if not rule.conditions.exists():
            self.log_debug(f"Rule {rule.name} has no conditions, auto-matching")
            return True
            
        for condition in rule.conditions.all():
            if not condition.evaluate(transaction_data):
                self.log_debug(f"Condition failed: {condition}")
                return False
                
        return True
    
    def _execute_rule_actions(self, rule: BaseFinancialRule, 
                            transaction_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute all actions for a matched rule to generate split data.
        """
        split_lines = []
        transaction_amount = Decimal(str(transaction_data.get('transaction_amount', 0)))
        
        # Context for template rendering
        context = {
            'customer_name': transaction_data.get('customer_name', ''),
            'transaction_amount': transaction_amount,
            'transaction_description': transaction_data.get('transaction_description', ''),
            'rule_name': rule.name,
        }
        
        # Process actions in sequence order
        actions = rule.actions.all().order_by('sequence')
        remainder_actions = []
        allocated_amount = Decimal('0')
        
        # First pass: process non-remainder actions
        for action in actions:
            if action.allocation_type == 'remainder':
                remainder_actions.append(action)
                continue
                
            amount = action.calculate_amount(transaction_amount, context)
            allocated_amount += amount
            
            split_line = {
                'description': action.render_description(context),
                'account_code': action.account_code,
                'amount': str(amount),
                'tax_treatment': action.tax_treatment,
                'rule_name': rule.name,
                'sequence': action.sequence,
            }
            split_lines.append(split_line)
            self.log_debug(f"Action executed: {split_line}")
        
        # Second pass: process remainder actions
        remainder_amount = transaction_amount - allocated_amount
        if remainder_actions and remainder_amount != 0:
            # Distribute remainder among remainder actions
            remainder_per_action = remainder_amount / len(remainder_actions)
            
            for action in remainder_actions:
                split_line = {
                    'description': action.render_description(context),
                    'account_code': action.account_code,
                    'amount': str(remainder_per_action),
                    'tax_treatment': action.tax_treatment,
                    'rule_name': rule.name,
                    'sequence': action.sequence,
                }
                split_lines.append(split_line)
                self.log_debug(f"Remainder action executed: {split_line}")
        
        return split_lines
    
    def _validate_and_adjust_splits(self, split_data: List[Dict[str, Any]], 
                                  target_amount: Decimal) -> List[Dict[str, Any]]:
        """
        Validate split data and make minor adjustments for rounding errors.
        """
        if not split_data:
            return split_data
            
        # Calculate total
        total_allocated = sum(Decimal(str(item['amount'])) for item in split_data)
        difference = target_amount - total_allocated
        
        self.log_debug(f"Target: {target_amount}, Allocated: {total_allocated}, Difference: {difference}")
        
        # If there's a small difference (rounding error), adjust the largest amount
        if abs(difference) <= Decimal('0.02') and difference != 0:
            # Find the split line with the largest amount
            largest_idx = 0
            largest_amount = Decimal('0')
            
            for i, item in enumerate(split_data):
                amount = Decimal(str(item['amount']))
                if amount > largest_amount:
                    largest_amount = amount
                    largest_idx = i
            
            # Adjust the largest amount
            new_amount = largest_amount + difference
            split_data[largest_idx]['amount'] = str(new_amount)
            self.log_debug(f"Adjusted split line {largest_idx} by {difference}")
        
        return split_data
    
    def _log_rule_execution(self, rule: BaseFinancialRule, transaction_data: Dict[str, Any],
                          matched: bool, result_data: List[Dict[str, Any]]):
        """
        Log rule execution for auditing and debugging.
        """
        try:
            RuleExecutionLog.objects.create(
                rule=rule,
                transaction_data=transaction_data,
                matched=matched,
                actions_executed=len(result_data) if matched else 0,
                result_data=result_data if matched else None
            )
        except Exception as e:
            logger.warning(f"Failed to log rule execution: {str(e)}")
    
    def test_rule(self, rule_id: int, test_data: Dict[str, Any]) -> RuleEngineResult:
        """
        Test a specific rule with test data without logging execution.
        """
        try:
            rule = BaseFinancialRule.objects.get(id=rule_id, company_id=self.company_id)
            
            if self._evaluate_rule_conditions(rule, test_data):
                split_data = self._execute_rule_actions(rule, test_data)
                return RuleEngineResult(
                    success=True,
                    matched_rules=[rule],
                    split_lines=split_data,
                    rule_matched=True,
                    conditions_met=True
                )
            else:
                return RuleEngineResult(
                    success=False,
                    error_message="Rule conditions not met",
                    rule_matched=False,
                    conditions_met=False
                )
                
        except BaseFinancialRule.DoesNotExist:
            return RuleEngineResult(
                success=False,
                error_message="Rule not found"
            )
        except Exception as e:
            return RuleEngineResult(
                success=False,
                error_message=f"Test error: {str(e)}"
            )


class RuleEngineFactory:
    """
    Factory for creating appropriate rule engines based on rule types.
    """
    
    @staticmethod
    def create_engine(company_id: int, rule_types: List[str] = None) -> BaseRuleEngine:
        """
        Create the appropriate rule engine for the given rule types.
        """
        # If no rule types specified, use base engine
        if not rule_types:
            engine = BaseRuleEngine(company_id)
        # If loan payment types are specified, use the loan engine
        elif 'loan_payment' in rule_types:
            from .loan_engine import create_loan_engine
            return create_loan_engine(company_id)
        # If contact types are specified, use the contact engine
        elif 'contact_based' in rule_types:
            from .contact_engine import create_contact_engine
            return create_contact_engine(company_id)
        # Default to base engine
        else:
            engine = BaseRuleEngine(company_id)
        
        # Enable debug mode in development
        from django.conf import settings
        if getattr(settings, 'DEBUG', False):
            engine.enable_debug()
            
        return engine
    
    @staticmethod
    def get_engine(rule_type: str) -> BaseRuleEngine:
        """
        Legacy method for backward compatibility
        """
        # This method doesn't have company_id, so we'll need to handle it differently
        # For now, return a basic engine factory method
        if rule_type == 'loan_payment':
            from .loan_engine import LoanPaymentEngine
            return LoanPaymentEngine(company_id=1)  # Default company
        elif rule_type == 'contact_based':
            from .contact_engine import ContactRuleEngine
            return ContactRuleEngine(company_id=1)  # Default company
        else:
            return BaseRuleEngine(company_id=1)  # Default company
