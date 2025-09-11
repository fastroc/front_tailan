from django import forms
from decimal import Decimal
from ..base import BaseSetupStep
from coa.models import TaxRate


class TaxSetupForm(forms.Form):
    """Form for basic tax setup"""
    
    create_default_tax = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Create default tax rate"
    )
    
    tax_name = forms.CharField(
        max_length=100,
        initial="Sales Tax",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tax Rate Name'
        }),
        label="Tax Rate Name"
    )
    
    tax_percentage = forms.DecimalField(
        max_digits=5,
        decimal_places=3,
        initial=Decimal('0.000'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.001',
            'placeholder': '0.000'
        }),
        label="Tax Percentage",
        help_text="Enter as decimal (e.g., 0.075 for 7.5%)"
    )


class TaxSetupStep(BaseSetupStep):
    """Tax setup step"""
    
    name = "Tax Configuration"
    description = "Set up your default tax rate"
    priority = 3
    required = False  # Optional for basic functionality
    url_name = "tax_setup"
    template_name = "setup/tax_setup.html"
    
    def is_complete(self, company):
        """Check if tax rates are configured"""
        return TaxRate.objects.filter(company=company).exists()
    
    def get_form_class(self):
        return TaxSetupForm
    
    def process_form(self, form, company, request):
        """Create tax rate"""
        try:
            if form.cleaned_data['create_default_tax']:
                # Create tax rate
                TaxRate.objects.get_or_create(
                    company=company,
                    name=form.cleaned_data['tax_name'],
                    defaults={
                        'rate': form.cleaned_data['tax_percentage'],
                        'description': 'Default tax rate for sales',
                        'is_active': True
                    }
                )
            
            # Update setup status
            from setup.models import CompanySetupStatus
            setup_status, created = CompanySetupStatus.objects.get_or_create(
                company=company
            )
            setup_status.tax_complete = True
            setup_status.save()
            
            return True
            
        except Exception as e:
            if hasattr(request, 'messages'):
                request.messages.error(request, f"Error creating tax rate: {str(e)}")
            return False
    
    def get_context(self, company, request=None):
        context = super().get_context(company, request)
        
        # Get existing tax rates
        tax_rates = TaxRate.objects.filter(company=company)
        
        context.update({
            'tax_rates': tax_rates,
            'tax_count': tax_rates.count(),
            'form': self.get_form_class()() if request and request.method != 'POST' else None
        })
        return context
