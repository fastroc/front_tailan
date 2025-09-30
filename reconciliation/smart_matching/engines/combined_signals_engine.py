"""
Combined Signals Engine

Smart matching engine that combines multiple detection methods for comprehensive loan matching.
Uses phone numbers, ID numbers, names, and amounts for intelligent suggestions.
"""

import re
from typing import List, Dict
from ..base_engine import SmartMatchingEngine


class CombinedSignalsEngine(SmartMatchingEngine):
    """Combines multiple detection methods for comprehensive matching"""
    
    def __init__(self):
        super().__init__()
        self.name = "CombinedSignalsEngine"
        self.version = "1.0"
        
    def detect_loans(self, bank_description: str, amount: float) -> List[Dict]:
        """Detect loans using multiple signals combined including license plates"""
        
        all_suggestions = []
        
        # Use multiple detection methods
        phone_results = self._detect_by_phone(bank_description)
        id_results = self._detect_by_id(bank_description)
        license_results = self._detect_by_license_plate(bank_description)  # NEW
        name_results = self._detect_by_name(bank_description)
        amount_results = self._detect_by_amount(amount)
        
        # Combine results with different confidence levels
        for result in phone_results:
            result['confidence'] = 95
            result['method'] = 'combined_phone'
            all_suggestions.append(result)
        
        for result in id_results:
            result['confidence'] = 90  # Increased for enhanced ID detection
            result['method'] = 'combined_id'
            all_suggestions.append(result)
        
        for result in license_results:  # NEW
            result['confidence'] = 85
            result['method'] = 'combined_license_plate'
            all_suggestions.append(result)
            
        for result in name_results:
            result['confidence'] = 70
            result['method'] = 'combined_name'
            all_suggestions.append(result)
            
        for result in amount_results:
            result['confidence'] = 60
            result['method'] = 'combined_amount'
            all_suggestions.append(result)
        
        # Remove duplicates and boost confidence for multiple matches
        unique_suggestions = self._deduplicate_and_boost(all_suggestions)
        
        return sorted(unique_suggestions, key=lambda x: x['confidence'], reverse=True)
    
    def _detect_by_phone(self, description: str) -> List[Dict]:
        """Detect loans by phone number"""
        phone_pattern = r'\b\d{8}\b'
        phones = re.findall(phone_pattern, description)
        
        suggestions = []
        try:
            from loans_core.models import Loan
            from loans_customers.models import Customer
            
            for phone in phones:
                customers = Customer.objects.filter(phone_primary=phone)
                for customer in customers:
                    active_loans = Loan.objects.filter(customer=customer, status='active').select_related('loan_product')
                    for loan in active_loans:
                        suggestions.append(self._format_suggestion(loan, customer, phone, 'phone_match'))
        except Exception as e:
            print(f"❌ Combined phone detection error: {e}")
        
        return suggestions
    
    def _detect_by_id(self, description: str) -> List[Dict]:
        """Detect loans by ID number with enhanced script handling"""
        # Enhanced ID patterns to handle Cyrillic/Latin script mixing
        id_patterns = [
            # Traditional Cyrillic patterns
            r'[ЧЦ][ЛЪ](\d{8})',           # ЧЛ74090619, ЦЪ12345678
            r'[ТT][ЗZ](\d{8})',           # ТЗ71080171, TZ71080171 (mixed)
            r'[УУӨ][Т](\d{8})',           # УТ12345678, ӨТ12345678
            
            # Latin equivalents often used
            r'[TТ][ZЗ](\d{8})',           # TZ71080171, ТZ71080171 (mixed)
            r'[CcЧ][LlЛ](\d{8})',         # CL74090619, Cl74090619, ЧL74090619
            r'[UuУӨ][TtТ](\d{8})',        # UT12345678, ut12345678, УT12345678
            
            # Common typing mistakes and variations
            r'[ЧCc][ЛLl](\d{8})',         # Mixed script: Чl74090619, CЛ74090619
            r'[ТT][ЗZ3](\d{8})',          # TZ71080171 with number 3 instead of З
            r'[УY][ТT](\d{8})',           # Sometimes Y used instead of У
        ]
        
        all_matches = []
        for pattern in id_patterns:
            matches = re.findall(pattern, description, re.IGNORECASE | re.UNICODE)
            all_matches.extend(matches)
        
        # Remove duplicates while preserving order
        id_numbers = list(dict.fromkeys(all_matches))
        
        suggestions = []
        try:
            from loans_core.models import Loan
            from loans_customers.models import Customer
            from django.db import models
            
            for id_number in id_numbers:
                # Normalize ID for search
                normalized_id = id_number.replace(' ', '').replace('-', '')
                
                customers = Customer.objects.filter(
                    models.Q(national_id__contains=normalized_id) |
                    models.Q(national_id__endswith=normalized_id) |
                    models.Q(national_id__icontains=id_number)
                ).distinct()
                
                for customer in customers:
                    active_loans = Loan.objects.filter(customer=customer, status='active').select_related('loan_product')
                    for loan in active_loans:
                        suggestions.append(self._format_suggestion(loan, customer, id_number, 'id_match'))
        except Exception as e:
            print(f"❌ Combined ID detection error: {e}")
        
        return suggestions
    
    def _detect_by_license_plate(self, description: str) -> List[Dict]:
        """Detect loans by license plate number"""
        # License plate patterns (common formats + actual database format)
        license_patterns = [
            r'\b[A-Za-zА-Я]{2,3}[-]?\d{3,4}\b',      # ABC-1234, АБВ1234
            r'\b\d{3,4}[A-Za-zА-Я]{2,3}\b',          # 1234ABC, 1234АБВ  
            r'\b[A-Za-zА-Я]{3}\d{3}[A-Za-zА-Я]\b',   # ABC123D
            r'\b\d{2}[A-Za-zА-Я]{2}\d{3}\b',         # 12AB345
            r'\d{2}-\d{2}\s*[А-Я]{3}',               # 25-42 УНГ (actual database format)
            r'\d{4}[А-Я]{3}',                        # 6045УАМ (user input format)
        ]
        
        license_plates = []
        for pattern in license_patterns:
            plates = re.findall(pattern, description, re.IGNORECASE)
            license_plates.extend(plates)
        
        # Remove duplicates
        license_plates = list(set(license_plates))
        
        suggestions = []
        try:
            from loans_core.models import Loan
            from loans_collateral.models import Collateral
            
            for plate in license_plates:
                # Find collateral with flexible license plate matching
                clean_input = plate.replace('-', '').replace(' ', '').strip().upper()
                
                # First try exact match
                collateral_items = Collateral.objects.filter(
                    vehicle_license_plate__iexact=plate.strip()
                ).select_related('loan_application__customer').prefetch_related('loan_application__loan')
                
                # If no exact match, try flexible matching (remove formatting)
                if not collateral_items.exists():
                    all_collateral = Collateral.objects.select_related('loan_application__customer').prefetch_related('loan_application__loan')
                    collateral_items = []
                    for item in all_collateral:
                        if item.vehicle_license_plate:
                            clean_db = item.vehicle_license_plate.replace('-', '').replace(' ', '').upper()
                            if clean_db == clean_input:
                                collateral_items.append(item)
                    
                # Convert back to queryset-like for compatibility
                if isinstance(collateral_items, list):
                    collateral_items = collateral_items
                else:
                    collateral_items = list(collateral_items)
                
                for collateral in collateral_items:
                    try:
                        # Get the loan associated with this collateral
                        loan = collateral.loan_application.loan
                        customer = collateral.loan_application.customer
                        
                        if loan and loan.status == 'active':
                            suggestion = self._format_suggestion(loan, customer, plate, 'license_plate_match')
                            suggestion['vehicle_info'] = f"{collateral.vehicle_make} {collateral.vehicle_model}".strip()
                            suggestions.append(suggestion)
                    except Exception:
                        continue  # Skip if no loan found
        except Exception as e:
            print(f"❌ Combined license plate detection error: {e}")
        
        return suggestions
    
    def _detect_by_name(self, description: str) -> List[Dict]:
        """Detect loans by customer name"""
        # Extract potential names (simple approach)
        words = re.findall(r'\b[A-Za-zА-Яа-яЁё]{3,}\b', description)
        if len(words) < 2:
            return []
        
        suggestions = []
        try:
            from loans_core.models import Loan
            from loans_customers.models import Customer
            from django.db import models
            
            # Try combinations of words as first/last names
            for i in range(len(words) - 1):
                first_name = words[i]
                last_name = words[i + 1]
                
                customers = Customer.objects.filter(
                    models.Q(first_name__icontains=first_name) &
                    models.Q(last_name__icontains=last_name)
                )
                
                for customer in customers:
                    active_loans = Loan.objects.filter(customer=customer, status='active').select_related('loan_product')
                    for loan in active_loans:
                        matched_name = f"{first_name} {last_name}"
                        suggestions.append(self._format_suggestion(loan, customer, matched_name, 'name_match'))
        except Exception as e:
            print(f"❌ Combined name detection error: {e}")
        
        return suggestions
    
    def _detect_by_amount(self, amount: float) -> List[Dict]:
        """Detect loans by typical payment amount (monthly payment)"""
        if amount <= 0:
            return []
        
        suggestions = []
        try:
            from loans_core.models import Loan
            
            # Look for loans where amount matches monthly payment (±10%)
            variance = amount * 0.1
            min_amount = amount - variance
            max_amount = amount + variance
            
            loans = Loan.objects.filter(
                status='active',
                monthly_payment__gte=min_amount,
                monthly_payment__lte=max_amount
            ).select_related('customer', 'loan_product')
            
            for loan in loans:
                customer = loan.customer
                suggestions.append(self._format_suggestion(loan, customer, f"${amount:,.2f}", 'amount_match'))
        except Exception as e:
            print(f"❌ Combined amount detection error: {e}")
        
        return suggestions
    
    def _format_suggestion(self, loan, customer, matched_data: str, method: str) -> Dict:
        """Format suggestion in standard format"""
        return {
            'loan_id': loan.id,
            'loan_number': loan.loan_number,
            'customer_id': customer.id,
            'customer_name': f"{customer.first_name} {customer.last_name}".strip(),
            'confidence': 0,  # Will be set by caller
            'method': method,
            'matched_data': matched_data,
            'loan_amount': float(loan.current_balance),
            'loan_type': loan.loan_product.category,
            'reason': f"{method.replace('_', ' ').title()}: {matched_data}"
        }
    
    def _deduplicate_and_boost(self, suggestions: List[Dict]) -> List[Dict]:
        """Remove duplicates and boost confidence for multiple matches"""
        loan_matches = {}
        
        for suggestion in suggestions:
            loan_id = suggestion['loan_id']
            
            if loan_id not in loan_matches:
                loan_matches[loan_id] = suggestion
            else:
                # Multiple matches for same loan - boost confidence
                existing = loan_matches[loan_id]
                if suggestion['confidence'] > existing['confidence']:
                    loan_matches[loan_id] = suggestion
                
                # Boost confidence for multiple detection methods
                loan_matches[loan_id]['confidence'] = min(99, loan_matches[loan_id]['confidence'] + 5)
                loan_matches[loan_id]['reason'] += f" + {suggestion['reason']}"
        
        return list(loan_matches.values())
