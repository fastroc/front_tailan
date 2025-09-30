"""
SIMPLIFIED Smart Suggestion Service

FOCUSED FUNCTIONALITY:
- License Plate Number → Customer Loan
- Phone Number → Customer Loan
- ID Number → Customer Loan

REMOVED:
- Complex UI components
- Multiple engines
- Confidence calculators
- Caching systems
- Complex ranking
"""

import re
from typing import List, Dict, Optional
from django.db.models import Q


class SimplifiedSmartSuggestionService:
    """
    Ultra-simple suggestion service focused on direct customer identification
    """

    def __init__(self):
        self.service_name = "Simplified Smart Suggestions"
        self.version = "2.0.0-minimal"

    def get_suggestions(self, bank_description: str, amount: float = 0) -> List[Dict]:
        """
        Get suggestions based on License Plate, Phone, or ID Number

        Args:
            bank_description: Bank transaction description
            amount: Transaction amount (optional)

        Returns:
            List of simple suggestions with customer info
        """
        suggestions = []

        # 1. Try License Plate matching
        license_suggestions = self._match_license_plate(bank_description)
        suggestions.extend(license_suggestions)

        # 2. Try Phone Number matching
        phone_suggestions = self._match_phone_number(bank_description)
        suggestions.extend(phone_suggestions)

        # 3. Try ID Number matching
        id_suggestions = self._match_id_number(bank_description)
        suggestions.extend(id_suggestions)

        # Remove duplicates and return top 3
        unique_suggestions = self._remove_duplicates(suggestions)
        return unique_suggestions[:3]

    def _match_license_plate(self, description: str) -> List[Dict]:
        """Match license plate patterns like КБ-123АА, УБ-4455, etc."""
        suggestions = []

        # Mongolian license plate patterns
        patterns = [
            r"[А-Я]{2}-?\d{3,4}[А-Я]{0,2}",  # КБ-123АА, УБ-4455
            r"[A-Z]{2}-?\d{3,4}[A-Z]{0,2}",  # KB-123AA (Latin)
            r"\d{4}[А-Я]{2}",  # 4455КБ
            r"\d{4}[A-Z]{2}",  # 4455KB
        ]

        for pattern in patterns:
            matches = re.findall(pattern, description.upper())
            for plate in matches:
                customer_suggestions = self._find_customer_by_plate(plate)
                suggestions.extend(customer_suggestions)

        return suggestions

    def _match_phone_number(self, description: str) -> List[Dict]:
        """Match phone number patterns"""
        suggestions = []

        # Phone number patterns
        patterns = [
            r"\b\d{8}\b",  # 88112233
            r"\b\d{4}[-\s]?\d{4}\b",  # 8811-2233, 8811 2233
            r"\+976[-\s]?\d{8}\b",  # +976-88112233
            r"976[-\s]?\d{8}\b",  # 976-88112233
        ]

        for pattern in patterns:
            matches = re.findall(pattern, description)
            for phone in matches:
                # Clean phone number differently for international vs local
                if phone.startswith("+976") or phone.startswith("976"):
                    # International format - extract the 8-digit local part
                    clean_phone = re.sub(r"[^\d]", "", phone)  # Remove non-digits
                    if len(clean_phone) >= 11:  # +976 + 8 digits
                        clean_phone = clean_phone[-8:]  # Take last 8 digits
                else:
                    # Local format - use as is if 8 digits
                    clean_phone = re.sub(
                        r"[-\s]", "", phone
                    )  # Only remove dashes and spaces

                if len(clean_phone) == 8:  # Valid Mongolia phone
                    customer_suggestions = self._find_customer_by_phone(clean_phone)
                    suggestions.extend(customer_suggestions)

        return suggestions

    def _match_id_number(self, description: str) -> List[Dict]:
        """Match national ID patterns"""
        suggestions = []

        # Mongolian ID patterns
        patterns = [
            r"[А-Я]{2}\d{8}",  # АБ12345678
            r"[A-Z]{2}\d{8}",  # AB12345678
            r"\b\d{10}\b",  # 1234567890
        ]

        for pattern in patterns:
            matches = re.findall(pattern, description.upper())
            for id_num in matches:
                customer_suggestions = self._find_customer_by_id(id_num)
                suggestions.extend(customer_suggestions)

        return suggestions

    def _find_customer_by_plate(self, plate: str) -> List[Dict]:
        """Find customer by vehicle registration - search in name fields since no vehicle_registration field"""
        suggestions = []

        try:
            from loans_customers.models import Customer
            from loans_core.models import Loan

            # Search for plate in various customer fields since there's no specific vehicle field
            customers = Customer.objects.filter(
                Q(business_name__icontains=plate)  # Sometimes plate in business name
                | Q(first_name__icontains=plate)  # Sometimes in name field
                | Q(last_name__icontains=plate)  # Sometimes in last name
                | Q(customer_id__icontains=plate)  # Sometimes in customer_id field
            ).distinct()

            for customer in customers:
                # Get customer's active loans
                loans = Loan.objects.filter(
                    customer=customer, status="active"
                ).first()  # Get first active loan

                if loans:
                    suggestion = {
                        "customer_id": customer.id,
                        "customer_name": f"{customer.first_name} {customer.last_name}".strip(),
                        "loan_id": loans.id,
                        "loan_number": getattr(loans, "loan_number", f"LN-{loans.id}"),
                        "match_type": "license_plate",
                        "match_value": plate,
                        "confidence": 80,  # Lower confidence since no dedicated field
                    }
                    suggestions.append(suggestion)

        except Exception as e:
            print(f"License plate search error: {e}")

        return suggestions

    def _find_customer_by_phone(self, phone: str) -> List[Dict]:
        """Find customer by phone number"""
        suggestions = []

        try:
            from loans_customers.models import Customer
            from loans_core.models import Loan

            customers = Customer.objects.filter(
                Q(phone_primary__icontains=phone)
                | Q(phone_secondary__icontains=phone)
                | Q(emergency_contact_phone__icontains=phone)
            ).distinct()

            for customer in customers:
                loans = Loan.objects.filter(customer=customer, status="active").first()

                if loans:
                    suggestion = {
                        "customer_id": customer.id,
                        "customer_name": f"{customer.first_name} {customer.last_name}".strip(),
                        "loan_id": loans.id,
                        "loan_number": getattr(loans, "loan_number", f"LN-{loans.id}"),
                        "match_type": "phone",
                        "match_value": phone,
                        "confidence": 85,
                    }
                    suggestions.append(suggestion)

        except Exception as e:
            print(f"Phone search error: {e}")

        return suggestions

    def _find_customer_by_id(self, id_number: str) -> List[Dict]:
        """Find customer by national ID"""
        suggestions = []

        try:
            from loans_customers.models import Customer
            from loans_core.models import Loan

            customers = Customer.objects.filter(
                Q(national_id__icontains=id_number)
                | Q(business_registration_number__icontains=id_number)
            ).distinct()

            for customer in customers:
                loans = Loan.objects.filter(customer=customer, status="active").first()

                if loans:
                    suggestion = {
                        "customer_id": customer.id,
                        "customer_name": f"{customer.first_name} {customer.last_name}".strip(),
                        "loan_id": loans.id,
                        "loan_number": getattr(loans, "loan_number", f"LN-{loans.id}"),
                        "match_type": "id_number",
                        "match_value": id_number,
                        "confidence": 95,  # ID is most reliable
                    }
                    suggestions.append(suggestion)

        except Exception as e:
            print(f"ID search error: {e}")

        return suggestions

    def _remove_duplicates(self, suggestions: List[Dict]) -> List[Dict]:
        """Remove duplicate suggestions based on customer_id"""
        seen_customers = set()
        unique_suggestions = []

        for suggestion in suggestions:
            customer_id = suggestion.get("customer_id")
            if customer_id not in seen_customers:
                seen_customers.add(customer_id)
                unique_suggestions.append(suggestion)

        # Sort by confidence (highest first)
        unique_suggestions.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        return unique_suggestions
