from django import forms
from ..base import BaseSetupStep
from coa.models import Account
from django.db import transaction


class EssentialAccountsForm(forms.Form):
    """Form for creating essential accounts"""
    
    create_defaults = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Create default essential accounts automatically"
    )
    
    cash_account_name = forms.CharField(
        max_length=100,
        initial="Cash",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Cash Account Name'
        }),
        label="Cash Account Name"
    )
    
    income_account_name = forms.CharField(
        max_length=100,
        initial="Sales Revenue",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Income Account Name'
        }),
        label="Income Account Name"
    )
    
    expense_account_name = forms.CharField(
        max_length=100,
        initial="General Expenses",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Expense Account Name'
        }),
        label="Expense Account Name"
    )


class EssentialAccountsSetupStep(BaseSetupStep):
    """Essential accounts setup step"""
    
    name = "Essential Accounts"
    description = "Create the basic accounts needed for transactions"
    priority = 2
    required = True
    url_name = "essential_accounts"
    template_name = "setup/essential_accounts.html"
    
    def is_complete(self, company):
        """Check if essential accounts exist"""
        cash_exists = Account.objects.filter(
            company=company,
            account_type='CURRENT_ASSET'
        ).exists()
        
        income_exists = Account.objects.filter(
            company=company,
            account_type__in=['REVENUE', 'SALES']
        ).exists()
        
        expense_exists = Account.objects.filter(
            company=company,
            account_type='EXPENSE'
        ).exists()
        
        return cash_exists and income_exists and expense_exists
    
    def get_form_class(self):
        return EssentialAccountsForm
    
    def process_form(self, form, company, request):
        """Create essential accounts"""
        try:
            with transaction.atomic():
                if form.cleaned_data['create_defaults']:
                    # Create Cash Account
                    Account.objects.get_or_create(
                        company=company,
                        code="1001",
                        defaults={
                            'name': form.cleaned_data['cash_account_name'],
                            'account_type': 'CURRENT_ASSET',
                            'description': 'Company cash and bank accounts',
                            'is_active': True
                        }
                    )
                    
                    # Create Income Account
                    Account.objects.get_or_create(
                        company=company,
                        code="4001",
                        defaults={
                            'name': form.cleaned_data['income_account_name'],
                            'account_type': 'REVENUE',
                            'description': 'Revenue from sales and services',
                            'is_active': True
                        }
                    )
                    
                    # Create Expense Account
                    Account.objects.get_or_create(
                        company=company,
                        code="6001",
                        defaults={
                            'name': form.cleaned_data['expense_account_name'],
                            'account_type': 'EXPENSE',
                            'description': 'General business expenses',
                            'is_active': True
                        }
                    )
                
                # Update setup status
                from setup.models import CompanySetupStatus
                setup_status, created = CompanySetupStatus.objects.get_or_create(
                    company=company
                )
                setup_status.accounts_complete = True
                setup_status.save()
                
                return True
                
        except Exception as e:
            request.messages.error(request, f"Error creating accounts: {str(e)}")
            return False
    
    def get_context(self, company, request=None):
        context = super().get_context(company, request)
        
        # Get existing accounts count
        accounts_count = Account.objects.filter(company=company).count()
        
        # Get existing essential accounts
        cash_accounts = Account.objects.filter(
            company=company,
            account_type='CURRENT_ASSET'
        )
        income_accounts = Account.objects.filter(
            company=company,
            account_type__in=['REVENUE', 'SALES']
        )
        expense_accounts = Account.objects.filter(
            company=company,
            account_type='EXPENSE'
        )
        
        context.update({
            'accounts_count': accounts_count,
            'cash_accounts': cash_accounts,
            'income_accounts': income_accounts,
            'expense_accounts': expense_accounts,
            'form': self.get_form_class()() if request and request.method != 'POST' else None
        })
        return context
