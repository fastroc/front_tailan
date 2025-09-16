from django import forms
from django.core.exceptions import ValidationError
from datetime import date
from .models import ConversionDate, ConversionBalance
from coa.models import Account


class ConversionDateForm(forms.ModelForm):
    """Form for setting conversion date"""
    
    month = forms.ChoiceField(
        choices=[
            (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
            (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
            (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    year = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = ConversionDate
        fields = ['conversion_date']
        widgets = {
            'conversion_date': forms.HiddenInput()
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Generate year choices (current year and previous 5 years)
        current_year = date.today().year
        year_choices = [(year, year) for year in range(current_year - 5, current_year + 2)]
        self.fields['year'].choices = year_choices
        
        # If instance has conversion_date, populate month and year
        if self.instance and self.instance.conversion_date:
            conv_date = self.instance.conversion_date
            self.fields['month'].initial = conv_date.month
            self.fields['year'].initial = conv_date.year
    
    def clean(self):
        cleaned_data = super().clean()
        month = int(cleaned_data.get('month', 1))
        year = int(cleaned_data.get('year', date.today().year))
        
        # Set conversion_date to first day of selected month/year
        try:
            conversion_date = date(year, month, 1)
            cleaned_data['conversion_date'] = conversion_date
        except ValueError as e:
            raise ValidationError(f"Invalid date: {e}")
        
        return cleaned_data


class ConversionBalanceForm(forms.ModelForm):
    """Form for entering conversion balances"""
    
    class Meta:
        model = ConversionBalance
        fields = [
            'account', 'debit_amount', 'credit_amount', 'notes'
        ]
        widgets = {
            'account': forms.Select(attrs={
                'class': 'form-select form-select-sm'
            }),
            'debit_amount': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm text-end',
                'step': '0.01',
                'min': '0'
            }),
            'credit_amount': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm text-end',
                'step': '0.01',
                'min': '0'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control form-control-sm',
                'rows': 2
            })
        }
    
    def __init__(self, company=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if company:
            # Filter accounts to company's chart of accounts
            self.fields['account'].queryset = Account.objects.filter(
                company=company
            ).order_by('code', 'name')


class ConversionBalanceFormSet(forms.BaseFormSet):
    """Formset for multiple conversion balance entries"""
    
    def clean(self):
        """Ensure total debits equal total credits"""
        if any(self.errors):
            return
        
        total_debits = 0
        total_credits = 0
        
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                total_debits += form.cleaned_data.get('debit_amount', 0)
                total_credits += form.cleaned_data.get('credit_amount', 0)
        
        # Allow small rounding differences
        difference = abs(total_debits - total_credits)
        if difference > 0.01:  # More than 1 cent difference
            raise ValidationError(
                f"Total debits (${total_debits:,.2f}) must equal total credits "
                f"(${total_credits:,.2f}). Difference: ${difference:,.2f}"
            )
