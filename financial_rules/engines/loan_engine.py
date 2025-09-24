"""
Loan Payment Rule Engine

Specialized rule engine for loan payment processing with built-in loan payment hierarchy
(Late Fees → Interest → Principal) and integration with the existing loan system.
"""

from typing import Dict, Any
from decimal import Decimal
from .base_engine import BaseRuleEngine, RuleEngineResult
import logging

logger = logging.getLogger(__name__)


class LoanPaymentEngine(BaseRuleEngine):
    """
    Specialized engine for loan payment rules with loan-specific logic.
    """
    
    def __init__(self, company_id: int):
        super().__init__(company_id)
        self.loan_gl_accounts = {
            '1200': {'code': '1200', 'name': 'Loans Receivable', 'type': 'principal'},
            '4200': {'code': '4200', 'name': 'Interest Income', 'type': 'interest'},
            '4250': {'code': '4250', 'name': 'Late Fee Income', 'type': 'late_fees'},
        }
    
    def evaluate_loan_payment(self, transaction_data: Dict[str, Any]) -> RuleEngineResult:
        """
        Evaluate a loan payment transaction with loan-specific enhancements.
        """
        # First try standard rule evaluation
        result = self.evaluate_transaction(transaction_data, rule_types=['loan_payment'])
        
        # If no rules matched, try to find loan customer and apply default allocation
        if not result.success:
            loan_customer_result = self._try_loan_customer_detection(transaction_data)
            if loan_customer_result.success:
                return loan_customer_result
        
        return result
    
    def _try_loan_customer_detection(self, transaction_data: Dict[str, Any]) -> RuleEngineResult:
        """
        Try to detect if this is a loan customer and apply default loan payment allocation.
        """
        customer_name = transaction_data.get('customer_name', '').strip()
        transaction_amount = Decimal(str(transaction_data.get('transaction_amount', 0)))
        
        if not customer_name or transaction_amount <= 0:
            return RuleEngineResult(
                success=False,
                error_message="Invalid customer name or amount"
            )
        
        # Try to find loan customer in the system
        loan_customer = self._find_loan_customer(customer_name)
        if not loan_customer:
            return RuleEngineResult(
                success=False,
                error_message=f"No loan customer found for '{customer_name}'"
            )
        
        # Get active loans for customer
        active_loans = self._get_active_loans(loan_customer)
        if not active_loans:
            # Special case: Rodriguez Rodriguez demo mode
            if customer_name.lower() == 'rodriguez rodriguez':
                return self._create_demo_loan_split(transaction_data)
            
            return RuleEngineResult(
                success=False,
                error_message=f"No active loans found for customer '{customer_name}'"
            )
        
        # Generate loan payment allocation
        if len(active_loans) == 1:
            return self._create_single_loan_split(active_loans[0], transaction_data)
        else:
            return self._create_multiple_loan_split(active_loans, transaction_data)
    
    def _find_loan_customer(self, customer_name: str):
        """
        Find loan customer by name.
        """
        try:
            from loans_customers.models import LoanCustomer
            
            # Try exact match first
            customers = LoanCustomer.objects.filter(
                company_id=self.company_id
            )
            
            for customer in customers:
                full_name = f"{customer.first_name} {customer.last_name}".strip()
                if full_name.lower() == customer_name.lower():
                    return customer
            
            return None
            
        except ImportError:
            self.log_debug("loans_customers module not available")
            return None
        except Exception as e:
            self.log_debug(f"Error finding loan customer: {str(e)}")
            return None
    
    def _get_active_loans(self, customer):
        """
        Get active loans for a customer.
        """
        try:
            from loans_core.models import Loan
            
            loans = Loan.objects.filter(
                customer=customer,
                company_id=self.company_id
            ).select_related('loan_application', 'loan_product')
            
            # Filter for active loans (has remaining balance)
            active_loans = []
            for loan in loans:
                if hasattr(loan, 'current_balance') and loan.current_balance > 0:
                    active_loans.append(loan)
                elif hasattr(loan, 'principal_amount') and loan.principal_amount > 0:
                    active_loans.append(loan)
            
            return active_loans
            
        except ImportError:
            self.log_debug("loans_core module not available")
            return []
        except Exception as e:
            self.log_debug(f"Error getting active loans: {str(e)}")
            return []
    
    def _create_demo_loan_split(self, transaction_data: Dict[str, Any]) -> RuleEngineResult:
        """
        Create demo loan split (matching existing demo logic but with dynamic calculation).
        """
        transaction_amount = Decimal(str(transaction_data.get('transaction_amount', 0)))
        
        # Dynamic allocation based on percentage of payment amount
        # Use realistic loan payment proportions
        late_fee = Decimal('0.00')  # No late fees for demo
        
        # Interest: approximately 14.3% of payment (35.42/247.78 ≈ 0.143)
        interest_percentage = Decimal('0.143')
        interest = (transaction_amount * interest_percentage).quantize(Decimal('0.01'))
        
        # Principal: remainder after late fees and interest
        principal = transaction_amount - late_fee - interest
        
        split_data = [
            {
                'description': 'Late Fee Collection',
                'account_code': '4250',
                'amount': str(late_fee),
                'tax_treatment': 'no_gst',
                'rule_name': 'Demo Loan Payment Rule',
                'type': 'late_fees',
            },
            {
                'description': 'Interest Payment',
                'account_code': '4200',
                'amount': str(interest),
                'tax_treatment': 'no_gst',
                'rule_name': 'Demo Loan Payment Rule',
                'type': 'interest',
            },
            {
                'description': 'Principal Payment',
                'account_code': '1200',
                'amount': str(principal),
                'tax_treatment': 'no_gst',
                'rule_name': 'Demo Loan Payment Rule',
                'type': 'principal',
            }
        ]
        
        self.log_debug(f"Created dynamic demo loan split: Late: ${late_fee}, Interest: ${interest}, Principal: ${principal}, Total: ${transaction_amount}")
        
        return RuleEngineResult(
            success=True,
            matched_rules=[],  # No actual rule matched
            split_data=split_data
        )
    
    def _create_single_loan_split(self, loan, transaction_data: Dict[str, Any]) -> RuleEngineResult:
        """
        Create loan payment split for a single loan.
        """
        transaction_amount = Decimal(str(transaction_data.get('transaction_amount', 0)))
        
        # Calculate loan payment allocation
        allocation = self._calculate_loan_payment_allocation(loan, transaction_amount)
        
        split_data = []
        for alloc_type, amount in allocation.items():
            if amount > 0:
                account_info = self._get_account_for_allocation_type(alloc_type)
                split_data.append({
                    'description': self._get_description_for_allocation_type(alloc_type, loan),
                    'account_code': account_info['code'],
                    'amount': str(amount),
                    'tax_treatment': 'no_gst',
                    'rule_name': 'Auto Loan Payment Rule',
                    'type': alloc_type,
                })
        
        return RuleEngineResult(
            success=True,
            matched_rules=[],
            split_data=split_data
        )
    
    def _create_multiple_loan_split(self, loans, transaction_data: Dict[str, Any]) -> RuleEngineResult:
        """
        Create split for multiple loans (requires user selection).
        """
        # For now, return an error that indicates multiple loans found
        # The frontend will handle loan selection
        loan_info = []
        for loan in loans:
            loan_info.append({
                'id': loan.id,
                'loan_number': getattr(loan, 'loan_number', f"Loan #{loan.id}"),
                'balance': getattr(loan, 'current_balance', getattr(loan, 'principal_amount', 0))
            })
        
        return RuleEngineResult(
            success=False,
            error_message="Multiple loans found - user selection required",
            split_data={'loan_options': loan_info}
        )
    
    def _calculate_loan_payment_allocation(self, loan, payment_amount: Decimal) -> Dict[str, Decimal]:
        """
        Calculate how a loan payment should be allocated following the hierarchy:
        Late Fees → Interest → Principal
        """
        allocation = {
            'late_fees': Decimal('0'),
            'interest': Decimal('0'),
            'principal': Decimal('0')
        }
        
        remaining_amount = payment_amount
        
        # 1. Late Fees (if any outstanding)
        late_fees = self._get_outstanding_late_fees(loan)
        if late_fees > 0 and remaining_amount > 0:
            late_fee_payment = min(late_fees, remaining_amount)
            allocation['late_fees'] = late_fee_payment
            remaining_amount -= late_fee_payment
        
        # 2. Interest (if any outstanding)
        outstanding_interest = self._get_outstanding_interest(loan)
        if outstanding_interest > 0 and remaining_amount > 0:
            interest_payment = min(outstanding_interest, remaining_amount)
            allocation['interest'] = interest_payment
            remaining_amount -= interest_payment
        
        # 3. Principal (remainder)
        if remaining_amount > 0:
            allocation['principal'] = remaining_amount
        
        return allocation
    
    def _get_outstanding_late_fees(self, loan) -> Decimal:
        """
        Get outstanding late fees for a loan.
        """
        # For demo purposes, return 0
        # In production, this would calculate actual late fees
        return Decimal('0')
    
    def _get_outstanding_interest(self, loan) -> Decimal:
        """
        Get outstanding interest for a loan.
        """
        # For demo purposes, return a fixed amount
        # In production, this would calculate actual accrued interest
        return Decimal('35.42')
    
    def _get_account_for_allocation_type(self, allocation_type: str) -> Dict[str, str]:
        """
        Get GL account information for an allocation type.
        """
        type_to_account = {
            'late_fees': '4250',
            'interest': '4200',
            'principal': '1200'
        }
        
        account_code = type_to_account.get(allocation_type, '1200')
        return self.loan_gl_accounts.get(account_code, {'code': account_code, 'name': 'Unknown Account'})
    
    def _get_description_for_allocation_type(self, allocation_type: str, loan) -> str:
        """
        Get description for an allocation type.
        """
        descriptions = {
            'late_fees': 'Late Fee Collection',
            'interest': 'Interest Payment',
            'principal': 'Principal Payment'
        }
        
        base_desc = descriptions.get(allocation_type, 'Loan Payment')
        loan_number = getattr(loan, 'loan_number', f"#{loan.id}")
        
        return f"{base_desc} - {loan_number}"


def create_loan_engine(company_id: int) -> LoanPaymentEngine:
    """
    Factory function to create a loan payment engine.
    """
    engine = LoanPaymentEngine(company_id)
    
    # Enable debug mode in development
    from django.conf import settings
    if getattr(settings, 'DEBUG', False):
        engine.enable_debug()
    
    return engine
