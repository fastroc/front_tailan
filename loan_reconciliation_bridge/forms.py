"""
Forms for loan_reconciliation_bridge app
"""
from django import forms
from .models import LoanGLConfiguration
from coa.models import Account


class LoanGLConfigurationForm(forms.ModelForm):
    """Form for configuring Loan Payments Received account"""
    
    class Meta:
        model = LoanGLConfiguration
        fields = ['principal_account']
        widgets = {
            'principal_account': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        if company:
            # Show all accounts for the company - let user choose appropriate one
            accounts_queryset = Account.objects.filter(
                company=company
            ).order_by('code')
            
            self.fields['principal_account'].queryset = accounts_queryset
            
            # Set helpful label
            self.fields['principal_account'].label = 'Loan Payments Received Account'
            self.fields['principal_account'].help_text = 'Select the account that will receive loan payments during reconciliation (e.g., 1250 - Loan Payments Received)'
