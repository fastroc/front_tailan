"""
ID Priority Engine

Smart matching engine that prioritizes ID number detection in bank transaction descriptions.
Looks for Cyrillic ID patterns (ЧЛ74090619) and extracts the numeric part for matching.
"""

import re
from typing import List, Dict
from django.db import models
from ..base_engine import SmartMatchingEngine


class IDPriorityEngine(SmartMatchingEngine):
    """Prioritizes ID number matching (ЧЛ74090619 format) for loan detection"""
    
    def __init__(self):
        super().__init__()
        self.name = "IDPriorityEngine"
        self.version = "1.0"
        
    def detect_loans(self, bank_description: str, amount: float) -> List[Dict]:
        """Detect loans by matching ID numbers and license plates in bank description with enhanced script handling"""
        
        suggestions = []
        
        # 1. Enhanced ID patterns to handle Cyrillic/Latin script mixing
        # Examples: ЧЛ74090619, TZ71080171, ТЗ71080171, CL74090619
        # Handle common confusions: T/Т, Z/З, U/У/Ө, C/Ч, L/Л
        
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
            
            # ID patterns without prefix (fallback)
            r'\b(\d{8})\b',               # Just 8 digits if other patterns fail
        ]
        
        all_matches = []
        for pattern in id_patterns:
            matches = re.findall(pattern, bank_description, re.IGNORECASE | re.UNICODE)
            all_matches.extend(matches)
        
        # Remove duplicates while preserving order
        id_numbers = list(dict.fromkeys(all_matches))
        
        # 2. Extract license plate patterns (same as PhonePriorityEngine)
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
            plates = re.findall(pattern, bank_description, re.IGNORECASE)
            license_plates.extend(plates)
        
        # Remove duplicates
        license_plates = list(set(license_plates))
        
        try:
            from loans_core.models import Loan
            from loans_customers.models import Customer
            from loans_collateral.models import Collateral
            
            # ID number matching (enhanced with script tolerance)
            for id_number in id_numbers:
                # Normalize ID for search - remove common prefixes and focus on numbers
                normalized_id = id_number.replace(' ', '').replace('-', '')
                
                # Search by ID number with multiple strategies
                customers = Customer.objects.filter(
                    models.Q(national_id__contains=normalized_id) |
                    models.Q(national_id__endswith=normalized_id) |
                    models.Q(national_id__icontains=id_number)
                ).distinct()
                
                for customer in customers:
                    # Get active loans for this customer
                    active_loans = Loan.objects.filter(
                        customer=customer,
                        status='active'
                    ).select_related('loan_product')
                    
                    for loan in active_loans:
                        # Calculate confidence based on pattern match quality
                        confidence = self._calculate_id_confidence(id_number, customer.national_id)
                        
                        suggestions.append({
                            'loan_id': loan.id,
                            'loan_number': loan.loan_number,
                            'customer_id': customer.id,
                            'customer_name': f"{customer.first_name} {customer.last_name}".strip(),
                            'confidence': confidence,
                            'method': 'id_number_match',
                            'matched_data': id_number,
                            'loan_amount': float(loan.current_balance),
                            'loan_type': loan.loan_product.category,
                            'reason': f"ID number {id_number} found in description (script-tolerant match)"
                        })
            
            # License plate matching (new functionality)
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
                            suggestions.append({
                                'loan_id': loan.id,
                                'loan_number': loan.loan_number,
                                'customer_id': customer.id,
                                'customer_name': f"{customer.first_name} {customer.last_name}".strip(),
                                'confidence': 80,  # Good confidence for license plate match
                                'method': 'license_plate_match',
                                'matched_data': plate,
                                'loan_amount': float(loan.current_balance),
                                'loan_type': loan.loan_product.category,
                                'reason': f"License plate {plate} found in description",
                                'vehicle_info': f"{collateral.vehicle_make} {collateral.vehicle_model}".strip()
                            })
                    except Exception:
                        continue  # Skip if no loan found
        
        except Exception as e:
            print(f"❌ IDPriorityEngine error: {e}")
            return []
        
        return suggestions
    
    def _calculate_id_confidence(self, matched_id: str, customer_national_id: str) -> int:
        """Calculate confidence score based on ID match quality"""
        if not customer_national_id:
            return 50
            
        # Exact numeric match gets highest score
        if matched_id in customer_national_id:
            return 95
            
        # Partial match but high similarity
        if len(matched_id) >= 6 and matched_id in customer_national_id.replace(' ', '').replace('-', ''):
            return 85
            
        # Weak match
        return 70
