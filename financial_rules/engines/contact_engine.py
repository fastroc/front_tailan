"""
Contact Rule Engine

Specialized rule engine for customer name pattern matching and account assignments.
Extends the base rule engine to provide contact-based transaction processing.
"""

import re
from typing import Dict, Any, List
from decimal import Decimal
from ..models import BaseFinancialRule
from .base_engine import BaseRuleEngine, RuleEngineResult
import logging

logger = logging.getLogger(__name__)


class ContactRuleEngine(BaseRuleEngine):
    """
    Specialized rule engine for contact-based transaction rules.
    
    Handles customer name matching, contact pattern recognition,
    and automatic account assignments based on customer relationships.
    """
    
    def __init__(self, company_id: int):
        super().__init__(company_id)
        self.contact_patterns = {}
        self.customer_cache = {}
        
    def evaluate_transaction(self, transaction_data: Dict[str, Any], 
                           rule_types: List[str] = None) -> RuleEngineResult:
        """
        Enhanced transaction evaluation with contact pattern matching
        """
        # Pre-process customer data for better matching
        enhanced_data = self._enhance_customer_data(transaction_data)
        
        # Use base engine evaluation with enhanced data
        return super().evaluate_transaction(enhanced_data, rule_types or ['contact_based'])
    
    def _enhance_customer_data(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance transaction data with normalized customer information
        """
        customer_name = transaction_data.get('customer_name', '').strip()
        
        # Make a copy to avoid modifying original data
        enhanced_data = transaction_data.copy()
        
        # Normalize customer name for better matching
        normalized_name = self._normalize_customer_name(customer_name)
        enhanced_data['normalized_customer_name'] = normalized_name
        
        # Extract name components
        name_parts = self._parse_customer_name(customer_name)
        enhanced_data.update(name_parts)
        
        # Look up customer in cache/database
        customer_info = self._lookup_customer(customer_name)
        if customer_info:
            enhanced_data['customer_id'] = customer_info.get('id')
            enhanced_data['customer_type'] = customer_info.get('type', 'individual')
            enhanced_data['customer_status'] = customer_info.get('status', 'active')
        
        self.log_debug(f"Enhanced customer data: {enhanced_data}")
        return enhanced_data
    
    def _normalize_customer_name(self, customer_name: str) -> str:
        """
        Normalize customer name for consistent matching
        
        Args:
            customer_name: Raw customer name from transaction
            
        Returns:
            Normalized customer name
        """
        if not customer_name:
            return ''
        
        # Convert to lowercase and strip
        normalized = customer_name.lower().strip()
        
        # Remove common business suffixes
        business_suffixes = [
            r'\s+(inc|ltd|llc|corp|corporation|company|co)\s*\.?\s*$',
            r'\s+(pty|limited)\s*\.?\s*$'
        ]
        
        for suffix_pattern in business_suffixes:
            normalized = re.sub(suffix_pattern, '', normalized, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Handle special characters
        normalized = re.sub(r'[^\w\s-]', '', normalized)
        
        return normalized
    
    def _parse_customer_name(self, customer_name: str) -> Dict[str, str]:
        """
        Parse customer name into components
        
        Args:
            customer_name: Customer name to parse
            
        Returns:
            Dictionary with name components
        """
        result = {
            'first_name': '',
            'last_name': '',
            'middle_name': '',
            'name_suffix': '',
            'is_business': False
        }
        
        if not customer_name:
            return result
        
        # Check if it looks like a business name
        business_indicators = [
            'inc', 'ltd', 'llc', 'corp', 'corporation', 'company', 'co',
            'pty', 'limited', 'enterprises', 'group', 'holdings'
        ]
        
        customer_lower = customer_name.lower()
        result['is_business'] = any(indicator in customer_lower for indicator in business_indicators)
        
        if result['is_business']:
            # For businesses, use the full name as last_name
            result['last_name'] = customer_name.strip()
            return result
        
        # Parse individual name
        # Handle "Last, First" format
        if ',' in customer_name:
            parts = customer_name.split(',', 1)
            if len(parts) == 2:
                result['last_name'] = parts[0].strip()
                first_part = parts[1].strip()
                
                # Check for middle name/initial in first part
                first_names = first_part.split()
                if first_names:
                    result['first_name'] = first_names[0]
                    if len(first_names) > 1:
                        result['middle_name'] = ' '.join(first_names[1:])
                
                return result
        
        # Handle "First Last" or "First Middle Last" format
        name_parts = customer_name.strip().split()
        if len(name_parts) == 1:
            result['last_name'] = name_parts[0]
        elif len(name_parts) == 2:
            result['first_name'] = name_parts[0]
            result['last_name'] = name_parts[1]
        elif len(name_parts) >= 3:
            result['first_name'] = name_parts[0]
            result['last_name'] = name_parts[-1]
            result['middle_name'] = ' '.join(name_parts[1:-1])
        
        return result
    
    def _lookup_customer(self, customer_name: str) -> Dict[str, Any]:
        """
        Look up customer in the database for additional context
        
        Args:
            customer_name: Customer name to look up
            
        Returns:
            Customer information dictionary or None if not found
        """
        # Check cache first
        if customer_name in self.customer_cache:
            return self.customer_cache[customer_name]
        
        try:
            # Try to find customer in loans_customers
            from loans_customers.models import Customer
            from django.db.models import Q
            
            # Parse name for database lookup
            name_parts = self._parse_customer_name(customer_name)
            
            if name_parts['is_business']:
                # For business, try to match by last_name (which contains full business name)
                customers = Customer.objects.filter(
                    company_id=self.company_id,
                    last_name__icontains=name_parts['last_name']
                )
            else:
                # For individuals, try exact and fuzzy matching
                customers = Customer.objects.filter(
                    company_id=self.company_id
                ).filter(
                    Q(first_name__iexact=name_parts['first_name'],
                      last_name__iexact=name_parts['last_name']) |
                    Q(first_name__icontains=name_parts['first_name']) |
                    Q(last_name__icontains=name_parts['last_name'])
                )
            
            if customers.exists():
                customer = customers.first()
                customer_info = {
                    'id': customer.id,
                    'type': 'business' if name_parts['is_business'] else 'individual',
                    'status': 'active',  # Default, could be enhanced
                    'email': getattr(customer, 'email', ''),
                    'customer_id': getattr(customer, 'customer_id', '')
                }
                
                # Cache the result
                self.customer_cache[customer_name] = customer_info
                self.log_debug(f"Found customer: {customer_info}")
                return customer_info
            
        except Exception as e:
            logger.warning(f"Customer lookup error: {e}")
        
        # Not found
        self.customer_cache[customer_name] = None
        return None
    
    def create_contact_rule(self, customer_pattern: str, account_mappings: List[Dict[str, Any]],
                          rule_name: str = None, priority: int = 5) -> BaseFinancialRule:
        """
        Create a new contact-based rule
        
        Args:
            customer_pattern: Pattern to match customer names (regex or contains)
            account_mappings: List of account allocations
            rule_name: Optional rule name
            priority: Rule priority (lower = higher priority)
            
        Returns:
            Created BaseFinancialRule instance
        """
        from ..models import RuleCondition, RuleAction
        
        # Generate rule name if not provided
        if not rule_name:
            rule_name = f"Contact Rule: {customer_pattern}"
        
        # Create the rule
        rule = BaseFinancialRule.objects.create(
            company_id=self.company_id,
            name=rule_name,
            rule_type='contact_based',
            description=f'Auto-generated contact rule for pattern: {customer_pattern}',
            priority=priority,
            is_active=True
        )
        
        # Add customer pattern condition
        RuleCondition.objects.create(
            rule=rule,
            field_name='customer_name',
            operator='contains',
            value=customer_pattern,
            sequence=1
        )
        
        # Add account mapping actions
        for i, mapping in enumerate(account_mappings, 1):
            RuleAction.objects.create(
                rule=rule,
                description_template=mapping.get('description', f'Allocation {i}'),
                account_code=mapping['account_code'],
                allocation_type=mapping.get('allocation_type', 'percentage'),
                value=Decimal(str(mapping.get('value', 100))),
                sequence=i
            )
        
        self.log_debug(f"Created contact rule: {rule.name}")
        return rule
    
    def test_contact_patterns(self, test_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Test contact name patterns for debugging
        
        Args:
            test_names: List of customer names to test
            
        Returns:
            Dictionary mapping names to their parsed components
        """
        results = {}
        
        for name in test_names:
            results[name] = {
                'normalized': self._normalize_customer_name(name),
                'parsed': self._parse_customer_name(name),
                'lookup': self._lookup_customer(name)
            }
        
        return results


def create_contact_engine(company_id: int) -> ContactRuleEngine:
    """
    Factory function to create a ContactRuleEngine instance
    
    Args:
        company_id: Company ID for the rule engine
        
    Returns:
        Configured ContactRuleEngine instance
    """
    engine = ContactRuleEngine(company_id)
    
    # Enable debug mode in development
    from django.conf import settings
    if getattr(settings, 'DEBUG', False):
        engine.enable_debug()
    
    return engine
