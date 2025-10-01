"""
License Plate Engine

Independent smart matching engine dedicated to license plate detection and matching.
Supports various license plate formats and provides flexible matching capabilities.
"""

import re
from typing import List, Dict
from ..base_engine import SmartMatchingEngine


class LicensePlateEngine(SmartMatchingEngine):
    """Dedicated license plate detection and matching engine"""

    def __init__(self):
        super().__init__()
        self.engine_name = "License Plate Engine"
        self.version = "1.0.0"

        # License plate patterns (common formats + actual database format)
        self.license_patterns = [
            r"\b[A-Za-zА-ЯӨөҮүЁё]{2,3}[-]?\d{3,4}\b",  # ABC-1234, АБВ1234 (with Mongolian chars)
            r"\b\d{3,4}[A-Za-zА-ЯӨөҮүЁё]{2,3}\b",  # 1234ABC, 1234АБВ, 6747унө (with Mongolian chars)
            r"\b\d{3,4}\s+[A-Za-zА-ЯӨөҮүЁё]{2,3}\b",  # 2542 ung, 1234 ABC (numbers + space + letters)
            r"\b[A-Za-zА-ЯӨөҮүЁё]{3}\d{3}[A-Za-zА-ЯӨөҮүЁё]\b",  # ABC123D
            r"\b\d{2}[A-Za-zА-ЯӨөҮүЁё]{2}\d{3}\b",  # 12AB345
            r"\d{2}-\d{2}\s*[А-ЯӨөҮүЁё]{3}",  # 25-42 УНГ (actual database format)
            r"\d{4}[А-ЯӨөҮүЁё]{3}",  # 6045УАМ (user input format)
            r"[А-ЯӨөҮүЁё]{2}\d{4}[А-ЯӨөҮүЁё]{2}",  # АБ1234ВГ
            r"[A-Z]\d{3}[A-Z]{2}",  # A123BC
        ]
        
        # Secondary patterns for fallback matching (lower confidence)
        self.fallback_patterns = [
            r"\b\d{4}\b",  # Just 4 digits (e.g., "2542")
            r"\b\d{3}\b",  # Just 3 digits (e.g., "123")
        ]

    def detect_loans(self, bank_description: str, amount: float) -> List[Dict]:
        """Detect loans by license plate number"""
        suggestions = []

        # Primary: Extract full license plates from description
        license_plates = self._extract_license_plates(bank_description)
        is_primary_match = len(license_plates) > 0
        
        # Secondary: If no full plates found, try fallback patterns (just numbers)
        if not license_plates:
            license_plates = self._extract_fallback_patterns(bank_description)

        if not license_plates:
            return suggestions

        try:
            from loans_core.models import Loan
            from loans_collateral.models import Collateral

            for plate in license_plates:
                # Use the extraction method to determine if this is fallback
                is_fallback = not is_primary_match
                matches = self._find_collateral_by_plate(plate, is_fallback)

                for collateral in matches:
                    try:
                        # Get the loan associated with this collateral
                        loan = collateral.loan_application.loan
                        customer = collateral.loan_application.customer

                        if loan and loan.status == "active":
                            suggestion = self._format_suggestion(loan, customer, plate, is_fallback)
                            suggestion["vehicle_info"] = (
                                f"{collateral.vehicle_make} {collateral.vehicle_model}".strip()
                            )
                            suggestions.append(suggestion)
                    except Exception:
                        continue  # Skip if no loan found

        except Exception as e:
            self._log_error(f"License plate detection error: {e}")
            return []

        return suggestions

    def _extract_fallback_patterns(self, description: str) -> List[str]:
        """Extract fallback patterns (standalone numbers) from description"""
        fallback_plates = []

        for pattern in self.fallback_patterns:
            plates = re.findall(pattern, description, re.IGNORECASE)
            fallback_plates.extend(plates)

        # Remove duplicates while preserving order
        return list(dict.fromkeys(fallback_plates))

    def _is_fallback_pattern(self, plate: str) -> bool:
        """Check if a plate matches fallback patterns (just numbers)"""
        for pattern in self.fallback_patterns:
            if re.match(pattern, plate):
                return True
        return False

    def _extract_license_plates(self, description: str) -> List[str]:
        """Extract license plate numbers from description"""
        license_plates = []

        for pattern in self.license_patterns:
            plates = re.findall(pattern, description, re.IGNORECASE)
            license_plates.extend(plates)

        # Remove duplicates while preserving order
        return list(dict.fromkeys(license_plates))

    def _find_collateral_by_plate(self, plate: str, is_fallback: bool = False) -> List:
        """Find collateral items matching the license plate"""
        from loans_collateral.models import Collateral

        matches = []
        clean_input = plate.replace("-", "").replace(" ", "").strip().upper()

        # For fallback patterns (just numbers), search within license plates
        if is_fallback:
            all_collateral = Collateral.objects.select_related(
                "loan_application__customer"
            ).prefetch_related("loan_application__loan")

            for item in all_collateral:
                if item.vehicle_license_plate:
                    # Check if the fallback number is contained in the license plate
                    clean_db = item.vehicle_license_plate.replace("-", "").replace(" ", "").upper()
                    if clean_input in clean_db:
                        matches.append(item)
            return matches

        # Primary matching: exact, flexible, and cross-script matching
        # First try exact match
        collateral_items = (
            Collateral.objects.filter(vehicle_license_plate__iexact=plate.strip())
            .select_related("loan_application__customer")
            .prefetch_related("loan_application__loan")
        )

        if collateral_items.exists():
            return list(collateral_items)

        # If no exact match, try flexible matching (remove formatting + cross-script)
        all_collateral = Collateral.objects.select_related(
            "loan_application__customer"
        ).prefetch_related("loan_application__loan")

        for item in all_collateral:
            if item.vehicle_license_plate:
                clean_db = item.vehicle_license_plate.replace("-", "").replace(" ", "").upper()
                
                # Direct match after cleaning
                if clean_db == clean_input:
                    matches.append(item)
                    continue
                
                # Number-based matching: extract and compare just the numbers
                if self._is_number_match(clean_input, clean_db):
                    matches.append(item)
                    continue
                
                # Cross-script matching: convert "0311uby" to match "0311УБЯ"
                if self._is_cross_script_match(clean_input, clean_db):
                    matches.append(item)

        return matches

    def _is_number_match(self, input_plate: str, db_plate: str) -> bool:
        """Check if plates match based on numbers only (ignores letters and formatting)"""
        import re
        
        # Extract all numbers from both plates
        input_numbers = ''.join(re.findall(r'\d', input_plate))
        db_numbers = ''.join(re.findall(r'\d', db_plate))
        
        # Must have at least 3-4 digits to be considered a license plate number match
        if len(input_numbers) >= 3 and len(db_numbers) >= 3:
            return input_numbers == db_numbers
        
        return False

    def _is_cross_script_match(self, input_plate: str, db_plate: str) -> bool:
        """Check if plates match across Latin/Cyrillic scripts"""
        # Enhanced cross-script matching using transliteration
        try:
            from ..transliteration_utils import TransliterationUtils
            transliterator = TransliterationUtils()
            
            # Try to match using flexible transliteration
            if transliterator.flexible_match(input_plate, db_plate):
                return True
                
        except ImportError:
            pass
        
        # Fallback: Basic Latin to Cyrillic mapping for common license plate letters
        latin_to_cyrillic = {
            'A': 'А', 'B': 'Б', 'C': 'С', 'E': 'Е', 'H': 'Н', 'K': 'К', 'M': 'М', 
            'O': 'О', 'P': 'Р', 'T': 'Т', 'X': 'Х', 'Y': 'У',
            # Common license plate combinations
            'UNG': 'УНГ', 'UAM': 'УАМ', 'UBY': 'УБЯ', 'UNK': 'УНК', 'UNO': 'УНӨ',
            'UBM': 'УБМ', 'UEN': 'УЕН', 'UNN': 'УНН', 'UBO': 'УБӨ', 'UAH': 'УАХ',
            'UBU': 'УБУ', 'UBR': 'УБР', 'UAU': 'УАУ'
        }
        
        # Convert Latin characters to Cyrillic
        converted_input = input_plate
        for latin, cyrillic in latin_to_cyrillic.items():
            converted_input = converted_input.replace(latin, cyrillic)
        
        return converted_input == db_plate

    def _format_suggestion(self, loan, customer, plate: str, is_fallback: bool = False) -> Dict:
        """Format loan suggestion with license plate information"""
        return {
            "loan_id": loan.id,
            "loan_number": loan.loan_number,
            "customer_id": customer.id,
            "customer_name": f"{customer.first_name} {customer.last_name}".strip(),
            "confidence": self._calculate_confidence(plate, is_fallback),
            "method": "license_plate_fallback" if is_fallback else "license_plate_match",
            "matched_data": plate,
            "loan_amount": float(loan.current_balance),
            "loan_type": loan.loan_product.category,
            "reason": f"License plate {plate} found in description" + (" (partial match)" if is_fallback else ""),
            "engine": self.engine_name,
        }

    def _calculate_confidence(self, plate: str, is_fallback: bool = False) -> int:
        """Calculate confidence score based on plate format"""
        # Fallback patterns get much lower confidence
        if is_fallback:
            if len(plate) == 4:  # 4-digit fallback
                return 50  # Lower confidence for partial matches
            elif len(plate) == 3:  # 3-digit fallback
                return 40  # Even lower for 3-digit matches
            else:
                return 35  # Very low for other fallback patterns
        
        # Base confidence for full license plate match
        confidence = 80

        # Higher confidence for more specific formats
        if re.match(r"\d{4}[А-Я]{3}", plate):  # 6045УАМ format
            confidence = 85
        elif re.match(r"\d{2}-\d{2}\s*[А-Я]{3}", plate):  # 25-42 УНГ format
            confidence = 90  # Database format gets highest confidence
        elif re.match(r"\b\d{3,4}\s+[A-Za-zА-Я]{2,3}\b", plate):  # 2542 ung format
            confidence = 75  # Good confidence for spaced format
        elif re.match(r"[A-Za-z]{2,3}[-]?\d{3,4}", plate):  # ABC-1234 format
            confidence = 82

        return confidence

    def validate_plate_format(self, plate: str) -> bool:
        """Validate if string matches any known license plate format"""
        for pattern in self.license_patterns:
            if re.match(pattern, plate, re.IGNORECASE):
                return True
        return False

    def normalize_plate(self, plate: str) -> str:
        """Normalize license plate for consistent matching"""
        return plate.replace("-", "").replace(" ", "").upper().strip()

    def get_supported_formats(self) -> List[str]:
        """Get list of supported license plate formats"""
        return [
            "6045УАМ (4 digits + 3 Cyrillic letters)",
            "25-42 УНГ (2-2 digits + 3 Cyrillic letters)",
            "ABC-1234 (3 letters + 4 digits)",
            "1234АБВ (4 digits + 3 letters)",
            "ABC123D (3 letters + 3 digits + 1 letter)",
            "12AB345 (2 digits + 2 letters + 3 digits)",
            "АБ1234ВГ (2 letters + 4 digits + 2 letters)",
            "A123BC (1 letter + 3 digits + 2 letters)",
        ]

    def get_engine_info(self) -> Dict:
        """Get engine information and capabilities"""
        return {
            "name": self.engine_name,
            "version": self.version,
            "description": "Dedicated license plate detection and matching",
            "supported_formats": len(self.license_patterns),
            "capabilities": [
                "Multiple format support",
                "Flexible matching (with/without formatting)",
                "Cyrillic and Latin script support",
                "Vehicle information extraction",
            ],
            "confidence_range": "80-90%",
            "independent": True,
            "debuggable": True,
            "removable": True,
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
            "Payment for vehicle 6045УАМ loan installment",
            "Car with license 25-42 УНГ monthly payment",
            "Vehicle ABC-1234 loan payment received",
            "Monthly payment 1234АБВ vehicle loan",
        ]

        results = {
            "engine": self.engine_name,
            "test_cases": len(test_cases),
            "plates_detected": 0,
            "patterns_working": 0,
            "status": "unknown",
        }

        for test_case in test_cases:
            plates = self._extract_license_plates(test_case)
            if plates:
                results["plates_detected"] += len(plates)
                results["patterns_working"] += 1

        results["success_rate"] = (results["patterns_working"] / len(test_cases)) * 100
        results["status"] = "PASS" if results["success_rate"] >= 75 else "FAIL"

        return results
