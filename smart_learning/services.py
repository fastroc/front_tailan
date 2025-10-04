"""
🧠 SMART LEARNING SERVICES
AI Pattern Matching & Confidence Calculation Engine
"""

from django.db.models import Q, Count
import re
from difflib import SequenceMatcher
from .models import MatchPattern, TransactionMatchHistory, MatchFeedback


class PatternMatcher:
    """
    AI Pattern Matching Service
    Learns from historical transaction matches and suggests WHO/WHAT mappings
    """
    
    def __init__(self, company=None):
        self.company = company
        self.min_confidence = 30.0  # Minimum confidence to suggest (adjustable)
        self.auto_apply_threshold = 90.0  # Auto-apply suggestions above this confidence
    
    def get_smart_suggestions(self, transaction_description, amount, trans_type):
        """
        Get AI-powered suggestions based on learned patterns
        
        Args:
            transaction_description: Text description from bank statement
            amount: Transaction amount (positive number)
            trans_type: 'debit' or 'credit'
        
        Returns:
            List of suggestions sorted by confidence (highest first):
            [
                {
                    'source': 'pattern',
                    'confidence': 85.5,
                    'who': 'Customer Name',
                    'what': ChartOfAccount object,
                    'pattern_id': 123,
                    'pattern_name': 'Khan Bank Fee Pattern',
                    'auto_apply': False,
                    'accuracy_history': 87.5,
                    'times_used': 15,
                },
                ...
            ]
        """
        suggestions = []
        
        # Get all active patterns (optionally filtered by company)
        patterns_query = MatchPattern.objects.filter(is_active=True)
        if self.company:
            patterns_query = patterns_query.filter(
                Q(company=self.company) | Q(company__isnull=True)
            )
        
        patterns = patterns_query.select_related('suggested_what')
        
        for pattern in patterns:
            # Calculate match score for this pattern
            score = self._calculate_pattern_match_score(
                pattern, 
                transaction_description, 
                amount, 
                trans_type
            )
            
            # Only include if meets minimum confidence
            if score >= self.min_confidence:
                suggestions.append({
                    'source': 'pattern',
                    'confidence': score,
                    'who': pattern.suggested_who,
                    'what': pattern.suggested_what,
                    'pattern_id': pattern.id,
                    'pattern_name': pattern.pattern_name,
                    'auto_apply': score >= self.auto_apply_threshold and pattern.auto_apply,
                    'accuracy_history': pattern.accuracy_rate,
                    'times_used': pattern.times_seen,
                })
        
        # Sort by confidence (highest first)
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        
        return suggestions
    
    def _calculate_pattern_match_score(self, pattern, description, amount, trans_type):
        """
        Calculate how well a pattern matches the transaction
        
        Returns:
            Confidence score 0-100
        """
        score = 0.0
        
        # 1. Description matching (60% weight) - Most important
        description_score = self._match_description(pattern, description)
        score += description_score * 0.6
        
        # 2. Amount matching (20% weight)
        amount_score = self._match_amount(pattern, amount)
        score += amount_score * 0.2
        
        # 3. Transaction type matching (10% weight)
        type_score = self._match_type(pattern, trans_type)
        score += type_score * 0.1
        
        # 4. Historical accuracy (10% weight) - Pattern's track record
        history_score = pattern.accuracy_rate
        score += history_score * 0.1
        
        # Adjust final score based on pattern confidence
        # A pattern with low confidence shouldn't score too high
        score = score * (pattern.confidence / 100.0)
        
        return round(score, 2)
    
    def _match_description(self, pattern, description):
        """
        Match transaction description against pattern
        
        Returns:
            Score 0-100 based on match quality
        """
        desc_lower = description.lower().strip()
        pattern_lower = pattern.description_pattern.lower().strip()
        
        if pattern.pattern_type == 'exact':
            # Exact match required
            return 100.0 if desc_lower == pattern_lower else 0.0
        
        elif pattern.pattern_type == 'contains':
            # Check if pattern is contained in description
            return 100.0 if pattern_lower in desc_lower else 0.0
        
        elif pattern.pattern_type == 'regex':
            # Regular expression matching
            try:
                if re.search(pattern_lower, desc_lower, re.IGNORECASE):
                    return 100.0
            except re.error:
                # Invalid regex, treat as contains
                return 100.0 if pattern_lower in desc_lower else 0.0
            return 0.0
        
        elif pattern.pattern_type == 'fuzzy':
            # Fuzzy matching using SequenceMatcher
            # Returns similarity ratio 0.0-1.0
            ratio = SequenceMatcher(None, desc_lower, pattern_lower).ratio()
            return ratio * 100.0
        
        elif pattern.pattern_type == 'ml':
            # Placeholder for future ML models
            # For now, use fuzzy matching
            ratio = SequenceMatcher(None, desc_lower, pattern_lower).ratio()
            return ratio * 100.0
        
        # Default: no match
        return 0.0
    
    def _match_amount(self, pattern, amount):
        """
        Check if transaction amount falls within pattern's amount range
        
        Returns:
            100.0 if match, 0.0 if no match
        """
        # If no amount constraints, always match
        if pattern.amount_min is None and pattern.amount_max is None:
            return 100.0
        
        # Check minimum constraint
        if pattern.amount_min and amount < pattern.amount_min:
            return 0.0
        
        # Check maximum constraint
        if pattern.amount_max and amount > pattern.amount_max:
            return 0.0
        
        # Amount is within range
        return 100.0
    
    def _match_type(self, pattern, trans_type):
        """
        Check if transaction type matches pattern
        
        Returns:
            100.0 if match, 0.0 if no match
        """
        # If no type constraint, always match
        if not pattern.transaction_type:
            return 100.0
        
        # Check if types match
        return 100.0 if pattern.transaction_type == trans_type else 0.0
    
    def log_match(self, transaction_data, matched_data, user, source='manual'):
        """
        Log a transaction match for learning purposes
        
        Args:
            transaction_data: dict with keys: date, description, amount, type
            matched_data: dict with keys: who, what, confidence (optional), bank_rule (optional), match_pattern (optional)
            user: User object who made the match
            source: 'manual', 'rule', 'pattern', or 'hybrid'
        
        Returns:
            TransactionMatchHistory object
        """
        match_history = TransactionMatchHistory.objects.create(
            transaction_date=transaction_data['date'],
            transaction_description=transaction_data['description'],
            transaction_amount=transaction_data['amount'],
            transaction_type=transaction_data['type'],
            matched_who=matched_data['who'],
            matched_what=matched_data['what'],
            match_source=source,
            bank_rule=matched_data.get('bank_rule'),
            match_pattern=matched_data.get('match_pattern'),
            confidence_score=matched_data.get('confidence', 0.0),
            matched_by=user,
            company=self.company,
        )
        
        return match_history
    
    def record_feedback(self, transaction_match_history, suggestion_data, action, actual_data=None):
        """
        Record user feedback on a suggestion (for continuous learning)
        
        Args:
            transaction_match_history: TransactionMatchHistory object
            suggestion_data: dict with: who, what, source, confidence, pattern_id (if applicable)
            action: 'accepted', 'modified', or 'rejected'
            actual_data: dict with: who, what (if user modified the suggestion)
        
        Returns:
            MatchFeedback object
        """
        # Create feedback record
        feedback = MatchFeedback.objects.create(
            match_history=transaction_match_history,
            suggested_who=suggestion_data['who'],
            suggested_what=suggestion_data['what'],
            suggestion_source=suggestion_data['source'],
            confidence_score=suggestion_data['confidence'],
            action=action,
            actual_who=actual_data.get('who') if actual_data else None,
            actual_what=actual_data.get('what') if actual_data else None,
            user=transaction_match_history.matched_by,
            company=self.company,
        )
        
        # Update pattern metrics if this was a pattern suggestion
        if suggestion_data['source'] == 'pattern' and 'pattern_id' in suggestion_data:
            try:
                pattern = MatchPattern.objects.get(id=suggestion_data['pattern_id'])
                pattern.times_seen += 1
                
                if action == 'accepted':
                    pattern.times_accepted += 1
                elif action == 'rejected':
                    pattern.times_rejected += 1
                # 'modified' doesn't count as accepted or rejected
                
                # Recalculate pattern metrics
                pattern.update_metrics()
            except MatchPattern.DoesNotExist:
                pass  # Pattern was deleted
        
        return feedback
    
    def discover_new_patterns(self, min_occurrences=3):
        """
        Analyze transaction history to discover new patterns automatically
        
        Args:
            min_occurrences: Minimum times a pattern must appear to be considered
        
        Returns:
            List of newly created MatchPattern objects
        """
        # Find frequently matched description → WHO/WHAT combinations
        query = TransactionMatchHistory.objects.values(
            'transaction_description',
            'matched_who',
            'matched_what_id'
        ).annotate(
            count=Count('id')
        ).filter(
            count__gte=min_occurrences
        ).filter(
            Q(user_accepted=True) | Q(user_accepted__isnull=True)  # Include accepted and unspecified
        ).order_by('-count')
        
        # Filter by company if set
        if self.company:
            query = query.filter(company=self.company)
        
        frequent_matches = query[:50]  # Limit to top 50
        
        new_patterns = []
        
        for match in frequent_matches:
            description = match['transaction_description']
            
            # Check if pattern already exists
            exists = MatchPattern.objects.filter(
                Q(description_pattern__iexact=description) &
                (Q(company=self.company) if self.company else Q(company__isnull=True))
            ).exists()
            
            if not exists:
                # Create new pattern
                try:
                    # Extract key words from description for pattern name
                    words = description.split()[:3]  # First 3 words
                    pattern_name = f"Auto: {' '.join(words)}"
                    if len(pattern_name) > 50:
                        pattern_name = pattern_name[:47] + "..."
                    
                    # Make pattern name unique
                    base_name = pattern_name
                    counter = 1
                    while MatchPattern.objects.filter(pattern_name=pattern_name).exists():
                        pattern_name = f"{base_name} ({counter})"
                        counter += 1
                    
                    pattern = MatchPattern.objects.create(
                        pattern_name=pattern_name,
                        pattern_type='contains',  # Start with contains matching
                        description_pattern=description,
                        suggested_who=match['matched_who'],
                        suggested_what_id=match['matched_what_id'],
                        times_seen=match['count'],
                        times_accepted=match['count'],  # Assume all were accepted since they appear frequently
                        accuracy_rate=100.0,  # Start with 100%, will be updated with real feedback
                        confidence=70.0,  # Start with medium confidence
                        company=self.company,
                        created_by_id=1,  # System-generated (assuming admin user ID=1)
                    )
                    pattern.update_metrics()
                    new_patterns.append(pattern)
                except Exception as e:
                    # Skip patterns that fail (e.g., duplicate, invalid data)
                    print(f"Failed to create pattern: {e}")
                    continue
        
        return new_patterns


class ConfidenceCalculator:
    """
    Calculates and calibrates confidence scores for suggestions
    """
    
    def calculate_hybrid_confidence(self, rule_confidence, pattern_confidence):
        """
        Combine rule and pattern confidence scores intelligently
        
        Strategy: Take maximum (trust the stronger signal)
        Alternative: Could use weighted average or ensemble methods
        
        Args:
            rule_confidence: Confidence from bank rule (0-100) or None
            pattern_confidence: Confidence from AI pattern (0-100) or None
        
        Returns:
            Combined confidence score (0-100)
        """
        if rule_confidence and pattern_confidence:
            # Both exist: take maximum (most confident wins)
            return max(rule_confidence, pattern_confidence)
        
        # Return whichever exists, or 0 if neither
        return rule_confidence or pattern_confidence or 0.0
    
    def adjust_for_novelty(self, base_confidence, times_seen):
        """
        Adjust confidence based on how often we've seen this pattern
        
        New patterns: Reduce confidence until proven
        Established patterns: Full confidence
        
        Args:
            base_confidence: Initial confidence score (0-100)
            times_seen: Number of times pattern has been used
        
        Returns:
            Adjusted confidence score (0-100)
        """
        if times_seen < 3:
            # Very new: reduce by 30%
            return base_confidence * 0.7
        elif times_seen < 10:
            # Moderately new: reduce by 10%
            return base_confidence * 0.9
        else:
            # Established: full confidence
            return base_confidence
    
    def get_confidence_label(self, confidence):
        """
        Get human-readable label for confidence score
        
        Args:
            confidence: Score 0-100
        
        Returns:
            Label string
        """
        if confidence >= 90:
            return "Very High"
        elif confidence >= 75:
            return "High"
        elif confidence >= 60:
            return "Medium"
        elif confidence >= 40:
            return "Low"
        else:
            return "Very Low"
