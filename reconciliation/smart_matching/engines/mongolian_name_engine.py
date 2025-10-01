"""
Mongolian Name Engine - Matches customers based on Mongolian name patterns
Handles patterns like "Б.Ням-Ochir", "Б.Очмаа", "Б.Номин-Эрдэнэ" etc.
"""

import re
from typing import List, Dict, Any, Optional
from django.db.models import Q
from ..base_engine import SmartMatchingEngine
from ..transliteration_utils import TransliterationUtils


class MongolianNameEngine(SmartMatchingEngine):
    """Engine for matching Mongolian customer names in transaction descriptions"""

    def __init__(self):
        super().__init__()
        self.name = "MongolianNameEngine"
        self.version = "1.0"
        self.transliterator = TransliterationUtils()

    def extract_names(self, description: str) -> List[str]:
        """Extract potential Mongolian names from description"""
        if not description:
            return []

        names = []

        # Pattern 1: "Б.Name" or "А.Name" etc (Initial + full name) - PRIORITY
        # Support both Cyrillic and Latin scripts
        pattern1_cyrillic = r"[А-ЯЁа-яё]\.[А-Яа-яё\-]+"
        pattern1_latin = r"[A-Za-z]\.[A-Za-z\-]+"
        
        matches1_cyrillic = re.findall(pattern1_cyrillic, description, re.IGNORECASE)
        matches1_latin = re.findall(pattern1_latin, description, re.IGNORECASE)
        matches1 = matches1_cyrillic + matches1_latin
        names.extend(matches1)

        # Pattern 2: Names after "EB-" prefix (more specific)
        # Support both Cyrillic and Latin scripts
        eb_pattern_cyrillic = r"EB\-([А-ЯЁа-яё]\.[А-Яа-яё\-]+)"
        eb_pattern_latin = r"EB\-([A-Za-z]\.[A-Za-z\-]+)"
        
        eb_matches_cyrillic = re.findall(eb_pattern_cyrillic, description, re.IGNORECASE)
        eb_matches_latin = re.findall(eb_pattern_latin, description, re.IGNORECASE)
        eb_matches = eb_matches_cyrillic + eb_matches_latin
        names.extend(eb_matches)

        # Pattern 3: Full compound names with hyphens (only if no pattern1 matches)
        if not matches1:  # Only if we didn't find pattern1 matches
            pattern3 = r"[А-ЯЁа-яё][а-яё]+\-[А-ЯЁа-яё][а-яё]+(?:\-[А-ЯЁа-яё][а-яё]+)*"
            matches3 = re.findall(pattern3, description, re.IGNORECASE)
            # Filter to avoid false positives (must be at least 6 chars for compound names)
            names.extend([name for name in matches3 if len(name) >= 6])

        # Pattern 4: Standalone Mongolian names (if no other patterns matched)
        if not matches1 and not eb_matches:  # Only if no better patterns found
            # Look for typical Mongolian name patterns (at least 6 chars to avoid false positives)
            # Support both Cyrillic and Latin scripts
            standalone_cyrillic = r"\b[А-ЯЁа-яё][а-яё]{5,}\b"  # Cyrillic names
            standalone_latin = r"\b[A-Za-z][a-z]{5,}\b"        # Latin names
            
            cyrillic_matches = re.findall(standalone_cyrillic, description, re.IGNORECASE)
            latin_matches = re.findall(standalone_latin, description, re.IGNORECASE)
            
            # Filter out common non-name words for both scripts
            mongolian_names = []
            common_words_cyrillic = [
                "зээлийн", "олгосон", "төлбөр", "гүйлгээ", "харилцах", "огноо"
            ]
            common_words_latin = [
                "payment", "transfer", "amount", "reference", "account", "transaction"
            ]
            
            for match in cyrillic_matches:
                if match.lower() not in common_words_cyrillic:
                    mongolian_names.append(match)
            
            for match in latin_matches:
                if match.lower() not in common_words_latin:
                    mongolian_names.append(match)
                    
            names.extend(mongolian_names)

        # Clean and deduplicate
        cleaned_names = []
        for name in names:
            name = name.strip()
            if len(name) >= 2 and name not in cleaned_names:
                cleaned_names.append(name)

        return cleaned_names

    def normalize_name_for_matching(self, name: str) -> List[str]:
        """Generate variations of a name for flexible matching"""
        variations = []

        # First, clean the name by removing Mongolian grammatical suffixes (case-insensitive)
        cleaned_name = name
        mongolian_suffixes = [
            "-д", "-Д",  # Add uppercase versions
            "-г", "-Г",
            "-аар", "-ААР",
            "-ээр", "-ЭЭР", 
            "-аас", "-ААС",
            "-ээс", "-ЭЭС",
            "-тай", "-ТАЙ",
            "-тэй", "-ТЭЙ",
        ]
        for suffix in mongolian_suffixes:
            if cleaned_name.endswith(suffix):
                cleaned_name = cleaned_name[: -len(suffix)]
                break  # Only remove one suffix

        variations.append(cleaned_name)

        # Add transliteration variations for cross-script matching
        transliteration_variations = self.transliterator.normalize_name(cleaned_name)
        variations.extend(transliteration_variations)

        # If it's in format "Initial.Name", generate more variations
        if "." in cleaned_name and len(cleaned_name.split(".")) == 2:
            initial, full_name = cleaned_name.split(".")
            variations.append(full_name)  # Just the name part
            variations.append(initial + full_name)  # "БName"
            
            # For Mongolian names, also try reversed pattern (Name Initial)
            # This handles cases like "Т.ГАНТУЛГА" -> "ГАНТУЛГА Т" 
            variations.append(f"{full_name} {initial}")
            
            # Also try just the initial by itself for broader matching
            if len(initial) == 1:
                variations.append(initial)
                
            # IMPORTANT: Also add the clean name part without suffix for direct matching
            clean_full_name = full_name
            # Remove suffixes from the name part (case-insensitive)
            for suffix in ["-д", "-Д", "-г", "-Г", "-аар", "-ААР"]:
                if clean_full_name.endswith(suffix):
                    clean_full_name = clean_full_name[:-len(suffix)]
                    break
            if clean_full_name != full_name:
                variations.append(clean_full_name)  # "ГАНТУЛГА" from "ГАНТУЛГА-Д"

        # If it has hyphens, try parts separately (but only meaningful parts)
        if "-" in cleaned_name:
            parts = cleaned_name.split("-")
            # Only add parts that are at least 3 characters and not just initials
            meaningful_parts = [
                part
                for part in parts
                if len(part) >= 3 and not (len(part) == 1 and part.isupper())
            ]
            variations.extend(meaningful_parts)

        # Try without hyphens
        variations.append(cleaned_name.replace("-", ""))

        # Handle common Mongolian name typos/variations
        typo_fixes = {
            "ь": "а",  # Common typo
            "й": "и",  # Common variation
            "ы": "и",  # Common variation
        }

        for original_char, replacement_char in typo_fixes.items():
            if original_char in cleaned_name:
                variations.append(cleaned_name.replace(original_char, replacement_char))

        # Filter out very short variations that could cause false matches
        variations = [v for v in variations if len(v) >= 3]

        return list(set(variations))  # Remove duplicates

    def detect_loans(
        self, bank_description: str, amount: float
    ) -> List[Dict[str, Any]]:
        """Detect loans based on Mongolian name matching"""
        suggestions = []

        if not bank_description:
            return suggestions

        # Extract names from description
        extracted_names = self.extract_names(bank_description)

        if not extracted_names:
            return suggestions

        try:
            # Import here to avoid circular imports
            from loans_customers.models import Customer

            # Track best match data for each loan
            loan_best_matches = (
                {}
            )  # loan_id -> {suggestion_data, confidence, matched_data}

            # Search for customers matching extracted names
            for extracted_name in extracted_names:
                name_variations = self.normalize_name_for_matching(extracted_name)

                # Build query with prioritized matching
                name_query = Q()
                exact_matches = Q()
                partial_matches = Q()

                for variation in name_variations:
                    # PRIORITY 1: Exact matches (full field equals the variation)
                    exact_matches |= Q(first_name__iexact=variation)
                    exact_matches |= Q(last_name__iexact=variation)
                    exact_matches |= Q(middle_name__iexact=variation)

                    # PRIORITY 2: Start-with matches (for compound names)
                    partial_matches |= Q(first_name__istartswith=variation)
                    partial_matches |= Q(last_name__istartswith=variation)
                    partial_matches |= Q(middle_name__istartswith=variation)

                    # PRIORITY 3: Contains matches (only for longer variations to avoid false positives)
                    if len(variation) >= 5:  # Only use contains for longer strings
                        partial_matches |= Q(first_name__icontains=variation)
                        partial_matches |= Q(last_name__icontains=variation)
                        partial_matches |= Q(middle_name__icontains=variation)

                # Combine queries: exact matches first, then partial matches
                name_query = exact_matches | partial_matches

                # Find matching customers
                matching_customers = Customer.objects.filter(name_query).distinct()

                # If no matches found with database queries, try flexible transliteration matching
                if not matching_customers:
                    matching_customers = self._find_customers_with_transliteration(extracted_name)

                for customer in matching_customers:
                    # Calculate confidence based on match quality
                    confidence = self._calculate_confidence(
                        extracted_name, customer, bank_description
                    )

                    if (
                        confidence > 25
                    ):  # Lowered threshold to allow transliteration matches
                        # Get all customer's loans (applications AND active loans)
                        customer_loans = self._get_all_customer_loans(customer)
                        
                        if customer_loans:
                            # Use disambiguation service to rank loans by relevance
                            from reconciliation.customer_disambiguation import CustomerDisambiguationService
                            
                            # Detect transaction type for better matching
                            transaction_context = CustomerDisambiguationService.detect_transaction_type(
                                bank_description, amount
                            )
                            
                            # Rank loans by relevance to this transaction
                            ranked_loans = CustomerDisambiguationService.rank_loan_matches(
                                customer_loans=customer_loans,
                                transaction_amount=amount,
                                description=bank_description,
                                is_disbursement=transaction_context['is_disbursement']
                            )
                            
                            # Process top loans (limit to top 2 per customer to avoid clutter)
                            for ranked_loan in ranked_loans[:2]:
                                loan_id = ranked_loan['loan_id']
                                
                                # Check if we already have this loan with better confidence
                                if loan_id in loan_best_matches:
                                    if confidence <= loan_best_matches[loan_id]["confidence"]:
                                        continue  # Skip if we have a better match already

                                # Boost confidence based on disambiguation quality
                                disambiguation_boost = min(ranked_loan.get('disambiguation_score', 0) // 10, 15)
                                final_confidence = confidence + disambiguation_boost
                                
                                # Create enhanced suggestion with disambiguation info
                                suggestion = {
                                    "loan_id": loan_id,
                                    "loan_number": ranked_loan.get('loan_number'),
                                    "customer_id": customer.id,
                                    "customer_name": self._get_customer_display_name(customer),
                                    "confidence": final_confidence,
                                    "method": "mongolian_name_match_enhanced",
                                    "matched_data": extracted_name,
                                    "loan_amount": ranked_loan.get('loan_amount', 0),
                                    "loan_type": ranked_loan.get('loan_type', 'personal'),
                                    "disambiguation_score": ranked_loan.get('disambiguation_score', 0),
                                    "disambiguation_reason": ranked_loan.get('disambiguation_reason', ''),
                                    "transaction_type": transaction_context.get('transaction_type', 'unknown'),
                                }

                                # Format with disambiguation for clear display
                                suggestion = CustomerDisambiguationService.format_suggestion_with_disambiguation(suggestion)

                                loan_best_matches[loan_id] = {
                                    "suggestion": suggestion,
                                    "confidence": final_confidence,
                                    "matched_data": extracted_name,
                                }

            # Convert best matches to suggestions list
            suggestions = [match["suggestion"] for match in loan_best_matches.values()]

        except ImportError:
            # loans_customers module not available
            pass
        except Exception as e:
            print(f"Error in MongolianNameEngine: {e}")

        # Sort by confidence and remove duplicates
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        return suggestions[:10]  # Limit to top 10

    def _calculate_confidence(
        self, extracted_name: str, customer, bank_description: str
    ) -> int:
        """Calculate match confidence percentage"""
        base_confidence = 30  # Lower base confidence

        extracted_lower = extracted_name.lower()

        # HIGH PRIORITY: Exact initial + name match (Б.Номин-Эрдэнэ matches Номин-Эрдэнэ Б)
        if "." in extracted_name:
            initial, name_part = extracted_name.split(".", 1)
            name_part_clean = name_part
            # Remove suffixes (case-insensitive)
            for suffix in ["-д", "-Д", "-г", "-Г", "-аар", "-ААР"]:
                if name_part_clean.endswith(suffix):
                    name_part_clean = name_part_clean[:-len(suffix)]
                    break

            # Try both scenarios:
            # Scenario 1: Initial.FirstName pattern (Б.Номин-Эрдэнэ)
            # Scenario 2: Initial.LastName pattern (Т.ГАНТУЛГА)
            
            first_name_match = False
            last_name_match = False
            
            # Check if the name part matches customer's first name (Scenario 1)
            if hasattr(customer, "first_name") and customer.first_name:
                customer_first_lower = customer.first_name.lower()
                name_part_lower = name_part_clean.lower()

                # PERFECT MATCH: Exact full name match
                if name_part_lower == customer_first_lower:
                    base_confidence += 75  # Increased from 70 for perfect matches
                    first_name_match = True

                    # BONUS: If initial also matches last name
                    if hasattr(customer, "last_name") and customer.last_name:
                        if initial.lower() == customer.last_name.lower()[:1]:
                            base_confidence += 25  # Perfect pattern match

                # GOOD MATCH: Name part is significant portion of customer name
                elif (
                    len(name_part_lower) >= 6
                    and name_part_lower in customer_first_lower
                    and len(name_part_lower) / len(customer_first_lower) >= 0.7
                ):  # At least 70% of the name
                    base_confidence += 20  # Reduced from 25
                    first_name_match = True

                # WEAK MATCH: Just a partial substring (penalize heavily)
                elif name_part_lower in customer_first_lower:
                    base_confidence += 5  # Much lower for partial matches
                    first_name_match = True

            # Check if the name part matches customer's last name (Scenario 2: Т.ГАНТУЛГА)
            if not first_name_match and hasattr(customer, "last_name") and customer.last_name:
                customer_last_lower = customer.last_name.lower()
                name_part_lower = name_part_clean.lower()

                # PERFECT MATCH: Exact last name match
                if name_part_lower == customer_last_lower:
                    base_confidence += 70  # High confidence for last name match
                    last_name_match = True

                    # BONUS: If initial also matches first name
                    if hasattr(customer, "first_name") and customer.first_name:
                        if initial.lower() == customer.first_name.lower()[:1]:
                            base_confidence += 25  # Perfect pattern match

                # GOOD MATCH: Name part is significant portion of last name
                elif (
                    len(name_part_lower) >= 6
                    and name_part_lower in customer_last_lower
                    and len(name_part_lower) / len(customer_last_lower) >= 0.7
                ):
                    base_confidence += 18
                    last_name_match = True

                # WEAK MATCH: Partial last name match
                elif name_part_lower in customer_last_lower:
                    base_confidence += 8
                    last_name_match = True

            # If neither first nor last name matched well, check just initial match
            if not first_name_match and not last_name_match:
                # Check initial against first name
                if hasattr(customer, "first_name") and customer.first_name:
                    if initial.lower() == customer.first_name.lower()[:1]:
                        base_confidence += 15  # Initial matches first name
                # Check initial against last name  
                elif hasattr(customer, "last_name") and customer.last_name:
                    if initial.lower() == customer.last_name.lower()[:1]:
                        base_confidence += 15  # Initial matches last name

        # MEDIUM PRIORITY: Direct name match (without initial)
        else:
            extracted_clean = extracted_lower
            # Remove suffixes (case-insensitive) 
            for suffix in ["-д", "-г", "-аар", "-ээр", "-аас", "-ээс"]:
                if extracted_clean.endswith(suffix):
                    extracted_clean = extracted_clean[:-len(suffix)]
                    break

            # Check for direct first name match
            if hasattr(customer, "first_name") and customer.first_name:
                if extracted_clean == customer.first_name.lower():
                    base_confidence += 50  # Increased from 40 for exact matches
                elif extracted_clean in customer.first_name.lower():
                    base_confidence += 30  # Increased from 25

            # Check for compound name match (like Номин-Эрдэнэ)
            if (
                "-" in extracted_name
                and hasattr(customer, "first_name")
                and customer.first_name
            ):
                if extracted_clean == customer.first_name.lower():
                    base_confidence += 35

        # Loan disbursement context bonus
        if any(
            keyword in bank_description.lower()
            for keyword in ["зээл олгов", "олгох", "зээл"]
        ):
            base_confidence += 10

        # PENALTY: If it's just a partial substring match, reduce confidence
        if len(extracted_name) < 4:
            base_confidence -= 20

        # ADDITIONAL PENALTY: For very common name parts that might match many customers
        common_name_parts = ["эрдэнэ", "баяр", "батыр", "сүрэн", "болд"]
        extracted_lower_clean = (
            extracted_name.lower().replace("-д", "").replace("-г", "")
        )

        # If the extracted name is just a common name part, reduce confidence
        for common_part in common_name_parts:
            if (
                common_part in extracted_lower_clean
                and len(extracted_lower_clean) <= len(common_part) + 3
            ):  # Allow some variation
                base_confidence -= 15  # Penalty for common names
                break
        
        return min(max(base_confidence, 10), 95)  # Cap between 10-95%

    def _find_customers_with_transliteration(self, extracted_name: str) -> List:
        """Find customers using flexible transliteration matching"""
        try:
            from loans_customers.models import Customer
            
            # Clean the extracted name (remove suffixes and dots)
            clean_name = extracted_name
            for suffix in ["-д", "-Д", "-г", "-Г", "-аар", "-ААР"]:
                if clean_name.endswith(suffix):
                    clean_name = clean_name[:-len(suffix)]
                    break
            
            # Handle Initial.Name format
            if "." in clean_name:
                parts = clean_name.split(".")
                if len(parts) == 2:
                    initial, name_part = parts
                    # Try matching the name part with transliteration
                    search_terms = [name_part, initial]
                else:
                    search_terms = [clean_name]
            else:
                search_terms = [clean_name]
            
            matching_customers = []
            
            # Get all customers for flexible matching (limited to avoid performance issues)
            all_customers = Customer.objects.all()[:1000]  # Limit for performance
            
            for customer in all_customers:
                customer_names = [
                    customer.first_name or "",
                    customer.last_name or "",
                    customer.middle_name or ""
                ]
                
                # Check if any search term matches any customer name using transliteration
                for search_term in search_terms:
                    if not search_term or len(search_term) < 2:
                        continue
                        
                    for customer_name in customer_names:
                        if not customer_name:
                            continue
                            
                        # Use transliteration flexible matching
                        if self.transliterator.flexible_match(search_term, customer_name):
                            matching_customers.append(customer)
                            break
                    else:
                        continue
                    break  # Break outer loop if match found
            
            return matching_customers
            
        except Exception as e:
            print(f"Error in transliteration matching: {e}")
            return []

    def _get_customer_display_name(self, customer) -> str:
        """Get the best display name for a customer"""
        first = getattr(customer, "first_name", "") or ""
        middle = getattr(customer, "middle_name", "") or ""
        last = getattr(customer, "last_name", "") or ""

        # Combine available name parts
        name_parts = [first, middle, last]
        full_name = " ".join(part for part in name_parts if part).strip()

        return full_name or f"Customer {customer.id}"

    def _get_all_customer_loans(self, customer) -> List[Dict[str, Any]]:
        """Get all loans for a customer (both applications and active loans) in unified format"""
        loans = []
        
        try:
            # Get loan applications
            loan_items = []
            
            # Add loan applications
            if hasattr(customer, "loan_applications"):
                loan_items.extend([(app, 'application') for app in customer.loan_applications.all()])
            elif hasattr(customer, "loanapplication_set"):
                loan_items.extend([(app, 'application') for app in customer.loanapplication_set.all()])
            
            # Add active loans
            if hasattr(customer, "loan_set"):
                loan_items.extend([(loan, 'loan') for loan in customer.loan_set.all()])

            for loan_item, item_type in loan_items:
                if item_type == 'application':
                    loan_data = {
                        'loan_id': loan_item.id,
                        'loan_number': getattr(loan_item, "application_id", f"APP{loan_item.id}"),
                        'loan_amount': float(
                            getattr(loan_item, "approved_amount", 0)
                            or getattr(loan_item, "requested_amount", 0)
                            or 0
                        ),
                        'loan_type': getattr(
                            getattr(loan_item, "loan_product", None),
                            "name",
                            "personal",
                        ),
                        'status': getattr(loan_item, 'status', 'pending'),
                        'item_type': 'application'
                    }
                else:  # active loan
                    loan_data = {
                        'loan_id': loan_item.id,
                        'loan_number': getattr(loan_item, "loan_number", f"LN{loan_item.id}"),
                        'loan_amount': float(
                            getattr(loan_item, "principal_amount", 0)
                            or getattr(loan_item, "current_balance", 0)
                            or 0
                        ),
                        'loan_type': getattr(
                            getattr(loan_item, "loan_product", None),
                            "name",
                            "personal",
                        ),
                        'status': getattr(loan_item, 'status', 'active'),
                        'item_type': 'loan'
                    }
                
                loans.append(loan_data)
                
        except Exception as e:
            print(f"Error getting customer loans: {e}")
        
        # Deduplicate: Remove loan applications that have corresponding active loans
        # This handles cases where APP20254909 became LN2025253031 (same customer, same amount)
        deduplicated_loans = self._deduplicate_applications_and_active_loans(loans)
        
        return deduplicated_loans

    def _deduplicate_applications_and_active_loans(self, loans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove loan applications that have corresponding active loans with same amount.
        This prevents showing both APP20254909 and LN2025253031 when they're the same loan.
        """
        if not loans:
            return loans
        
        # Separate applications and active loans
        applications = [loan for loan in loans if loan.get('item_type') == 'application']
        active_loans = [loan for loan in loans if loan.get('item_type') == 'loan']
        
        # If no active loans, return all (only applications exist)
        if not active_loans:
            return loans
        
        # Create set of active loan amounts for quick lookup
        active_loan_amounts = {loan.get('loan_amount') for loan in active_loans}
        
        # Filter out applications that match active loan amounts (within $1000 tolerance)
        filtered_applications = []
        for app in applications:
            app_amount = app.get('loan_amount', 0)
            # Check if this application amount matches any active loan
            has_matching_active = any(
                abs(app_amount - active_amount) < 1000 
                for active_amount in active_loan_amounts
            )
            
            if not has_matching_active:
                # Keep this application (no matching active loan found)
                filtered_applications.append(app)
        
        # Return active loans + non-matching applications
        result = active_loans + filtered_applications
        
        # Sort by status priority: active first, then pending
        result.sort(key=lambda x: (
            0 if x.get('item_type') == 'loan' else 1,  # Active loans first
            -x.get('loan_amount', 0)  # Then by amount (largest first)
        ))
        
        return result
