"""
Smart Suggestion Service

Comprehensive service that integrates all smart matching engines to provide
ranked suggestions with match percentages for bank transaction processing.
"""

from typing import List, Dict, Optional
from datetime import datetime

# Import our modular smart matching engines
from reconciliation.smart_matching.engines.license_plate_engine import (
    LicensePlateEngine,
)
from reconciliation.smart_matching.engines.phone_priority_engine import (
    PhonePriorityEngine,
)
from reconciliation.smart_matching.engines.id_priority_engine import IDPriorityEngine
from reconciliation.smart_matching.engines.mongolian_name_engine import (
    MongolianNameEngine,
)
from reconciliation.smart_matching.confidence_calculator import ConfidenceCalculator


class SmartSuggestionService:
    """
    Central service for generating smart suggestions with match percentages
    """

    def __init__(self):
        # Initialize all engines
        self.engines = {
            "license_plate": LicensePlateEngine(),
            "phone_priority": PhonePriorityEngine(),
            "id_priority": IDPriorityEngine(),
            "mongolian_name": MongolianNameEngine(),
        }

        # Initialize confidence calculator
        self.confidence_calculator = ConfidenceCalculator()

        # Service metadata
        self.service_name = "Smart Suggestion Service"
        self.version = "1.0.0"

        # Suggestion cache for performance
        self.suggestion_cache = {}
        self.cache_expiry_minutes = 30

    def get_suggestions(
        self, bank_description: str, amount: float, transaction_type: str = "auto"
    ) -> List[Dict]:
        """
        Get ranked suggestions with match percentages for a bank transaction

        Args:
            bank_description: Bank transaction description
            amount: Transaction amount
            transaction_type: Type of transaction (auto, disbursement, payment)

        Returns:
            List of suggestions with match percentages, ranked by confidence
        """
        # Create cache key
        cache_key = f"{bank_description}_{amount}_{transaction_type}"

        # Check cache first
        cached_result = self._get_cached_suggestion(cache_key)
        if cached_result:
            return cached_result

        # Collect suggestions from all engines
        all_suggestions = {}

        for engine_name, engine in self.engines.items():
            try:
                engine_suggestions = engine.detect_loans(bank_description, amount)
                if engine_suggestions:
                    all_suggestions[engine_name] = engine_suggestions
            except Exception as e:
                print(f"Warning: {engine_name} engine error: {e}")
                continue

        # Calculate ensemble confidence and ranking
        ensemble_result = self.confidence_calculator.calculate_ensemble_confidence(
            all_suggestions
        )

        # Process and rank suggestions
        ranked_suggestions = self._process_and_rank_suggestions(
            all_suggestions, ensemble_result, bank_description, amount
        )

        # Cache the result
        self._cache_suggestion(cache_key, ranked_suggestions)

        return ranked_suggestions

    def _process_and_rank_suggestions(
        self,
        all_suggestions: Dict,
        ensemble_result: Dict,
        description: str,
        amount: float,
    ) -> List[Dict]:
        """Process and rank all suggestions with enhanced metadata"""

        processed_suggestions = []

        for engine_name, suggestions in all_suggestions.items():
            for suggestion in suggestions:
                # Add engine name to suggestion for confidence calculation
                suggestion_with_engine = suggestion.copy()
                suggestion_with_engine["engine"] = self._get_engine_display_name(
                    engine_name
                )

                # Calculate weighted confidence
                weighted_suggestions = (
                    self.confidence_calculator.calculate_weighted_confidence(
                        [suggestion_with_engine]
                    )
                )
                weighted_suggestion = (
                    weighted_suggestions[0]
                    if weighted_suggestions
                    else suggestion_with_engine
                )

                # Enhance suggestion with UI-friendly data
                enhanced_suggestion = self._enhance_suggestion_for_ui(
                    weighted_suggestion, engine_name, description, amount
                )

                processed_suggestions.append(enhanced_suggestion)

        # Deduplicate suggestions by customer - keep highest confidence
        deduplicated_suggestions = self._deduplicate_by_customer(processed_suggestions)

        # Sort by confidence descending
        ranked_suggestions = sorted(
            deduplicated_suggestions, key=lambda x: x["match_percentage"], reverse=True
        )

        # Add ranking metadata
        for i, suggestion in enumerate(ranked_suggestions):
            suggestion["rank"] = i + 1
            suggestion["is_top_suggestion"] = i == 0
            suggestion["confidence_tier"] = self._get_confidence_tier(
                suggestion["match_percentage"]
            )

        # Add ensemble metadata to top suggestion
        if ranked_suggestions and ensemble_result:
            ranked_suggestions[0]["ensemble_info"] = {
                "consensus": ensemble_result.get("consensus", False),
                "participating_engines": ensemble_result.get(
                    "participating_engines", []
                ),
                "total_suggestions": ensemble_result.get("total_suggestions", 0),
            }

        return ranked_suggestions[:10]  # Return top 10 suggestions

    def _enhance_suggestion_for_ui(
        self, suggestion: Dict, engine_name: str, description: str, amount: float
    ) -> Dict:
        """Enhance suggestion with UI-friendly metadata"""

        # Get match percentage (confidence)
        match_percentage = suggestion.get("confidence", 0)

        # Create user-friendly display
        enhanced = {
            # Core suggestion data
            "loan_id": suggestion.get("loan_id"),
            "loan_number": suggestion.get("loan_number", "N/A"),
            "customer_id": suggestion.get("customer_id"),
            "customer_name": suggestion.get("customer_name", "Unknown"),
            "loan_amount": suggestion.get("loan_amount", 0),
            "loan_type": suggestion.get("loan_type", "Unknown"),
            # Match information
            "match_percentage": match_percentage,
            "matched_data": suggestion.get("matched_data", ""),
            "matching_method": suggestion.get("method", "unknown"),
            "engine_name": engine_name,
            "engine_display_name": self._get_engine_display_name(engine_name),
            # UI display helpers
            "percentage_display": f"{match_percentage}%",
            "confidence_color": self._get_confidence_color(match_percentage),
            "confidence_icon": self._get_confidence_icon(match_percentage),
            "match_reason": suggestion.get("reason", "Pattern matched"),
            # Additional metadata
            "related_account": suggestion.get("related_account"),
            "gl_account_suggestion": suggestion.get("gl_account_suggestion"),
            "transaction_amount": amount,
            "original_description": description,
            # Timestamps
            "suggested_at": datetime.now().isoformat(),
            "suggestion_id": f"{engine_name}_{hash(str(suggestion))}",
            # Raw data for debugging
            "raw_suggestion": suggestion if hasattr(self, "debug_mode") else None,
        }

        return enhanced

    def _get_engine_display_name(self, engine_name: str) -> str:
        """Get user-friendly engine names"""
        display_names = {
            "license_plate": "License Plate Engine",
            "phone_priority": "Phone Priority Engine",
            "id_priority": "ID Priority Engine",
            "mongolian_name": "Mongolian Name Engine",
            "loan_disbursement": "Loan Pattern Analyzer",
            "recurring_pattern": "Historical Pattern Matcher",
        }
        return display_names.get(engine_name, engine_name.title())

    def _get_confidence_tier(self, percentage: float) -> str:
        """Get confidence tier for UI styling"""
        if percentage >= 85:
            return "high"
        elif percentage >= 70:
            return "medium"
        elif percentage >= 50:
            return "low"
        else:
            return "very_low"

    def _get_confidence_color(self, percentage: float) -> str:
        """Get color code for confidence percentage"""
        if percentage >= 85:
            return "#28a745"  # Green
        elif percentage >= 70:
            return "#ffc107"  # Yellow
        elif percentage >= 50:
            return "#fd7e14"  # Orange
        else:
            return "#dc3545"  # Red

    def _get_confidence_icon(self, percentage: float) -> str:
        """Get icon for confidence level"""
        if percentage >= 85:
            return "🎯"  # High confidence
        elif percentage >= 70:
            return "✅"  # Good confidence
        elif percentage >= 50:
            return "⚠️"  # Medium confidence
        else:
            return "❓"  # Low confidence

    def get_suggestion_details(self, suggestion_id: str) -> Optional[Dict]:
        """Get detailed information about a specific suggestion"""
        # Search through cache for the suggestion
        for cached_suggestions in self.suggestion_cache.values():
            if isinstance(cached_suggestions, list):
                for suggestion in cached_suggestions:
                    if suggestion.get("suggestion_id") == suggestion_id:
                        return self._get_detailed_suggestion_info(suggestion)

        return None

    def _get_detailed_suggestion_info(self, suggestion: Dict) -> Dict:
        """Get comprehensive details about a suggestion"""
        return {
            "suggestion": suggestion,
            "engine_info": self._get_engine_info(suggestion.get("engine_name")),
            "confidence_breakdown": self._get_confidence_breakdown(suggestion),
            "similar_patterns": self._get_similar_patterns(suggestion),
            "historical_accuracy": self._get_historical_accuracy(
                suggestion.get("engine_name")
            ),
        }

    def _get_engine_info(self, engine_name: str) -> Dict:
        """Get information about the engine that made the suggestion"""
        if engine_name in self.engines:
            return self.engines[engine_name].get_engine_info()
        return {}

    def _get_confidence_breakdown(self, suggestion: Dict) -> Dict:
        """Get detailed confidence calculation breakdown"""
        return {
            "base_confidence": suggestion.get("confidence", 0),
            "engine_weight": suggestion.get("engine_weight", 1.0),
            "method_bonus": suggestion.get("method_bonus", 0),
            "data_quality_factor": suggestion.get("data_quality_factor", 1.0),
            "final_percentage": suggestion.get("match_percentage", 0),
        }

    def _get_similar_patterns(self, suggestion: Dict) -> List[str]:
        """Get similar patterns that might also match"""
        # This would typically query the recurring pattern engine
        return []  # Placeholder for now

    def _get_historical_accuracy(self, engine_name: str) -> Dict:
        """Get historical accuracy data for the engine"""
        stats = self.confidence_calculator.get_engine_performance_stats()
        return stats.get(engine_name, {})

    def provide_feedback(
        self,
        suggestion_id: str,
        was_correct: bool,
        actual_loan_id: Optional[str] = None,
    ) -> Dict:
        """Provide feedback on suggestion accuracy for learning"""

        suggestion = self.get_suggestion_details(suggestion_id)
        if not suggestion:
            return {"success": False, "error": "Suggestion not found"}

        # Get the base suggestion data
        base_suggestion = suggestion["suggestion"]

        # Provide feedback to confidence calculator
        calibration_result = self.confidence_calculator.calibrate_confidence(
            base_suggestion, was_correct
        )

        # Store feedback result
        feedback_record = {
            "suggestion_id": suggestion_id,
            "was_correct": was_correct,
            "actual_loan_id": actual_loan_id,
            "predicted_percentage": base_suggestion.get("match_percentage", 0),
            "engine_name": base_suggestion.get("engine_name"),
            "feedback_timestamp": datetime.now().isoformat(),
            "calibration_result": calibration_result,
        }

        return {
            "success": True,
            "feedback_recorded": feedback_record,
            "calibration_adjustment": calibration_result.get(
                "calibration_adjustment", 0
            ),
        }

    def get_quick_suggestions(
        self, partial_description: str, limit: int = 5
    ) -> List[Dict]:
        """Get quick suggestions for auto-complete as user types"""
        if len(partial_description) < 3:
            return []

        # Use all available engines for quick matches
        try:
            # Get suggestions from all engines
            all_suggestions = []
            
            for engine_name, engine in self.engines.items():
                try:
                    suggestions = engine.detect_loans(
                        partial_description, 0
                    )  # Amount not important for quick suggestions
                    
                    # Ensure we have a list
                    if not isinstance(suggestions, list):
                        suggestions = []
                    
                    # Add engine info to each suggestion
                    for suggestion in suggestions:
                        if isinstance(suggestion, dict):
                            suggestion["engine_name"] = engine_name
                            suggestion["engine_display_name"] = self._get_engine_display_name(engine_name)
                    
                    all_suggestions.extend(suggestions)
                except Exception as e:
                    # Continue with other engines if one fails
                    print(f"Quick suggestion error from {engine_name}: {e}")
                    continue

            # Deduplicate and sort by confidence
            deduplicated = self._deduplicate_by_customer(all_suggestions)
            
            # Ensure deduplicated is a list
            if not isinstance(deduplicated, list):
                deduplicated = []
            
            deduplicated.sort(key=lambda x: x.get("confidence", 0), reverse=True)

            # Format for quick display
            quick_suggestions = []
            for suggestion in deduplicated[:limit]:
                quick_suggestions.append(
                    {
                        "display_text": suggestion.get("customer_name", "Unknown"),
                        "match_percentage": suggestion.get("confidence", 0),
                        "matched_pattern": suggestion.get("matched_data", ""),
                        "suggestion_preview": f"{suggestion.get('customer_name', 'Unknown')} ({suggestion.get('confidence', 0)}%)",
                    }
                )

            return quick_suggestions

        except Exception as e:
            print(f"Quick suggestions error: {e}")
            return []

    def _get_cached_suggestion(self, cache_key: str) -> Optional[List[Dict]]:
        """Get suggestion from cache if still valid"""
        if cache_key in self.suggestion_cache:
            cache_entry = self.suggestion_cache[cache_key]
            cache_time = datetime.fromisoformat(cache_entry["timestamp"])

            # Check if cache is still valid (within expiry time)
            time_diff = datetime.now() - cache_time
            if time_diff.total_seconds() < (self.cache_expiry_minutes * 60):
                return cache_entry["suggestions"]

        return None

    def _cache_suggestion(self, cache_key: str, suggestions: List[Dict]):
        """Cache suggestions for performance"""
        self.suggestion_cache[cache_key] = {
            "suggestions": suggestions,
            "timestamp": datetime.now().isoformat(),
        }

        # Clean old cache entries if cache gets too large
        if len(self.suggestion_cache) > 1000:
            # Remove oldest 100 entries
            sorted_keys = sorted(
                self.suggestion_cache.keys(),
                key=lambda k: self.suggestion_cache[k]["timestamp"],
            )
            for key in sorted_keys[:100]:
                del self.suggestion_cache[key]

    def _deduplicate_by_customer(self, suggestions: List[Dict]) -> List[Dict]:
        """
        Group suggestions by customer and loan, keeping multiple loans per customer
        Enhanced to show: "Customer Name - Loan X ($Amount)"
        """
        # Group by customer_id and loan_id to avoid true duplicates
        unique_suggestions = {}
        customer_loan_counts = {}

        for suggestion in suggestions:
            customer_id = suggestion.get("customer_id")
            loan_id = suggestion.get("loan_id")
            
            if not customer_id or not loan_id:
                continue

            # Create unique key for customer + loan combination
            unique_key = f"{customer_id}_{loan_id}"
            
            # Track how many loans each customer has
            if customer_id not in customer_loan_counts:
                customer_loan_counts[customer_id] = set()
            customer_loan_counts[customer_id].add(loan_id)

            current_confidence = suggestion.get("match_percentage", 0)

            if unique_key not in unique_suggestions:
                unique_suggestions[unique_key] = suggestion
            else:
                # Keep higher confidence suggestion for same customer+loan
                existing_confidence = unique_suggestions[unique_key].get("match_percentage", 0)
                if current_confidence > existing_confidence:
                    unique_suggestions[unique_key] = suggestion

        # Enhance customer names for customers with multiple loans
        enhanced_suggestions = []
        
        for suggestion in unique_suggestions.values():
            customer_id = suggestion.get("customer_id")
            loan_count = len(customer_loan_counts.get(customer_id, set()))
            
            # Create enhanced suggestion with loan-specific naming
            enhanced_suggestion = suggestion.copy()
            
            if loan_count > 1:
                # Multiple loans: enhance name with loan identifier
                customer_name = suggestion.get("customer_name", "Unknown Customer")
                loan_amount = suggestion.get("loan_amount", 0)
                loan_number = suggestion.get("loan_number", "")
                
                # Create loan identifier (extract number from loan number)
                loan_identifier = self._extract_loan_identifier(loan_number)
                
                # Format: "Customer Name - Loan X ($Amount)"
                if loan_amount > 0:
                    enhanced_name = f"{customer_name} - Loan {loan_identifier} (${loan_amount:,.0f})"
                else:
                    enhanced_name = f"{customer_name} - Loan {loan_identifier}"
                
                enhanced_suggestion["customer_name"] = enhanced_name
                enhanced_suggestion["is_multi_loan_customer"] = True
                enhanced_suggestion["loan_identifier"] = loan_identifier
            else:
                # Single loan: keep original name but add amount for clarity
                customer_name = suggestion.get("customer_name", "Unknown Customer")
                loan_amount = suggestion.get("loan_amount", 0)
                
                if loan_amount > 0:
                    enhanced_name = f"{customer_name} (${loan_amount:,.0f})"
                    enhanced_suggestion["customer_name"] = enhanced_name
                
                enhanced_suggestion["is_multi_loan_customer"] = False
            
            enhanced_suggestions.append(enhanced_suggestion)

        return enhanced_suggestions
    
    def _extract_loan_identifier(self, loan_number: str) -> str:
        """Extract a clean identifier from loan number for display"""
        if not loan_number:
            return "Unknown"
        
        # Extract meaningful part from loan number
        # Examples: "LN2025998342" -> "998342", "APP20258679" -> "258679"
        import re
        
        # Try to extract last 6 digits
        numbers = re.findall(r'\d+', loan_number)
        if numbers:
            # Use last 6 digits of the longest number found
            longest_number = max(numbers, key=len)
            if len(longest_number) >= 6:
                return longest_number[-6:]
            else:
                return longest_number
        
        # Fallback: use last part after last letter/symbol
        parts = re.split(r'[A-Za-z]+', loan_number)
        if len(parts) > 1 and parts[-1]:
            return parts[-1]
        
        return loan_number

    def get_service_statistics(self) -> Dict:
        """Get service usage and performance statistics"""
        return {
            "service_name": self.service_name,
            "version": self.version,
            "active_engines": len(self.engines),
            "cache_size": len(self.suggestion_cache),
            "engine_status": {name: "active" for name in self.engines.keys()},
            "confidence_calculator_stats": self.confidence_calculator.get_engine_performance_stats(),
            "last_suggestion_time": (
                max([entry["timestamp"] for entry in self.suggestion_cache.values()])
                if self.suggestion_cache
                else None
            ),
        }

    def clear_cache(self):
        """Clear suggestion cache"""
        self.suggestion_cache.clear()
        return {"cache_cleared": True, "timestamp": datetime.now().isoformat()}

    def enable_debug_mode(self):
        """Enable debug mode to include raw suggestion data"""
        self.debug_mode = True

    def disable_debug_mode(self):
        """Disable debug mode"""
        self.debug_mode = False
