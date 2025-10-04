"""
Bank Rules Engine Service
--------------------------
Core matching logic for rule-based transaction suggestions.

Safety: Completely separate from reconciliation logic.
Can be disabled without breaking the reconciliation system.
"""

from decimal import Decimal
from datetime import datetime
from django.utils import timezone


class RuleEngineService:
    """
    Rule matching engine - completely modular and safe.
    
    Main Entry Point:
        get_suggestions_from_rules(transaction, company)
        
    Returns suggestions in same format as SmartSuggestionService
    so they integrate seamlessly into the reconciliation UI.
    """
    
    @staticmethod
    def get_suggestions_from_rules(transaction, company):
        """
        Main entry point: Check transaction against all active rules.
        
        Args:
            transaction: Dict with transaction fields (description, amount, etc.)
            company: Company instance
            
        Returns:
            list: Suggestions in smart suggestion format
        """
        try:
            from .models import BankRule
            
            suggestions = []
            
            # Get active rules for this company, ordered by priority
            rules = BankRule.objects.filter(
                company=company,
                is_active=True
            ).prefetch_related('conditions').order_by('-priority', 'id')
            
            for rule in rules:
                if RuleEngineService._rule_matches(transaction, rule):
                    # Create suggestion from this rule
                    suggestion = RuleEngineService._create_suggestion_from_rule(
                        transaction, 
                        rule
                    )
                    suggestions.append(suggestion)
                    
                    # Update statistics
                    rule.increment_match_count()
                    
                    # Stop after first match (highest priority wins)
                    # Remove this break to show all matching rules
                    break
            
            return suggestions
            
        except Exception as e:
            # Fail gracefully - don't break reconciliation if rules break
            print(f"⚠️ Bank Rules Engine Error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    @staticmethod
    def _rule_matches(transaction, rule):
        """
        Check if transaction matches rule's conditions.
        
        Args:
            transaction: Transaction dict
            rule: BankRule instance with conditions
            
        Returns:
            bool: True if transaction matches rule
        """
        conditions = rule.conditions.all()
        
        if not conditions:
            return False  # No conditions = no match
        
        if rule.match_logic == 'ALL':
            # AND logic - all conditions must match
            return all(
                RuleEngineService._condition_matches(transaction, cond)
                for cond in conditions
            )
        else:
            # OR logic - any condition can match
            return any(
                RuleEngineService._condition_matches(transaction, cond)
                for cond in conditions
            )
    
    @staticmethod
    def _condition_matches(transaction, condition):
        """
        Check if single condition matches transaction.
        
        Args:
            transaction: Transaction dict
            condition: BankRuleCondition instance
            
        Returns:
            bool: True if condition matches
        """
        # Get field value from transaction
        field_value = RuleEngineService._get_field_value(transaction, condition.field)
        
        # Handle blank/empty checks
        if field_value is None or field_value == '':
            if condition.operator == 'is_blank':
                return True
            elif condition.operator == 'is_not_blank':
                return False
            else:
                return False  # Can't compare None/empty
        
        # Apply operator
        return RuleEngineService._apply_operator(
            field_value,
            condition.operator,
            condition.value,
            condition.value_secondary,
            condition.case_sensitive
        )
    
    @staticmethod
    def _get_field_value(transaction, field):
        """
        Extract field value from transaction.
        
        Args:
            transaction: Transaction dict or object
            field: Field name (string)
            
        Returns:
            Field value (string, number, date, etc.)
        """
        # Handle both dict and object access
        def safe_get(obj, key, default=''):
            if isinstance(obj, dict):
                return obj.get(key, default)
            else:
                return getattr(obj, key, default)
        
        if field == 'description':
            return safe_get(transaction, 'description', '')
        
        elif field == 'amount':
            amount = safe_get(transaction, 'amount', 0)
            return float(amount) if amount else 0
        
        elif field == 'amount_abs':
            amount = safe_get(transaction, 'amount', 0)
            return abs(float(amount)) if amount else 0
        
        elif field == 'debit_credit':
            # Return 'debit' or 'credit' based on amount sign
            # In banking: negative amount = money OUT = debit, positive = money IN = credit
            amount = safe_get(transaction, 'amount', 0)
            amount_float = float(amount) if amount else 0
            return 'debit' if amount_float < 0 else 'credit'
        
        elif field == 'correspondent_account':
            return safe_get(transaction, 'correspondent_account', '')
        
        elif field == 'date':
            return safe_get(transaction, 'transaction_date', None)
        
        elif field == 'reference':
            return safe_get(transaction, 'reference_number', '')
        
        return None
    
    @staticmethod
    def _apply_operator(field_value, operator, value, value_secondary, case_sensitive):
        """
        Apply comparison operator to field value and condition value.
        
        Args:
            field_value: Value from transaction
            operator: Comparison operator (equals, contains, etc.)
            value: Value to compare against
            value_secondary: Secondary value (for 'between')
            case_sensitive: Whether to match case exactly
            
        Returns:
            bool: True if comparison passes
        """
        
        # TEXT OPERATORS
        if operator in ['equals', 'not_equals', 'contains', 'not_contains', 
                       'starts_with', 'ends_with']:
            
            # Convert to string and handle case
            field_str = str(field_value)
            value_str = str(value)
            
            if not case_sensitive:
                field_str = field_str.lower()
                value_str = value_str.lower()
            
            if operator == 'equals':
                return field_str == value_str
            
            elif operator == 'not_equals':
                return field_str != value_str
            
            elif operator == 'contains':
                return value_str in field_str
            
            elif operator == 'not_contains':
                return value_str not in field_str
            
            elif operator == 'starts_with':
                return field_str.startswith(value_str)
            
            elif operator == 'ends_with':
                return field_str.endswith(value_str)
        
        # BLANK CHECKS
        elif operator == 'is_blank':
            return not bool(field_value)
        
        elif operator == 'is_not_blank':
            return bool(field_value)
        
        # NUMERIC OPERATORS
        elif operator in ['greater_than', 'less_than', 'greater_equal', 
                         'less_equal', 'between']:
            try:
                field_num = float(field_value)
                value_num = float(value)
                
                if operator == 'greater_than':
                    return field_num > value_num
                
                elif operator == 'less_than':
                    return field_num < value_num
                
                elif operator == 'greater_equal':
                    return field_num >= value_num
                
                elif operator == 'less_equal':
                    return field_num <= value_num
                
                elif operator == 'between':
                    if value_secondary:
                        value_secondary_num = float(value_secondary)
                        return value_num <= field_num <= value_secondary_num
                    else:
                        return False  # Between requires secondary value
                        
            except (ValueError, TypeError):
                return False  # Can't convert to number
        
        return False
    
    @staticmethod
    def _create_suggestion_from_rule(transaction, rule):
        """
        Create suggestion dict from matched rule.
        
        Format matches SmartSuggestionService output so it integrates
        seamlessly into the reconciliation UI.
        
        Args:
            transaction: Transaction that matched
            rule: BankRule that matched
            
        Returns:
            dict: Suggestion in smart suggestion format
        """
        # Get matched conditions details
        conditions = rule.conditions.all()
        matched_conditions = []
        for cond in conditions:
            if RuleEngineService._condition_matches(transaction, cond):
                field_value = RuleEngineService._get_field_value(transaction, cond.field)
                matched_conditions.append({
                    'field': cond.get_field_display(),
                    'operator': cond.get_operator_display(),
                    'value': cond.value,
                    'matched_value': str(field_value)[:50] if field_value else ''
                })
        
        # Create readable match description
        if len(matched_conditions) == 1:
            mc = matched_conditions[0]
            match_desc = f"{mc['field']} {mc['operator']} '{mc['value']}'"
        elif len(matched_conditions) > 1:
            match_desc = f"{len(matched_conditions)} conditions matched"
        else:
            match_desc = "Rule conditions satisfied"
        
        # Base suggestion structure
        suggestion = {
            'source': 'bank_rule',
            'rule_id': rule.id,
            'rule_name': rule.name,
            'engine_display_name': '🎯 Bank Rule',
            'match_percentage': 90,  # Rules get high confidence
            'match_reason': f'Rule "{rule.name}" matched',
            'matched_data': match_desc,
            'matched_conditions': matched_conditions,  # For detailed display
        }
        
        # Add WHO suggestion (free text - universal correspondent)
        if rule.suggested_who_text:
            suggestion.update({
                'loan_id': None,
                'customer_name': rule.suggested_who_text,
                'suggested_who_text': rule.suggested_who_text,  # Add this field for template
                'loan_number': '',
                'loan_amount': 0,
                'loan_type': '',
            })
        else:
            suggestion.update({
                'loan_id': None,
                'customer_name': '',
                'suggested_who_text': '',  # Add this field for template
                'loan_number': '',
                'loan_amount': 0,
                'loan_type': '',
            })
        
        # Add WHAT suggestion (COA - Chart of Account)
        if rule.suggested_coa:
            suggestion['suggested_coa'] = {
                'account_id': rule.suggested_coa.id,
                'account_code': rule.suggested_coa.code,
                'account_name': rule.suggested_coa.name,
                'account_display': f"{rule.suggested_coa.code} - {rule.suggested_coa.name}"
            }
            suggestion['coa_reason'] = f'Rule: {rule.name}'
        else:
            # Return empty dict instead of None to prevent .get() errors
            suggestion['suggested_coa'] = {
                'account_id': None,
                'account_code': '',
                'account_name': '',
                'account_display': ''
            }
            suggestion['coa_reason'] = ''
        
        return suggestion
