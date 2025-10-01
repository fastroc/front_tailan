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
        """Detect loans by matching phone numbers in bank description"""

        suggestions = []

        # Extract 8-digit phone numbers from description
        phone_pattern = r"\b\d{8}\b"
        phones = re.findall(phone_pattern, bank_description)

        try:
            from loans_core.models import Loan
            from loans_customers.models import Customer

            # Phone number matching
            for phone in phones:
                customers = Customer.objects.filter(phone_primary=phone)

                for customer in customers:
                    active_loans = Loan.objects.filter(
                        customer=customer, status="active"
                    ).select_related("loan_product")

                    for loan in active_loans:
                        suggestions.append(
                            {
                                "loan_id": loan.id,
                                "loan_number": loan.loan_number,
                                "customer_id": customer.id,
                                "customer_name": f"{customer.first_name} {customer.last_name}".strip(),
                                "confidence": 95,  # High confidence for exact phone match
                                "method": "phone_exact_match",
                                "matched_data": phone,
                                "loan_amount": float(loan.current_balance),
                                "loan_type": loan.loan_product.category,
                                "reason": f"Phone number {phone} found in description",
                            }
                        )

        except Exception as e:
            print(f"❌ PhonePriorityEngine error: {e}")
            return []

        return suggestions
