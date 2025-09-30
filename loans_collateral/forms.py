from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal

from .models import Collateral, CollateralType, CollateralValuation, CollateralDocument
from loans_core.models import LoanApplication


class CollateralForm(forms.ModelForm):
    """Form for creating and editing collateral items"""
    
    class Meta:
        model = Collateral
        fields = [
            'loan_application', 'collateral_type', 'title', 'description',
            'location', 'condition', 'owner_name', 'ownership_document',
            'registration_number', 'declared_value', 'market_value', 'status',
            'verification_notes', 'insurance_required',
            'insurance_policy_number', 'insurance_expiry_date', 'insurance_value',
            # Vehicle-specific fields
            'vehicle_make', 'vehicle_model', 'vehicle_year', 'vehicle_registration_year',
            'vehicle_license_plate', 'vehicle_vin', 'vehicle_mileage', 'vehicle_fuel_type'
        ]
        
        widgets = {
            'loan_application': forms.Select(attrs={
                'class': 'form-control loan-application-select', 
                'required': True,
                'data-bs-toggle': 'tooltip',
                'title': 'Select the loan application this collateral secures',
                'style': 'width: 100%;'
            }),
            'collateral_type': forms.Select(attrs={
                'class': 'form-control',
                'required': True,
                'id': 'id_collateral_type',
                'data-bs-toggle': 'tooltip',
                'title': 'Choose the type of collateral'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a brief title for the collateral',
                'maxlength': 200
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Provide detailed description of the collateral item...'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Physical location or address of the collateral'
            }),
            'condition': forms.Select(attrs={
                'class': 'form-control'
            }),
            'owner_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Legal owner name as per documents'
            }),
            'ownership_document': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Title Deed #TD-2023-456'
            }),
            'registration_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Registration or identification number'
            }),
            'declared_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'market_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'verification_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes or comments...'
            }),
            'insurance_required': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'id_insurance_required'
            }),
            'insurance_policy_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Insurance policy number (if applicable)'
            }),
            'insurance_expiry_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'insurance_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            # Vehicle-specific field widgets
            'vehicle_make': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Toyota, BMW, Ford'
            }),
            'vehicle_model': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Camry, X5, F-150'
            }),
            'vehicle_year': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1900',
                'max': '2030',
                'placeholder': 'e.g., 2022'
            }),
            'vehicle_registration_year': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1900',
                'max': '2030',
                'placeholder': 'e.g., 2023'
            }),
            'vehicle_license_plate': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., ABC-1234',
                'style': 'text-transform: uppercase;'
            }),
            'vehicle_vin': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '17-character VIN number',
                'maxlength': '17',
                'style': 'text-transform: uppercase;'
            }),
            'vehicle_mileage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'Current mileage'
            }),
            'vehicle_fuel_type': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get enhanced loan application queryset with loan numbers and customer info
        loan_apps_with_loans = []
        for app in LoanApplication.objects.filter(
            status__in=['submitted', 'under_review', 'approved']
        ).select_related('customer', 'loan'):
            
            # Try to get the associated loan number
            loan_number = None
            try:
                loan = app.loan
                if loan:
                    loan_number = loan.loan_number
            except Exception:
                pass
            
            loan_apps_with_loans.append((app, loan_number))
        
        # Create choices with enhanced display
        choices = [('', '--- Select Loan Application ---')]
        for app, loan_number in loan_apps_with_loans:
            # Format the display text
            if loan_number:
                display_text = f"{loan_number} - {app.customer.full_name} (${app.requested_amount:,.0f})"
            else:
                display_text = f"{app.application_id} - {app.customer.full_name} (${app.requested_amount:,.0f})"
            
            choices.append((app.id, display_text))
        
        # Set the choices for the loan application field
        self.fields['loan_application'].choices = choices
        
        # Set queryset for validation
        self.fields['loan_application'].queryset = LoanApplication.objects.filter(
            status__in=['submitted', 'under_review', 'approved']
        ).select_related('customer')
        
        # Filter active collateral types only
        self.fields['collateral_type'].queryset = CollateralType.objects.filter(
            is_active=True
        ).order_by('category', 'name')
        
        # Customize field labels and help texts
        self.fields['loan_application'].label = 'Loan Application'
        self.fields['loan_application'].help_text = 'Search by customer first name or click to see all available loans with loan numbers'
        
        self.fields['collateral_type'].label = 'Collateral Type'
        self.fields['collateral_type'].help_text = 'Type determines LTV ratio and risk assessment'
        
        # Set field labels and help text for the new fields
        self.fields['declared_value'].label = 'Declared Value ($)'
        self.fields['declared_value'].help_text = 'Value as declared by the applicant'
        
        self.fields['market_value'].label = 'Market Value ($)'
        self.fields['market_value'].help_text = 'Current market value assessment'
        
        self.fields['status'].label = 'Status'
        self.fields['status'].help_text = 'Current status of the collateral item'
        self.fields['status'].initial = 'pending'  # Set default value
        
        self.fields['verification_notes'].label = 'Additional Notes'
        self.fields['verification_notes'].help_text = 'Notes, comments, or verification details'
        
        # Make insurance fields conditional
        self.fields['insurance_policy_number'].required = False
        self.fields['insurance_expiry_date'].required = False
        self.fields['insurance_value'].required = False
        
        # Make vehicle fields conditional (not required by default)
        self.fields['vehicle_make'].required = False
        self.fields['vehicle_model'].required = False
        self.fields['vehicle_year'].required = False
        self.fields['vehicle_registration_year'].required = False
        self.fields['vehicle_license_plate'].required = False
        self.fields['vehicle_vin'].required = False
        self.fields['vehicle_mileage'].required = False
        self.fields['vehicle_fuel_type'].required = False
        
        # Make status not required since we set a default
        self.fields['status'].required = False
        
        # Add labels for vehicle fields
        self.fields['vehicle_make'].label = 'Make'
        self.fields['vehicle_model'].label = 'Model'
        self.fields['vehicle_year'].label = 'Manufactured Year'
        self.fields['vehicle_registration_year'].label = 'Registration Year'
        self.fields['vehicle_license_plate'].label = 'License Plate'
        self.fields['vehicle_vin'].label = 'VIN Number'
        self.fields['vehicle_mileage'].label = 'Mileage'
        self.fields['vehicle_fuel_type'].label = 'Fuel Type'
    
    def clean_declared_value(self):
        value = self.cleaned_data.get('declared_value')
        if value and value <= 0:
            raise ValidationError('Declared value must be greater than zero.')
        return value
    
    def clean_insurance_value(self):
        insurance_required = self.cleaned_data.get('insurance_required')
        insurance_value = self.cleaned_data.get('insurance_value')
        
        if insurance_required and not insurance_value:
            raise ValidationError('Insurance value is required when insurance is marked as required.')
        
        if insurance_value and insurance_value <= 0:
            raise ValidationError('Insurance value must be greater than zero.')
        
        return insurance_value
    
    def clean(self):
        cleaned_data = super().clean()
        insurance_required = cleaned_data.get('insurance_required')
        insurance_policy_number = cleaned_data.get('insurance_policy_number')
        insurance_expiry_date = cleaned_data.get('insurance_expiry_date')
        
        # Validate insurance requirements
        if insurance_required:
            if not insurance_policy_number:
                self.add_error('insurance_policy_number', 'Policy number is required when insurance is required.')
            if not insurance_expiry_date:
                self.add_error('insurance_expiry_date', 'Expiry date is required when insurance is required.')
        
        # Validate vehicle fields if collateral type is vehicle
        collateral_type = cleaned_data.get('collateral_type')
        if collateral_type and collateral_type.category == 'vehicle':
            vehicle_make = cleaned_data.get('vehicle_make')
            vehicle_model = cleaned_data.get('vehicle_model')
            vehicle_year = cleaned_data.get('vehicle_year')
            vehicle_license_plate = cleaned_data.get('vehicle_license_plate')
            
            if not vehicle_make:
                self.add_error('vehicle_make', 'Make is required for vehicle collateral.')
            if not vehicle_model:
                self.add_error('vehicle_model', 'Model is required for vehicle collateral.')
            if not vehicle_year:
                self.add_error('vehicle_year', 'Manufactured year is required for vehicle collateral.')
            if not vehicle_license_plate:
                self.add_error('vehicle_license_plate', 'License plate is required for vehicle collateral.')
            
            # Validate year ranges
            if vehicle_year and (vehicle_year < 1900 or vehicle_year > 2030):
                self.add_error('vehicle_year', 'Please enter a valid manufactured year.')
            
            vehicle_registration_year = cleaned_data.get('vehicle_registration_year')
            if vehicle_registration_year and vehicle_year:
                if vehicle_registration_year < vehicle_year:
                    self.add_error('vehicle_registration_year', 'Registration year cannot be earlier than manufactured year.')
        
        # Check for potential duplicates
        if not self.errors:  # Only check duplicates if no other validation errors
            try:
                from .duplicate_detector import detect_collateral_duplicates
                
                # Prepare data for duplicate detection
                duplicate_data = cleaned_data.copy()
                
                # Get the current instance ID if this is an update
                exclude_id = None
                if hasattr(self, 'instance') and self.instance.pk:
                    exclude_id = self.instance.collateral_id
                
                # Detect duplicates
                duplicate_results = detect_collateral_duplicates(
                    duplicate_data, 
                    exclude_id=exclude_id
                )
                
                # Check for high-risk duplicates (exact matches or high probability)
                if duplicate_results['exact_matches']:
                    exact_match = duplicate_results['exact_matches'][0]
                    collateral = exact_match['collateral']
                    error_message = (
                        f"Exact duplicate detected: {exact_match['reason']} "
                        f"(Existing: {collateral.collateral_id} - {collateral.title})"
                    )
                    
                    # Add error to the relevant field
                    if exact_match['match_type'] == 'exact_vin':
                        self.add_error('vehicle_vin', error_message)
                    elif exact_match['match_type'] == 'exact_license_plate':
                        self.add_error('vehicle_license_plate', error_message)
                    elif exact_match['match_type'] == 'exact_registration':
                        self.add_error('registration_number', error_message)
                    else:
                        self.add_error(None, error_message)
                
                # Store duplicate results for use in the view (warning purposes)
                self._duplicate_results = duplicate_results
                
            except Exception:
                # Don't fail validation if duplicate detection has issues
                # Log the error in production
                pass
        
        return cleaned_data


class CollateralTypeForm(forms.ModelForm):
    """Form for creating and editing collateral types"""
    
    class Meta:
        model = CollateralType
        fields = [
            'name', 'category', 'description', 'max_loan_to_value',
            'depreciation_rate', 'risk_level', 'liquidity_score',
            'requires_insurance', 'requires_professional_valuation', 'is_active'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'max_loan_to_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'depreciation_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'risk_level': forms.Select(attrs={'class': 'form-control'}),
            'liquidity_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '10'
            }),
            'requires_insurance': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'requires_professional_valuation': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CollateralValuationForm(forms.ModelForm):
    """Form for creating collateral valuations"""
    
    class Meta:
        model = CollateralValuation
        fields = [
            'valuation_type', 'valuer_type', 'valuer_name', 'valuer_license',
            'assessed_value', 'forced_sale_value', 'valuation_date',
            'report_reference', 'methodology', 'key_assumptions', 'limitations',
            'valid_until'
        ]
        
        widgets = {
            'valuation_type': forms.Select(attrs={'class': 'form-control'}),
            'valuer_type': forms.Select(attrs={'class': 'form-control'}),
            'valuer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'valuer_license': forms.TextInput(attrs={'class': 'form-control'}),
            'assessed_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'forced_sale_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'valuation_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'report_reference': forms.TextInput(attrs={'class': 'form-control'}),
            'methodology': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'key_assumptions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'limitations': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'valid_until': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }


class CollateralSearchForm(forms.Form):
    """Form for searching and filtering collateral"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by ID, title, customer name...',
        })
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + Collateral.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    collateral_type = forms.ModelChoiceField(
        required=False,
        queryset=CollateralType.objects.filter(is_active=True),
        empty_label='All Types',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    value_range = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Values'),
            ('0-10000', 'Under $10,000'),
            ('10000-50000', '$10,000 - $50,000'),
            ('50000-100000', '$50,000 - $100,000'),
            ('100000-500000', '$100,000 - $500,000'),
            ('500000+', 'Over $500,000'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
