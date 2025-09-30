"""
Loan Disbursement Engine

Smart matching engine for detecting loan disbursement transactions by patterns and GL codes.
Integrates with LoanAutoMatchService for automatic GL account matching.
"""

import re
from typing import List, Dict
from ..base_engine import SmartMatchingEngine


class LoanDisbursementEngine(SmartMatchingEngine):
    """Detects loan disbursement transactions by GL code patterns"""
    
    def __init__(self):
        super().__init__()
        self.engine_name = "Loan Disbursement Engine"
        self.version = "1.0.0"
        
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
        
        # GL codes typically used for loan disbursements
        self.disbursement_gl_codes = ['1250', '1200', '122000']
    
    def detect_loans(self, bank_description: str, amount: float) -> List[Dict]:
        """Detect loan disbursements and suggest GL account matching"""
        suggestions = []
        
        # Check if description matches disbursement patterns
        matched_patterns = self._match_disbursement_patterns(bank_description)
        
        if not matched_patterns:
            return suggestions
        
        try:
            # Get GL configuration for auto-matching
            gl_suggestion = self._get_gl_account_suggestion(bank_description, amount)
            
            if gl_suggestion:
                suggestion = {
                    'loan_id': None,  # Not tied to specific loan
                    'loan_number': 'N/A',
                    'customer_id': None,
                    'customer_name': self._extract_customer_name(bank_description),
                    'confidence': self._calculate_confidence(bank_description, matched_patterns),
                    'method': 'loan_disbursement_pattern',
                    'matched_data': matched_patterns[0],  # First matching pattern
                    'loan_amount': float(amount),
                    'loan_type': 'disbursement',
                    'reason': f"Loan disbursement pattern: {matched_patterns[0]}",
                    'gl_account_suggestion': gl_suggestion,
                    'auto_match_available': True,
                    'engine': self.engine_name
                }
                suggestions.append(suggestion)
        
        except Exception as e:
            self._log_error(f"Disbursement detection error: {e}")
            return []
        
        return suggestions
    
    def _match_disbursement_patterns(self, description: str) -> List[str]:
        """Find matching disbursement patterns in description"""
        matches = []
        description_lower = description.lower()
        
        for pattern in self.disbursement_patterns:
            if re.search(pattern, description_lower, re.IGNORECASE | re.UNICODE):
                matches.append(pattern)
        
        return matches
    
    def _get_gl_account_suggestion(self, description: str, amount: float) -> Dict:
        """Get GL account suggestion using LoanAutoMatchService"""
        try:
            # Import here to avoid circular imports
            from loan_reconciliation_bridge.auto_match_service import LoanAutoMatchService
            from company.models import Company
            
            # Get company (assuming first company for now - could be enhanced)
            company = Company.objects.first()
            if not company:
                return None
            
            auto_match_service = LoanAutoMatchService(company)
            
            if auto_match_service.can_auto_match():
                gl_config = auto_match_service._get_gl_configuration()
                
                if gl_config and gl_config.general_loan_disbursements_account:
                    return {
                        'account_id': gl_config.general_loan_disbursements_account.id,
                        'account_code': gl_config.general_loan_disbursements_account.code,
                        'account_name': gl_config.general_loan_disbursements_account.name,
                        'account_type': 'General Loan Disbursements',
                        'auto_match': True
                    }
        
        except Exception as e:
            self._log_error(f"GL account suggestion error: {e}")
        
        return None
    
    def _extract_customer_name(self, description: str) -> str:
        """Extract customer name from disbursement description"""
        # Pattern for "EB-Customer Name-д зээл олгов"
        name_pattern = r'EB-([^-]+)-д зээл олгов'
        match = re.search(name_pattern, description, re.IGNORECASE)
        
        if match:
            return match.group(1).strip()
        
        # Pattern for "EB-Customer Name loan disbursement"
        name_pattern_en = r'EB-([^-]+) loan disbursement'
        match = re.search(name_pattern_en, description, re.IGNORECASE)
        
        if match:
            return match.group(1).strip()
        
        # Fallback: extract any name-like pattern after EB-
        fallback_pattern = r'EB-([А-Яа-яA-Za-z\s\.]+)'
        match = re.search(fallback_pattern, description)
        
        if match:
            name = match.group(1).strip()
            # Clean up the name (remove common suffixes)
            name = re.sub(r'(д|loan|disbursement).*$', '', name, flags=re.IGNORECASE).strip()
            return name
        
        return "Unknown Customer"
    
    def _calculate_confidence(self, description: str, matched_patterns: List[str]) -> int:
        """Calculate confidence score for disbursement detection"""
        base_confidence = 70
        description_lower = description.lower()
        
        # Higher confidence for specific patterns
        if any('EB-' in pattern and 'зээл олгов' in pattern for pattern in matched_patterns):
            if 'EB-' in description and 'зээл олгов' in description:
                base_confidence = 95
        elif 'EB-' in description:
            base_confidence = 85
        elif any('зээл олгов' in pattern for pattern in matched_patterns):
            base_confidence = 80
        elif any('loan disbursement' in pattern for pattern in matched_patterns):
            base_confidence = 80
        
        # Boost for specific customer name patterns
        if re.search(r'EB-[А-Яа-яA-Za-z\s\.]+-д зээл олгов', description):
            base_confidence += 10
        
        # Boost for EB-number patterns
        if re.search(r'EB-\d+', description):
            base_confidence += 5
        
        return min(base_confidence, 99)  # Cap at 99%
    
    def is_disbursement_transaction(self, description: str) -> bool:
        """Quick check if transaction is likely a disbursement"""
        return len(self._match_disbursement_patterns(description)) > 0
    
    def get_pattern_details(self, description: str) -> Dict:
        """Get detailed information about matched patterns"""
        matched = self._match_disbursement_patterns(description)
        customer_name = self._extract_customer_name(description)
        confidence = self._calculate_confidence(description, matched)
        
        return {
            'is_disbursement': len(matched) > 0,
            'matched_patterns': matched,
            'customer_name': customer_name,
            'confidence': confidence,
            'description_analysis': {
                'has_eb_prefix': 'EB-' in description,
                'has_mongolian_pattern': 'зээл олгов' in description.lower(),
                'has_english_pattern': 'loan disbursement' in description.lower(),
                'has_customer_name': customer_name != "Unknown Customer",
                'has_eb_number': bool(re.search(r'EB-\d+', description))
            }
        }
    
    def get_supported_patterns(self) -> List[str]:
        """Get list of supported disbursement patterns"""
        return [
            "EB-CustomerName-д зээл олгов (Mongolian format)",
            "EB-CustomerName loan disbursement (English format)",
            "EB-200000000371 (Transaction code format)",
            "General 'зээл олгов' patterns",
            "General 'loan granted' patterns",
            "General 'disbursement' patterns"
        ]
    
    def get_engine_info(self) -> Dict:
        """Get engine information and capabilities"""
        return {
            'name': self.engine_name,
            'version': self.version,
            'description': 'Detects loan disbursement transactions and suggests GL accounts',
            'supported_patterns': len(self.disbursement_patterns),
            'gl_integration': True,
            'capabilities': [
                'Multi-language pattern support (Mongolian/English)',
                'Customer name extraction',
                'GL account auto-matching',
                'Confidence scoring',
                'Pattern analysis'
            ],
            'confidence_range': '70-99%',
            'independent': True,
            'debuggable': True,
            'removable': True
        }
    
    def _log_error(self, message: str):
        """Log engine-specific errors"""
        print(f"❌ {self.engine_name} Error: {message}")
    
    def _log_info(self, message: str):
        """Log engine-specific information"""
        print(f"ℹ️ {self.engine_name}: {message}")
    
    def run_self_test(self) -> Dict:
        """Run self-test to verify engine functionality"""
        test_cases = [
            "EB-Б.Ням-Очир-д зээл олгов.",
            "EB-200000000371",
            "EB-Г.Батбаасан-д зээл олгов.",
            "EB-Customer loan disbursement",
            "General loan disbursement transaction"
        ]
        
        results = {
            'engine': self.engine_name,
            'test_cases': len(test_cases),
            'patterns_detected': 0,
            'customers_extracted': 0,
            'status': 'unknown'
        }
        
        for test_case in test_cases:
            patterns = self._match_disbursement_patterns(test_case)
            if patterns:
                results['patterns_detected'] += 1
            
            customer = self._extract_customer_name(test_case)
            if customer != "Unknown Customer":
                results['customers_extracted'] += 1
        
        results['pattern_success_rate'] = (results['patterns_detected'] / len(test_cases)) * 100
        results['extraction_success_rate'] = (results['customers_extracted'] / len(test_cases)) * 100
        results['overall_success'] = (results['pattern_success_rate'] + results['extraction_success_rate']) / 2
        results['status'] = 'PASS' if results['overall_success'] >= 70 else 'FAIL'
        
        return results
