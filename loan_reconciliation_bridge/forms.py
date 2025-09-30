"""
Forms for loan_reconciliation_bridge app
"""
from django import forms
from .models import LoanGLConfiguration
from coa.models import Account


class LoanGLConfigurationForm(forms.ModelForm):
    """Form for configuring Five-Tier Payment Allocation system"""
    
    class Meta:
        model = LoanGLConfiguration
        fields = [
            'general_loans_receivable_account', 
            'principal_account', 
            'interest_income_account', 
            'late_fee_income_account',
            'general_loan_disbursements_account'
        ]
        widgets = {
            'general_loans_receivable_account': forms.Select(attrs={'class': 'form-control'}),
            'principal_account': forms.Select(attrs={'class': 'form-control'}),
            'interest_income_account': forms.Select(attrs={'class': 'form-control'}),
            'late_fee_income_account': forms.Select(attrs={'class': 'form-control'}),
            'general_loan_disbursements_account': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        if company:
            # SIMPLE: Show ALL company accounts in ALL dropdowns - no smart filtering
            all_accounts = Account.objects.filter(
                company=company
            ).order_by('code')
            
            # Set same queryset for all fields - user chooses appropriate accounts
            self.fields['general_loans_receivable_account'].queryset = all_accounts
            self.fields['principal_account'].queryset = all_accounts
            self.fields['interest_income_account'].queryset = all_accounts
            self.fields['late_fee_income_account'].queryset = all_accounts
            self.fields['general_loan_disbursements_account'].queryset = all_accounts
            
            # Set helpful labels and help text
            self.fields['general_loans_receivable_account'].label = 'General Loans Receivable Account (Main Engine)'
            self.fields['general_loans_receivable_account'].help_text = 'Main account that receives payments and creates Payment records via reconciliation'
            
            self.fields['principal_account'].label = 'Principal Allocation Account'
            self.fields['principal_account'].help_text = 'Account for principal portion of payments (can be same as General Loans Receivable)'
            
            self.fields['interest_income_account'].label = 'Interest Income Account'
            self.fields['interest_income_account'].help_text = 'Revenue account for interest portion of payments'
            
            self.fields['late_fee_income_account'].label = 'Late Fee Income Account'
            self.fields['late_fee_income_account'].help_text = 'Revenue account for late fee portion of payments'
            
            self.fields['general_loan_disbursements_account'].label = 'General Loan Disbursements Account (Auto-Match)'
            self.fields['general_loan_disbursements_account'].help_text = 'Account for automatic loan disbursement detection and matching (Recommended: 1250 - Loan Disbursements)'
            
            # Pre-select suggested accounts for better UX
            self._set_suggested_defaults()
    
    def _set_suggested_defaults(self):
        """Set suggested default accounts if none are selected"""
        if not self.instance.pk:  # Only for new configurations
            company = self.initial.get('company') or getattr(self.instance, 'company', None)
            if company:
                # Try to find suggested accounts by code patterns
                accounts = Account.objects.filter(company=company)
                
                # Suggest 1250 for General Loan Disbursements
                disbursement_account = accounts.filter(code='1250').first()
                if disbursement_account and not self.instance.general_loan_disbursements_account:
                    self.fields['general_loan_disbursements_account'].initial = disbursement_account.id
                
                # Suggest 122000 or 1200 for General Loans Receivable  
                receivable_account = accounts.filter(code__in=['122000', '1200']).first()
                if receivable_account and not self.instance.general_loans_receivable_account:
                    self.fields['general_loans_receivable_account'].initial = receivable_account.id
                
                # Suggest 4200 for Interest Income
                interest_account = accounts.filter(code='4200').first()
                if interest_account and not self.instance.interest_income_account:
                    self.fields['interest_income_account'].initial = interest_account.id
                
                # Suggest 4250 for Late Fee Income
                late_fee_account = accounts.filter(code='4250').first()
                if late_fee_account and not self.instance.late_fee_income_account:
                    self.fields['late_fee_income_account'].initial = late_fee_account.id
