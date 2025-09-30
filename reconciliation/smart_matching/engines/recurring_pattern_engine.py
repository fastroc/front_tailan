"""
Recurring Pattern Engine

Smart matching engine that learns from Excel data and applies recurring patterns.
Uses the established Excel column H (related account) patterns for matching.
"""

import re
from typing import List, Dict, Optional
from collections import defaultdict
from datetime import datetime
from ..base_engine import SmartMatchingEngine


class RecurringPatternEngine(SmartMatchingEngine):
    """Learns from Excel data and applies recurring patterns"""
    
    def __init__(self):
        super().__init__()
        self.engine_name = "Recurring Pattern Engine"
        self.version = "1.0.0"
        self.pattern_library = {}  # Description -> Account mapping
        self.confidence_scores = {}  # Pattern -> confidence mapping
        self.usage_count = defaultdict(int)  # Track pattern usage
        
        # Load patterns from Excel data
        self._load_patterns_from_database()
    
    def detect_loans(self, bank_description: str, amount: float) -> List[Dict]:
        """Detect loans using learned recurring patterns"""
        suggestions = []
        
        # Check for exact pattern matches first
        exact_match = self._find_exact_pattern_match(bank_description)
        if exact_match:
            suggestions.append(exact_match)
        
        # Check for partial pattern matches
        partial_matches = self._find_partial_pattern_matches(bank_description)
        suggestions.extend(partial_matches)
        
        return suggestions
    
    def _load_patterns_from_database(self):
        """Load recurring patterns from existing bank transactions with related_account data"""
        try:
            from bank_accounts.models import BankTransaction
            
            # Check if the table and columns exist before querying
            try:
                # Try a simple query first to check if fields exist
                BankTransaction.objects.first()
            except Exception as e:
                if "column" in str(e) and "does not exist" in str(e):
                    self._log_info("Database not ready yet - skipping pattern loading")
                    return
                else:
                    raise e
            
            # Get transactions that have related_account data (from Excel import)
            transactions = BankTransaction.objects.filter(
                related_account__isnull=False
            ).exclude(related_account="").exclude(related_account="-")
            
            pattern_frequency = defaultdict(int)
            pattern_accounts = defaultdict(set)
            
            for transaction in transactions:
                description = transaction.description.strip()
                related_account = transaction.related_account.strip()
                
                if description and related_account:
                    # Store exact pattern
                    self.pattern_library[description] = related_account
                    pattern_frequency[description] += 1
                    pattern_accounts[description].add(related_account)
                    
                    # Create variations for partial matching
                    self._create_pattern_variations(description, related_account)
            
            # Calculate confidence scores based on frequency and consistency
            self._calculate_pattern_confidence(pattern_frequency, pattern_accounts)
            
            self._log_info(f"Loaded {len(self.pattern_library)} patterns from database")
            
        except Exception as e:
            self._log_error(f"Failed to load patterns: {e}")
            # Continue without patterns rather than failing completely
    
    def _create_pattern_variations(self, description: str, related_account: str):
        """Create pattern variations for fuzzy matching"""
        # Create shorter patterns for partial matching
        words = description.split()
        
        # Store patterns of different lengths
        for i in range(2, len(words) + 1):
            partial_desc = " ".join(words[:i])
            if len(partial_desc) > 10:  # Only meaningful patterns
                pattern_key = f"partial_{partial_desc}"
                if pattern_key not in self.pattern_library:
                    self.pattern_library[pattern_key] = related_account
    
    def _calculate_pattern_confidence(self, frequency: dict, accounts: dict):
        """Calculate confidence scores for patterns"""
        for pattern, freq in frequency.items():
            account_consistency = len(accounts[pattern]) == 1  # Only one account used
            
            # Base confidence from frequency
            if freq >= 5:
                base_confidence = 95
            elif freq >= 3:
                base_confidence = 85
            elif freq >= 2:
                base_confidence = 75
            else:
                base_confidence = 60
            
            # Boost for consistency
            if account_consistency:
                base_confidence += 10
            else:
                base_confidence -= 20  # Multiple accounts for same pattern
            
            self.confidence_scores[pattern] = min(base_confidence, 99)
    
    def _find_exact_pattern_match(self, description: str) -> Optional[Dict]:
        """Find exact pattern match"""
        description = description.strip()
        
        if description in self.pattern_library:
            related_account = self.pattern_library[description]
            confidence = self.confidence_scores.get(description, 80)
            
            # Track usage
            self.usage_count[description] += 1
            
            return {
                'loan_id': None,  # Pattern-based, not specific loan
                'loan_number': 'N/A',
                'customer_id': None,
                'customer_name': self._extract_customer_from_description(description),
                'confidence': confidence,
                'method': 'recurring_pattern_exact',
                'matched_data': description,
                'loan_amount': 0,  # Not available from pattern
                'loan_type': 'pattern_based',
                'reason': "Exact recurring pattern match",
                'related_account': related_account,
                'pattern_frequency': self.usage_count[description],
                'engine': self.engine_name
            }
        
        return None
    
    def _find_partial_pattern_matches(self, description: str) -> List[Dict]:
        """Find partial pattern matches"""
        suggestions = []
        description_clean = description.strip().lower()
        
        # Look for partial matches
        for pattern, related_account in self.pattern_library.items():
            if pattern.startswith('partial_'):
                pattern_text = pattern.replace('partial_', '').lower()
                
                # Check if pattern text is contained in description
                if pattern_text in description_clean and len(pattern_text) > 10:
                    confidence = max(self.confidence_scores.get(pattern, 60) - 15, 45)  # Lower confidence for partial
                    
                    suggestion = {
                        'loan_id': None,
                        'loan_number': 'N/A',
                        'customer_id': None,
                        'customer_name': self._extract_customer_from_description(description),
                        'confidence': confidence,
                        'method': 'recurring_pattern_partial',
                        'matched_data': pattern_text,
                        'loan_amount': 0,
                        'loan_type': 'pattern_based',
                        'reason': f"Partial recurring pattern match: {pattern_text}",
                        'related_account': related_account,
                        'pattern_type': 'partial',
                        'engine': self.engine_name
                    }
                    suggestions.append(suggestion)
                    
                    # Only return best partial match
                    break
        
        return suggestions
    
    def _extract_customer_from_description(self, description: str) -> str:
        """Extract customer name from description patterns"""
        # Common patterns for customer names
        patterns = [
            r'EB-([^-]+)-д',           # EB-CustomerName-д
            r'([А-Яа-я]+\s+[А-Яа-я]+)', # Two Cyrillic words
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)', # Two capitalized words
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description)
            if match:
                return match.group(1).strip()
        
        return "Pattern Customer"
    
    def learn_new_pattern(self, description: str, related_account: str):
        """Learn a new pattern from user input"""
        description = description.strip()
        related_account = related_account.strip()
        
        if description and related_account:
            self.pattern_library[description] = related_account
            self.confidence_scores[description] = 70  # New patterns start with medium confidence
            self.usage_count[description] = 1
            
            # Create variations
            self._create_pattern_variations(description, related_account)
            
            self._log_info(f"Learned new pattern: {description[:30]}... -> {related_account}")
    
    def get_pattern_statistics(self) -> Dict:
        """Get statistics about learned patterns"""
        total_patterns = len(self.pattern_library)
        exact_patterns = len([p for p in self.pattern_library.keys() if not p.startswith('partial_')])
        partial_patterns = total_patterns - exact_patterns
        
        confidence_distribution = {
            'high_confidence': len([c for c in self.confidence_scores.values() if c >= 80]),
            'medium_confidence': len([c for c in self.confidence_scores.values() if 60 <= c < 80]),
            'low_confidence': len([c for c in self.confidence_scores.values() if c < 60])
        }
        
        most_used_patterns = sorted(
            self.usage_count.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        return {
            'total_patterns': total_patterns,
            'exact_patterns': exact_patterns,
            'partial_patterns': partial_patterns,
            'confidence_distribution': confidence_distribution,
            'most_used_patterns': most_used_patterns,
            'average_confidence': sum(self.confidence_scores.values()) / len(self.confidence_scores) if self.confidence_scores else 0
        }
    
    def get_pattern_details(self, description: str) -> Dict:
        """Get detailed information about patterns for a description"""
        exact_match = description in self.pattern_library
        partial_matches = []
        
        description_lower = description.lower()
        for pattern in self.pattern_library.keys():
            if pattern.startswith('partial_'):
                pattern_text = pattern.replace('partial_', '').lower()
                if pattern_text in description_lower:
                    partial_matches.append(pattern_text)
        
        return {
            'description': description,
            'has_exact_match': exact_match,
            'exact_account': self.pattern_library.get(description),
            'exact_confidence': self.confidence_scores.get(description),
            'partial_matches': partial_matches[:3],  # Top 3 partial matches
            'total_patterns_available': len(self.pattern_library)
        }
    
    def export_patterns(self) -> Dict:
        """Export patterns for backup or analysis"""
        return {
            'patterns': dict(self.pattern_library),
            'confidence_scores': dict(self.confidence_scores),
            'usage_count': dict(self.usage_count),
            'export_timestamp': str(datetime.now()),
            'total_patterns': len(self.pattern_library)
        }
    
    def import_patterns(self, pattern_data: Dict):
        """Import patterns from external source"""
        if 'patterns' in pattern_data:
            self.pattern_library.update(pattern_data['patterns'])
        
        if 'confidence_scores' in pattern_data:
            self.confidence_scores.update(pattern_data['confidence_scores'])
        
        if 'usage_count' in pattern_data:
            for k, v in pattern_data['usage_count'].items():
                self.usage_count[k] += v
        
        self._log_info(f"Imported {len(pattern_data.get('patterns', {}))} patterns")
    
    def get_engine_info(self) -> Dict:
        """Get engine information and capabilities"""
        stats = self.get_pattern_statistics()
        
        return {
            'name': self.engine_name,
            'version': self.version,
            'description': 'Learns from Excel data and applies recurring patterns',
            'total_patterns': stats['total_patterns'],
            'pattern_sources': ['Database transactions', 'Excel imports', 'User learning'],
            'capabilities': [
                'Exact pattern matching',
                'Partial pattern matching', 
                'Pattern learning from user input',
                'Confidence scoring based on frequency',
                'Pattern variation generation'
            ],
            'confidence_range': '45-99%',
            'independent': True,
            'debuggable': True,
            'removable': True,
            'learning_enabled': True
        }
    
    def _log_error(self, message: str):
        """Log engine-specific errors"""
        print(f"❌ {self.engine_name} Error: {message}")
    
    def _log_info(self, message: str):
        """Log engine-specific information"""
        print(f"ℹ️ {self.engine_name}: {message}")
    
    def run_self_test(self) -> Dict:
        """Run self-test to verify engine functionality"""
        # Test with some patterns we should have loaded
        test_descriptions = [
            "EB-зээл олгов Б.Очмаа",
            "EB-200000000371",
            "6045УАМ 88980800"
        ]
        
        results = {
            'engine': self.engine_name,
            'patterns_loaded': len(self.pattern_library),
            'test_cases': len(test_descriptions),
            'exact_matches': 0,
            'partial_matches': 0,
            'status': 'unknown'
        }
        
        for desc in test_descriptions:
            exact = self._find_exact_pattern_match(desc)
            partial = self._find_partial_pattern_matches(desc)
            
            if exact:
                results['exact_matches'] += 1
            if partial:
                results['partial_matches'] += 1
        
        total_matches = results['exact_matches'] + results['partial_matches']
        results['match_rate'] = (total_matches / len(test_descriptions)) * 100 if test_descriptions else 0
        results['status'] = 'PASS' if results['match_rate'] >= 50 and results['patterns_loaded'] > 0 else 'FAIL'
        
        return results
