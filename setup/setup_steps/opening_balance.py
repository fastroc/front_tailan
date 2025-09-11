from django import forms
from decimal import Decimal
from ..base import BaseSetupStep
from coa.models import Account


class OpeningBalanceForm(forms.Form):
    """Form for setting opening cash balance"""
    
    opening_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="As of Date",
        help_text="The date when these balances are effective"
    )
    
    cash_balance = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        initial=Decimal('0.00'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        }),
        label="Starting Cash Balance",
        help_text="How much cash does the company have?"
    )
    
    def clean_cash_balance(self):
        balance = self.cleaned_data.get('cash_balance')
        if balance is None:
            return Decimal('0.00')
        return balance


class OpeningBalanceSetupStep(BaseSetupStep):
    """Opening balance setup step"""
    
    name = "Opening Balance"
    description = "Set your starting cash amount"
    priority = 4
    required = False  # Optional for basic functionality
    url_name = "opening_balance"
    template_name = "setup/opening_balance.html"
    
    def is_complete(self, company):
        """Check if opening balance is set"""
        # Check if any cash account has a non-zero opening balance
        cash_accounts = Account.objects.filter(
            company=company,
            account_type='CURRENT_ASSET'
        )
        return any(account.ytd_balance != 0 for account in cash_accounts)
    
    def get_form_class(self):
        return OpeningBalanceForm
    
    def process_form(self, form, company, request):
        """Set the opening balance"""
        try:
            # Get the main cash account
            cash_account = Account.objects.filter(
                company=company,
                account_type='CURRENT_ASSET'
            ).first()
            
            if not cash_account:
                request.messages.error(request, 'No cash account found. Please create essential accounts first.')
                return False
            
            # Set the opening balance
            opening_balance_amount = form.cleaned_data['cash_balance']
            
            # Update account balance
            cash_account.ytd_balance = opening_balance_amount
            cash_account.save()
            
            # Create OpeningBalance record
            from coa.models import OpeningBalance
            from datetime import date
            
            # Check if opening balance record already exists
            existing_balance = OpeningBalance.objects.filter(
                company=company,
                account=cash_account
            ).first()
            
            if existing_balance:
                # Update existing record
                existing_balance.balance_amount = opening_balance_amount
                existing_balance.balance_date = date.today()
                existing_balance.description = 'Updated opening balance from setup'
                existing_balance.entered_by = request.user
                existing_balance.save()
            else:
                # Create new record
                OpeningBalance.objects.create(
                    company=company,
                    account=cash_account,
                    balance_amount=opening_balance_amount,
                    balance_date=date.today(),
                    description='Opening balance from setup',
                    entered_by=request.user,
                    is_active=True
                )
            
            # Update setup status
            from setup.models import CompanySetupStatus
            setup_status, created = CompanySetupStatus.objects.get_or_create(
                company=company
            )
            setup_status.balance_complete = True
            setup_status.save()
            
            return True
            
        except Exception as e:
            if hasattr(request, 'messages'):
                request.messages.error(request, f"Error setting opening balance: {str(e)}")
            return False
    
    def get_context(self, company, request=None):
        context = super().get_context(company, request)
        
        # Get existing cash accounts
        cash_accounts = Account.objects.filter(
            company=company,
            account_type='CURRENT_ASSET'
        )
        
        # Calculate current total cash balance
        total_cash = sum(account.ytd_balance for account in cash_accounts)
        
        context.update({
            'cash_accounts': cash_accounts,
            'total_cash': total_cash,
            'accounts_exist': cash_accounts.exists(),
            'form': self.get_form_class()() if request and request.method != 'POST' else None
        })
        return context
