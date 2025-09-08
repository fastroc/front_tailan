from django import forms
from django.core.exceptions import ValidationError
from .models import Company
import datetime

class CompanyCreateForm(forms.ModelForm):
    """
    Form for creating and editing companies
    """
    
    class Meta:
        model = Company
        fields = [
            'name', 'legal_name', 'logo',
            'business_type', 'industry', 'registration_number', 'tax_id',
            'email', 'phone', 'website',
            'address_line_1', 'address_line_2', 'city', 'state_province', 'postal_code', 'country',
            'base_currency', 'financial_year_start'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter company name'
            }),
            'legal_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Legal registered name (if different)'
            }),
            'business_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'industry': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Technology, Healthcare, Manufacturing'
            }),
            'registration_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Business registration/license number'
            }),
            'tax_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tax ID (EIN, ABN, etc.)'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'company@example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1 (555) 123-4567'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.company.com'
            }),
            'address_line_1': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Street address'
            }),
            'address_line_2': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apartment, suite, unit, building, floor, etc.'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City'
            }),
            'state_province': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'State/Province'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ZIP/Postal code'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Country'
            }),
            'base_currency': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'USD',
                'maxlength': '3'
            }),
            'financial_year_start': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'logo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }
        
        labels = {
            'name': 'Company Name *',
            'legal_name': 'Legal Name',
            'business_type': 'Business Type',
            'industry': 'Industry',
            'registration_number': 'Registration Number',
            'tax_id': 'Tax ID',
            'email': 'Email Address',
            'phone': 'Phone Number',
            'website': 'Website',
            'address_line_1': 'Address Line 1',
            'address_line_2': 'Address Line 2',
            'city': 'City',
            'state_province': 'State/Province',
            'postal_code': 'ZIP/Postal Code',
            'country': 'Country',
            'base_currency': 'Base Currency *',
            'financial_year_start': 'Financial Year Start',
            'logo': 'Company Logo',
        }
        
        help_texts = {
            'name': 'This will be displayed throughout the system',
            'legal_name': 'Official registered business name',
            'base_currency': 'Three-letter currency code (e.g., USD, EUR, GBP)',
            'financial_year_start': 'When does your financial year begin?',
            'logo': 'Upload a company logo (optional)',
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            if len(name) < 2:
                raise ValidationError('Company name must be at least 2 characters long.')
        return name
    
    def clean_base_currency(self):
        currency = self.cleaned_data.get('base_currency')
        if currency:
            currency = currency.upper().strip()
            if len(currency) != 3:
                raise ValidationError('Currency code must be exactly 3 characters (e.g., USD).')
        return currency
    
    def clean_financial_year_start(self):
        start_date = self.cleaned_data.get('financial_year_start')
        if start_date:
            # Check if the date is not too far in the future
            current_year = datetime.date.today().year
            if start_date.year > current_year + 2:
                raise ValidationError('Financial year start cannot be more than 2 years in the future.')
        return start_date
    
    def clean_logo(self):
        logo = self.cleaned_data.get('logo')
        if logo:
            # Check file size (limit to 5MB)
            if logo.size > 5 * 1024 * 1024:
                raise ValidationError('Logo file size cannot exceed 5MB.')
            
            # Check file type
            if not logo.content_type.startswith('image/'):
                raise ValidationError('Logo must be an image file.')
        
        return logo


class CompanyQuickCreateForm(forms.ModelForm):
    """
    Simplified form for quick company creation
    """
    
    class Meta:
        model = Company
        fields = ['name', 'business_type', 'base_currency', 'financial_year_start']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Enter your company name'
            }),
            'business_type': forms.Select(attrs={
                'class': 'form-select form-select-lg'
            }),
            'base_currency': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'USD',
                'maxlength': '3'
            }),
            'financial_year_start': forms.DateInput(attrs={
                'class': 'form-control form-control-lg',
                'type': 'date'
            }),
        }
        
        labels = {
            'name': 'Company Name',
            'business_type': 'Business Type',
            'base_currency': 'Currency',
            'financial_year_start': 'Financial Year Start',
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            if len(name) < 2:
                raise ValidationError('Company name must be at least 2 characters long.')
        return name
    
    def clean_base_currency(self):
        currency = self.cleaned_data.get('base_currency')
        if currency:
            currency = currency.upper().strip()
            if len(currency) != 3:
                raise ValidationError('Currency code must be exactly 3 characters.')
        return currency
