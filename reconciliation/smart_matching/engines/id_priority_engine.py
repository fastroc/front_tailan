"""
ID Priority Engine

Smart matching engine that prioritizes ID number detection in bank transaction descriptions.
Looks for Cyrillic ID patterns (ЧЛ74090619) and extracts the numeric part for matching.
Uses transliteration utilities for flexible name and ID matching.
"""

import re
from typing import List, Dict
from django.db import models
from ..base_engine import SmartMatchingEngine
from ..transliteration_utils import transliteration


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
            r"[ЧЦ][ЛЪ](\d{8})",  # ЧЛ74090619, ЦЪ12345678
            r"[ТT][ЗZ](\d{8})",  # ТЗ71080171, TZ71080171 (mixed)
            r"[УУӨ][Т](\d{8})",  # УТ12345678, ӨТ12345678
            # Latin equivalents often used
            r"[TТ][ZЗ](\d{8})",  # TZ71080171, ТZ71080171 (mixed)
            r"[CcЧ][LlЛ](\d{8})",  # CL74090619, Cl74090619, ЧL74090619
            r"[UuУӨ][TtТ](\d{8})",  # UT12345678, ut12345678, УT12345678
            # Common typing mistakes and variations
            r"[ЧCc][ЛLl](\d{8})",  # Mixed script: Чl74090619, CЛ74090619
            r"[ТT][ЗZ3](\d{8})",  # TZ71080171 with number 3 instead of З
            r"[УY][ТT](\d{8})",  # Sometimes Y used instead of У
            # Special patterns for Mongolian ID variations
            r"[ВвWw][ЭэEe](\d{8})",  # ВЭ70102015, we70102015, WE70102015
            r"[БбBb][ГгGg](\d{8})",  # БГ pattern variations
            r"[ДдDd][ЭэEe](\d{8})",  # ДЭ pattern variations
            # FLEXIBLE: Any letters followed by 8 digits (catches unknown prefixes)
            r"\b[A-Za-zА-Я]+(\d{8})\b",  # xx70102015, abc12345678, любая буквенная комбинация
            # ID patterns without prefix (fallback)
            r"\b(\d{8})\b",  # Just 8 digits if other patterns fail
        ]

        all_matches = []
        for pattern in id_patterns:
            matches = re.findall(pattern, bank_description, re.IGNORECASE | re.UNICODE)
            all_matches.extend(matches)

        # Remove duplicates while preserving order
        id_numbers = list(dict.fromkeys(all_matches))

        if not id_numbers:
            return suggestions

        try:
            from loans_core.models import Loan
            from loans_customers.models import Customer

            # ID number matching (enhanced with script tolerance)
            for id_number in id_numbers:
                # Normalize ID for search - remove common prefixes and focus on numbers
                normalized_id = id_number.replace(" ", "").replace("-", "")

                # Search by ID number with enhanced transliteration strategies
                customers = self._find_customers_by_id_flexible(
                    normalized_id, id_number
                )

                for customer in customers:
                    # Get active loans for this customer
                    active_loans = Loan.objects.filter(
                        customer=customer, status="active"
                    ).select_related("loan_product")

                    for loan in active_loans:
                        # Calculate confidence based on pattern match quality
                        confidence = self._calculate_id_confidence(
                            id_number, customer.national_id
                        )

                        suggestions.append(
                            {
                                "loan_id": loan.id,
                                "loan_number": loan.loan_number,
                                "customer_id": customer.id,
                                "customer_name": f"{customer.first_name} {customer.last_name}".strip(),
                                "confidence": confidence,
                                "method": "id_number_match",
                                "matched_data": id_number,
                                "loan_amount": float(loan.current_balance),
                                "loan_type": loan.loan_product.category,
                                "reason": f"ID number {id_number} found in description (script-tolerant match)",
                            }
                        )

        except Exception as e:
            print(f"ID Priority Engine error: {e}")

        return suggestions

    def _calculate_id_confidence(
        self, matched_id: str, customer_national_id: str
    ) -> int:
        """Calculate confidence score based on ID match quality"""
        if not customer_national_id:
            return 50

        # Exact numeric match gets highest score
        if matched_id in customer_national_id:
            return 95

        # Partial match but high similarity
        if len(matched_id) >= 6 and matched_id in customer_national_id.replace(
            " ", ""
        ).replace("-", ""):
            return 85

        # Weak match
        return 70

    def _find_customers_by_id_flexible(self, normalized_id: str, original_id: str):
        """Find customers using flexible transliteration matching"""
        from loans_customers.models import Customer

        # Generate ID variations using transliteration
        id_variations = transliteration.normalize_id_prefix(original_id)
        id_variations.extend([normalized_id, original_id])

        # Search using all variations
        query = models.Q()
        for id_variant in set(id_variations):  # Remove duplicates
            query |= models.Q(national_id__contains=id_variant)
            query |= models.Q(national_id__endswith=id_variant)
            query |= models.Q(national_id__icontains=id_variant)

        customers = Customer.objects.filter(query).distinct()

        # Additional flexible matching for customers not found by direct search
        if not customers.exists():
            all_customers = Customer.objects.all()
            flexible_matches = []

            for customer in all_customers:
                if customer.national_id and transliteration.flexible_match(
                    original_id, customer.national_id
                ):
                    flexible_matches.append(customer)

            # Convert list back to queryset-like
            return flexible_matches

        return customers

    def _find_customers_by_name_flexible(self, name_text: str):
        """Find customers using flexible transliteration matching for names"""
        from loans_customers.models import Customer

        # Generate name variations using transliteration
        name_variations = transliteration.normalize_name(name_text)

        # Search using all variations
        query = models.Q()
        for name_variant in name_variations:
            query |= models.Q(first_name__icontains=name_variant)
            query |= models.Q(last_name__icontains=name_variant)

        customers = Customer.objects.filter(query).distinct()

        # Additional flexible matching
        if not customers.exists():
            all_customers = Customer.objects.all()
            flexible_matches = []

            for customer in all_customers:
                full_name = f"{customer.first_name} {customer.last_name}".strip()
                if transliteration.flexible_match(name_text, full_name):
                    flexible_matches.append(customer)
                elif transliteration.flexible_match(name_text, customer.first_name):
                    flexible_matches.append(customer)
                elif transliteration.flexible_match(name_text, customer.last_name):
                    flexible_matches.append(customer)

            return flexible_matches

        return customers
