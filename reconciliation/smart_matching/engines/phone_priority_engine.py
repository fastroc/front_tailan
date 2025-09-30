"""
Phone Priority Engine

Smart matching engine that prioritizes phone number detection in bank transaction descriptions.
Looks for 8-digit phone numbers and matches them against customer database.
"""

import re
from typing import List, Dict
from ..base_engine import SmartMatchingEngine


class PhonePriorityEngine(SmartMatchingEngine):
    """Prioritizes phone number matching (8 digits) for loan detection"""
    
    def __init__(self):
        super().__init__()
        self.name = "PhonePriorityEngine"
        self.version = "1.0"
        
    def detect_loans(self, bank_description: str, amount: float) -> List[Dict]:
        """Detect loans by matching phone numbers and license plates in bank description"""
        
        suggestions = []
        
        # 1. Extract 8-digit phone numbers from description
        phone_pattern = r'\b\d{8}\b'
        phones = re.findall(phone_pattern, bank_description)
        
        # 2. Extract license plate patterns (common formats)
        # Examples: ABC-1234, 1234ABC, АБВ1234, 1234АБВ, ABC123D
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
            
            # Phone number matching (original functionality)
            for phone in phones:
                customers = Customer.objects.filter(phone_primary=phone)
                
                for customer in customers:
                    active_loans = Loan.objects.filter(
                        customer=customer,
                        status='active'
                    ).select_related('loan_product')
                    
                    for loan in active_loans:
                        suggestions.append({
                            'loan_id': loan.id,
                            'loan_number': loan.loan_number,
                            'customer_id': customer.id,
                            'customer_name': f"{customer.first_name} {customer.last_name}".strip(),
                            'confidence': 95,  # High confidence for exact phone match
                            'method': 'phone_exact_match',
                            'matched_data': phone,
                            'loan_amount': float(loan.current_balance),
                            'loan_type': loan.loan_product.category,
                            'reason': f"Phone number {phone} found in description"
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
                                'confidence': 85,  # High confidence for license plate match
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
            print(f"❌ PhonePriorityEngine error: {e}")
            return []
        
        return suggestions
