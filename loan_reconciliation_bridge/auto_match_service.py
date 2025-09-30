"""
Auto-Match Service for Loan Bridge

Provides automatic matching capabilities for loan-related transactions
based on predefined patterns and GL account configurations.
"""

import re
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from django.db.models import Q

from .models import LoanGLConfiguration
from bank_accounts.models import BankTransaction
from coa.models import Account


class LoanAutoMatchService:
    """Service for automatic loan transaction matching"""
    
    def __init__(self, company):
        self.company = company
        self.gl_config = self._get_gl_configuration()
        
        # Loan disbursement patterns (Mongolian and English)
        self.disbursement_patterns = [
            r'EB-.*зээл олгов',                    # Mongolian: "EB-...loan granted"
            r'EB-.*loan disbursement',             # English
            r'EB-.*д зээл олгов',                  # "granted loan to..."
            r'EB-\d+',                           # EB-200000000371 format
            r'.*зээл олгов.*',                    # General loan disbursement
            r'.*loan granted.*',                  # English equivalent
            r'.*disbursement.*',                  # General disbursement
        ]
        
        # Loan payment patterns
        self.payment_patterns = [
            r'.*loan payment.*',
            r'.*зээлийн төлбөр.*',                # Mongolian: loan payment
            r'.*payment.*loan.*',
            r'.*monthly payment.*',
            r'.*installment.*',
        ]
    
    def _get_gl_configuration(self) -> Optional[LoanGLConfiguration]:
        """Get GL configuration for the company"""
        try:
            return LoanGLConfiguration.objects.get(company=self.company)
        except LoanGLConfiguration.DoesNotExist:
            return None
    
    def can_auto_match(self) -> bool:
        """Check if auto-matching is available for this company"""
        return (self.gl_config and 
                self.gl_config.general_loan_disbursements_account and
                self.gl_config.general_loans_receivable_account)
    
    def detect_loan_disbursement(self, transaction: BankTransaction) -> Optional[Dict]:
        """
        Detect if transaction is a loan disbursement
        
        Returns:
            Dict with match info if detected, None otherwise
        """
        if not self.can_auto_match():
            return None
        
        description = transaction.description.lower()
        
        # Check against disbursement patterns
        for pattern in self.disbursement_patterns:
            if re.search(pattern, description, re.IGNORECASE | re.UNICODE):
                return {
                    'transaction_id': transaction.id,
                    'suggested_account': self.gl_config.general_loan_disbursements_account,
                    'confidence': self._calculate_disbursement_confidence(description, pattern),
                    'match_reason': f'Loan disbursement pattern: {pattern}',
                    'match_type': 'loan_disbursement',
                    'auto_match': True
                }
        
        return None
    
    def detect_loan_payment(self, transaction: BankTransaction) -> Optional[Dict]:
        """
        Detect if transaction is a loan payment
        
        Returns:
            Dict with match info if detected, None otherwise
        """
        if not self.can_auto_match():
            return None
        
        description = transaction.description.lower()
        
        # Check against payment patterns
        for pattern in self.payment_patterns:
            if re.search(pattern, description, re.IGNORECASE | re.UNICODE):
                return {
                    'transaction_id': transaction.id,
                    'suggested_account': self.gl_config.general_loans_receivable_account,
                    'confidence': self._calculate_payment_confidence(description, pattern),
                    'match_reason': f'Loan payment pattern: {pattern}',
                    'match_type': 'loan_payment',
                    'auto_match': True
                }
        
        return None
    
    def auto_match_transaction(self, transaction: BankTransaction) -> Optional[Dict]:
        """
        Attempt to auto-match a transaction to the appropriate GL account
        
        Returns:
            Dict with match result if successful, None otherwise
        """
        # Try loan disbursement first (more specific)
        disbursement_match = self.detect_loan_disbursement(transaction)
        if disbursement_match and disbursement_match['confidence'] >= 80:
            return disbursement_match
        
        # Try loan payment
        payment_match = self.detect_loan_payment(transaction)
        if payment_match and payment_match['confidence'] >= 70:
            return payment_match
        
        return None
    
    def bulk_auto_match(self, transactions: List[BankTransaction]) -> Dict[str, List]:
        """
        Auto-match multiple transactions
        
        Returns:
            Dict with 'matched', 'failed', 'suggestions' lists
        """
        results = {
            'matched': [],
            'failed': [],
            'suggestions': []
        }
        
        for transaction in transactions:
            match_result = self.auto_match_transaction(transaction)
            
            if match_result:
                if match_result['confidence'] >= 90:
                    # High confidence - auto-match
                    results['matched'].append(match_result)
                else:
                    # Medium confidence - suggest
                    results['suggestions'].append(match_result)
            else:
                results['failed'].append({
                    'transaction_id': transaction.id,
                    'reason': 'No matching patterns found'
                })
        
        return results
    
    def get_disbursement_suggestions(self, description: str, amount: Decimal) -> List[Dict]:
        """
        Get loan disbursement suggestions for a given description and amount
        
        Returns:
            List of suggestion dictionaries
        """
        suggestions = []
        
        if not self.can_auto_match():
            return suggestions
        
        description_lower = description.lower()
        
        # Check each disbursement pattern
        for pattern in self.disbursement_patterns:
            if re.search(pattern, description_lower, re.IGNORECASE | re.UNICODE):
                confidence = self._calculate_disbursement_confidence(description_lower, pattern)
                
                suggestions.append({
                    'account': self.gl_config.general_loan_disbursements_account,
                    'account_code': self.gl_config.general_loan_disbursements_account.code,
                    'account_name': self.gl_config.general_loan_disbursements_account.name,
                    'confidence': confidence,
                    'pattern_matched': pattern,
                    'reason': f'Matches loan disbursement pattern: {pattern}',
                    'suggested_description': f'Loan disbursement - {description}',
                    'auto_match_available': confidence >= 80
                })
                break  # Only return first match
        
        return suggestions
    
    def _calculate_disbursement_confidence(self, description: str, pattern: str) -> int:
        """Calculate confidence score for loan disbursement detection"""
        base_confidence = 70
        
        # Higher confidence for specific patterns
        if 'EB-' in description and 'зээл олгов' in description:
            base_confidence = 95
        elif 'EB-' in description:
            base_confidence = 85
        elif 'зээл олгов' in description:
            base_confidence = 80
        elif 'loan disbursement' in description:
            base_confidence = 80
        
        # Boost confidence for pattern specificity
        if r'EB-.*д зээл олгов' in pattern:
            base_confidence += 10
        elif r'EB-\d+' in pattern:
            base_confidence += 5
        
        return min(base_confidence, 99)  # Cap at 99%
    
    def _calculate_payment_confidence(self, description: str, pattern: str) -> int:
        """Calculate confidence score for loan payment detection"""
        base_confidence = 60
        
        # Higher confidence for specific indicators
        if 'loan payment' in description:
            base_confidence = 75
        elif 'зээлийн төлбөр' in description:
            base_confidence = 75
        elif 'monthly payment' in description:
            base_confidence = 70
        elif 'installment' in description:
            base_confidence = 70
        
        return min(base_confidence, 85)  # Cap at 85% for payments
    
    def get_configuration_status(self) -> Dict:
        """Get current auto-match configuration status"""
        return {
            'auto_match_available': self.can_auto_match(),
            'gl_config_exists': self.gl_config is not None,
            'disbursement_account_configured': (
                self.gl_config and 
                self.gl_config.general_loan_disbursements_account is not None
            ),
            'receivable_account_configured': (
                self.gl_config and 
                self.gl_config.general_loans_receivable_account is not None
            ),
            'disbursement_account': (
                self.gl_config.general_loan_disbursements_account.name 
                if self.gl_config and self.gl_config.general_loan_disbursements_account 
                else None
            ),
            'receivable_account': (
                self.gl_config.general_loans_receivable_account.name 
                if self.gl_config and self.gl_config.general_loans_receivable_account 
                else None
            )
        }
