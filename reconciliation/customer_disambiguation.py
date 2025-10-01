"""
Customer Disambiguation Utility for Smart Suggestions

Handles cases where multiple customers have same initials or multiple loans per customer
"""
from typing import List, Dict, Any, Optional
import re

class CustomerDisambiguationService:
    """Service to handle customer disambiguation in smart suggestions"""
    
    @staticmethod
    def rank_loan_matches(customer_loans: List[Dict], transaction_amount: float = None, 
                         description: str = "", is_disbursement: bool = False) -> List[Dict]:
        """
        Rank loans for a customer based on transaction context
        
        Args:
            customer_loans: List of loan dictionaries
            transaction_amount: Transaction amount (negative for disbursements, positive for payments)
            description: Transaction description for additional context
            is_disbursement: Whether this is a loan disbursement transaction
        
        Returns:
            List of loans ranked by relevance, with disambiguation scores
        """
        if not customer_loans:
            return []
            
        if len(customer_loans) == 1:
            loan = customer_loans[0].copy()
            loan['disambiguation_score'] = 50
            loan['disambiguation_reason'] = "Only loan for customer"
            return [loan]
        
        ranked_loans = []
        
        for loan in customer_loans:
            score = 0
            reasons = []
            loan_amount = loan.get('loan_amount', 0)
            loan_status = loan.get('status', '').lower()
            
            # Strategy 1: Exact amount matching (highest priority)
            if transaction_amount:
                amount_diff = abs(abs(transaction_amount) - loan_amount)
                if amount_diff < 1000:  # Within $1K
                    score += 50
                    reasons.append("Exact amount match")
                elif amount_diff < 10000:  # Within $10K
                    score += 30
                    reasons.append("Close amount match")
                elif loan_amount > 0:
                    # Partial amount matching for large loans
                    percentage = abs(transaction_amount) / loan_amount
                    if 0.1 <= percentage <= 1.1:  # 10% to 110% of loan
                        score += int(20 * (1 - abs(percentage - 0.5)))  # Peak at 50%
                        reasons.append(f"Partial amount ({percentage:.0%} of loan)")
            
            # Strategy 2: Status-based relevance
            if is_disbursement:
                if 'pending' in loan_status or 'approved' in loan_status:
                    score += 25
                    reasons.append("Pending disbursement status")
                elif 'disbursed' in loan_status and 'partial' in loan_status:
                    score += 15
                    reasons.append("Partially disbursed")
            else:  # Payment transaction
                if 'active' in loan_status or 'current' in loan_status:
                    score += 20
                    reasons.append("Active loan status")
                elif 'disbursed' in loan_status:
                    score += 15
                    reasons.append("Disbursed loan")
            
            # Strategy 3: Loan size preference (larger loans more likely to have activity)
            if loan_amount > 10000000:  # > $10M
                score += 15
                reasons.append("Large loan amount")
            elif loan_amount > 1000000:  # > $1M
                score += 10
                reasons.append("Significant loan amount")
            
            # Strategy 4: Description context clues
            description_lower = description.lower()
            if any(keyword in description_lower for keyword in ['олгов', 'disburs']):
                if 'pending' in loan_status:
                    score += 15
                    reasons.append("Disbursement keywords + pending status")
            elif any(keyword in description_lower for keyword in ['payment', 'төлбөр']):
                if 'active' in loan_status:
                    score += 15
                    reasons.append("Payment keywords + active status")
            
            # Strategy 5: Recency (prefer newer loans for activity)
            # This would need creation date - simplified for now
            score += 5  # Base score
            
            # Create ranked loan with disambiguation info
            ranked_loan = loan.copy()
            ranked_loan['disambiguation_score'] = score
            ranked_loan['disambiguation_reason'] = " + ".join(reasons) if reasons else "Base scoring"
            ranked_loans.append(ranked_loan)
        
        # Sort by disambiguation score (highest first)
        ranked_loans.sort(key=lambda x: x['disambiguation_score'], reverse=True)
        
        return ranked_loans
    
    @staticmethod
    def detect_transaction_type(description: str, amount: float) -> Dict[str, Any]:
        """
        Detect if transaction is a disbursement or payment based on description and amount
        """
        description_lower = description.lower()
        
        # Disbursement indicators
        disbursement_keywords = [
            'зээл олгов', 'олгосон', 'зээл олго', 'disburs', 'диsburse',
            'loan disburs', 'олгосон зээл', 'eb-', 'зээл-', 'олголт'
        ]
        
        # Payment indicators  
        payment_keywords = [
            'payment', 'төлбөр', 'төлөлт', 'installment', 'буцаалт',
            'зээлийн төлбөр', 'сарын төлбөр'
        ]
        
        is_disbursement = (
            amount < 0 and 
            any(keyword in description_lower for keyword in disbursement_keywords)
        )
        
        is_payment = (
            amount > 0 and 
            any(keyword in description_lower for keyword in payment_keywords)
        )
        
        return {
            'is_disbursement': is_disbursement,
            'is_payment': is_payment,
            'transaction_type': (
                'disbursement' if is_disbursement else
                'payment' if is_payment else
                'unknown'
            ),
            'confidence': 0.8 if (is_disbursement or is_payment) else 0.3
        }
    
    @staticmethod
    def format_suggestion_with_disambiguation(suggestion: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format suggestion with clear disambiguation information for the UI
        """
        enhanced_suggestion = suggestion.copy()
        
        # Add disambiguation info to customer name if multiple loans
        if suggestion.get('disambiguation_reason'):
            customer_name = suggestion.get('customer_name', '')
            loan_amount = suggestion.get('loan_amount', 0)
            disambiguation = suggestion.get('disambiguation_reason', '')
            
            # Create clear display with amount and reason
            if loan_amount > 0:
                amount_display = f"${loan_amount:,.0f}"
                enhanced_suggestion['customer_name_extended'] = f"{customer_name} ({amount_display} - {disambiguation})"
            else:
                enhanced_suggestion['customer_name_extended'] = f"{customer_name} ({disambiguation})"
        
        return enhanced_suggestion
