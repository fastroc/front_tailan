"""
Fixed Asset Forms
Comprehensive forms for asset management matching new.html template
"""

import calendar
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from .models import FixedAsset, AssetType, AssetDisposal


class FixedAssetForm(forms.ModelForm):
    """
    Comprehensive Fixed Asset form matching new.html template
    Includes all fields and validation logic
    """
    
    class Meta:
        model = FixedAsset
        fields = [
            # Basic Asset Information
            'name', 'number', 'description', 'asset_type', 'serial_number',
            
            # Location & Tracking
            'location', 'supplier',
            
            # Financial Information
            'purchase_price', 'purchase_date', 'depreciation_start_date',
            'residual_value', 'cost_limit',
            
            # Depreciation Configuration - removed depreciation_basis and depreciation_rate
            'depreciation_method', 'averaging_method', 'effective_life',
            
            # Asset Lifecycle
            'warranty_expiry', 'expected_disposal_date', 'disposal_method',
            'estimated_disposal_value',
            
            # Tax Depreciation
            'separate_tax_depreciation', 'tax_depreciation_method',
        ]
        
        widgets = {
            # Text inputs with professional styling
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dell Laptop',
                'required': True
            }),
            'number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Auto-generated',
                'readonly': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Brief description of the asset'
            }),
            'serial_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'SN123456'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Main Office, IT Department'
            }),
            'supplier': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Company name'
            }),
            
            # Select dropdowns
            'asset_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'depreciation_method': forms.Select(attrs={
                'class': 'form-control'
            }),
            'averaging_method': forms.Select(attrs={
                'class': 'form-control'
            }),
            'disposal_method': forms.Select(attrs={
                'class': 'form-control'
            }),
            'tax_depreciation_method': forms.Select(attrs={
                'class': 'form-control'
            }),
            
            # Financial inputs with currency styling
            'purchase_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01',
                'required': True
            }),
            'residual_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.00'
            }),
            'cost_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.00'
            }),
            'estimated_disposal_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.00'
            }),
            
            # Depreciation calculation inputs
            'effective_life': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '5',
                'min': '1',
                'max': '50'
            }),
            
            # Date inputs
            'purchase_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'depreciation_start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'warranty_expiry': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'expected_disposal_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            
            # Checkbox for tax depreciation
            'separate_tax_depreciation': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter asset types to active only
        self.fields['asset_type'].queryset = AssetType.objects.filter(is_active=True)
        
        # Set default values for new assets
        if not self.instance.pk:
            self.fields['purchase_date'].initial = timezone.now().date()
            self.fields['depreciation_method'].initial = 'straight_line'
            self.fields['averaging_method'].initial = 'full_month'
    
    def clean(self):
        """Comprehensive form validation"""
        cleaned_data = super().clean()
        
        # Validate depreciation configuration
        self._validate_depreciation_settings(cleaned_data)
        
        # Validate financial amounts
        self._validate_financial_amounts(cleaned_data)
        
        # Validate dates
        self._validate_dates(cleaned_data)
        
        return cleaned_data
    
    def _validate_depreciation_settings(self, cleaned_data):
        """Validate depreciation method and effective life"""
        depreciation_method = cleaned_data.get('depreciation_method')
        effective_life = cleaned_data.get('effective_life')
        
        if depreciation_method and depreciation_method != 'none':
            if not effective_life:
                raise ValidationError({
                    'effective_life': 'Effective life is required when depreciation method is set.'
                })
            if effective_life <= 0 or effective_life > 50:
                raise ValidationError({
                    'effective_life': 'Effective life must be between 1 and 50 years.'
                })
    
    def _validate_financial_amounts(self, cleaned_data):
        """Validate financial amount relationships"""
        purchase_price = cleaned_data.get('purchase_price')
        residual_value = cleaned_data.get('residual_value', Decimal('0.00'))
        cost_limit = cleaned_data.get('cost_limit')
        
        if purchase_price and residual_value:
            if residual_value >= purchase_price:
                raise ValidationError({
                    'residual_value': 'Residual value must be less than purchase price.'
                })
        
        if cost_limit and purchase_price:
            if cost_limit < purchase_price:
                raise ValidationError({
                    'cost_limit': 'Cost limit cannot be less than purchase price.'
                })
    
    def _validate_dates(self, cleaned_data):
        """Validate date relationships"""
        purchase_date = cleaned_data.get('purchase_date')
        depreciation_start_date = cleaned_data.get('depreciation_start_date')
        warranty_expiry = cleaned_data.get('warranty_expiry')
        expected_disposal_date = cleaned_data.get('expected_disposal_date')
        
        if purchase_date:
            # Purchase date cannot be in the future
            if purchase_date > timezone.now().date():
                raise ValidationError({
                    'purchase_date': 'Purchase date cannot be in the future.'
                })
            
            # Depreciation start date must be >= purchase date
            if depreciation_start_date and depreciation_start_date < purchase_date:
                raise ValidationError({
                    'depreciation_start_date': 'Depreciation start date cannot be before purchase date.'
                })
            
            # Warranty expiry should be after purchase date
            if warranty_expiry and warranty_expiry < purchase_date:
                raise ValidationError({
                    'warranty_expiry': 'Warranty expiry should be after purchase date.'
                })
            
            # Expected disposal date should be after purchase date
            if expected_disposal_date and expected_disposal_date <= purchase_date:
                raise ValidationError({
                    'expected_disposal_date': 'Expected disposal date should be after purchase date.'
                })
    
    def save(self, commit=True):
        """Override save to set company and created_by"""
        asset = super().save(commit=False)
        
        if not asset.pk:  # New asset
            if self.company:
                asset.company = self.company
            if self.user:
                asset.created_by = self.user
                
            # Auto-set depreciation start date if not provided
            if not asset.depreciation_start_date and asset.purchase_date:
                asset.depreciation_start_date = asset.purchase_date
        
        # Always set depreciation_basis to effective_life since we removed the choice
        asset.depreciation_basis = 'effective_life'
        
        if commit:
            asset.save()
        
        return asset


class AssetTypeForm(forms.ModelForm):
    """Form for managing asset types/categories"""
    
    class Meta:
        model = AssetType
        fields = ['name', 'code', 'default_life_years', 'default_depreciation_method', 'description', 'is_active']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Computer Equipment'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'COMP',
                'style': 'text-transform: uppercase;'
            }),
            'default_life_years': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '50'
            }),
            'default_depreciation_method': forms.Select(attrs={
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def clean_code(self):
        """Ensure code is uppercase and unique"""
        code = self.cleaned_data.get('code', '').upper()
        
        if len(code) > 10:
            raise ValidationError('Code must be 10 characters or less.')
        
        # Check uniqueness
        existing = AssetType.objects.filter(code=code)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        
        if existing.exists():
            raise ValidationError('An asset type with this code already exists.')
        
        return code


class AssetDisposalForm(forms.ModelForm):
    """Form for asset disposal"""
    
    class Meta:
        model = AssetDisposal
        fields = [
            'disposal_date', 'disposal_method', 'disposal_value',
            'buyer_details', 'disposal_costs'
        ]
        
        widgets = {
            'disposal_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'disposal_method': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'disposal_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.00',
                'required': True
            }),
            'buyer_details': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Details about buyer or disposal recipient'
            }),
            'disposal_costs': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.00'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.asset = kwargs.pop('asset', None)
        super().__init__(*args, **kwargs)
        
        # Set default disposal date to today
        if not self.instance.pk:
            self.fields['disposal_date'].initial = timezone.now().date()
    
    def clean_disposal_date(self):
        """Validate disposal date"""
        disposal_date = self.cleaned_data.get('disposal_date')
        
        if disposal_date:
            if disposal_date > timezone.now().date():
                raise ValidationError('Disposal date cannot be in the future.')
            
            if self.asset and disposal_date < self.asset.purchase_date:
                raise ValidationError('Disposal date cannot be before purchase date.')
        
        return disposal_date


class AssetSearchForm(forms.Form):
    """Form for searching and filtering assets"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search assets...'
        })
    )
    
    asset_type = forms.ModelChoiceField(
        queryset=AssetType.objects.filter(is_active=True),
        required=False,
        empty_label="All Types",
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(FixedAsset._meta.get_field('status').choices),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Location/Department'
        })
    )
    
    purchase_date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    purchase_date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )


class DepreciationRunForm(forms.Form):
    """Form for running depreciation calculations"""
    
    period_end_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'required': True
        }),
        help_text="End date for depreciation period"
    )
    
    create_journal_entries = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text="Create journal entries for depreciation"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Default to end of current month
        today = timezone.now().date()
        last_day = calendar.monthrange(today.year, today.month)[1]
        month_end = today.replace(day=last_day)
        
        self.fields['period_end_date'].initial = month_end
