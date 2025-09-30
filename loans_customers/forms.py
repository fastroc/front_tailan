"""
Forms for customer management
"""
from django import forms
from .models import Customer, CustomerDocument


class CustomerForm(forms.ModelForm):
    """Form for creating and editing customers"""
    
    class Meta:
        model = Customer
        fields = [
            'customer_type', 'first_name', 'last_name', 'middle_name',
            'date_of_birth', 'national_id', 'email', 'phone_primary', 'phone_secondary',
            'street_address', 'city', 'state_province', 'postal_code', 'country',
            'employment_type', 'employer_name', 'job_title', 'employment_duration_months',
            'monthly_income', 'other_income', 'marital_status', 'dependents_count',
            'business_name', 'business_registration_number', 'business_type', 'years_in_business',
            'annual_revenue', 'monthly_expenses', 'existing_debt_payments',
            'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship',
            'credit_score', 'risk_rating', 'is_active'
        ]
        widgets = {
            'customer_type': forms.Select(attrs={'class': 'form-select'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'national_id': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_primary': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_secondary': forms.TextInput(attrs={'class': 'form-control'}),
            'street_address': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state_province': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'value': 'USA'}),
            'employment_type': forms.Select(attrs={'class': 'form-select'}),
            'employer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'job_title': forms.TextInput(attrs={'class': 'form-control'}),
            'employment_duration_months': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'monthly_income': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'other_income': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'marital_status': forms.Select(attrs={'class': 'form-select'}),
            'dependents_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'business_name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'business_type': forms.TextInput(attrs={'class': 'form-control'}),
            'years_in_business': forms.NumberInput(attrs={'class': 'form-control'}),
            'annual_revenue': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'monthly_expenses': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'existing_debt_payments': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_relationship': forms.TextInput(attrs={'class': 'form-control'}),
            'credit_score': forms.NumberInput(attrs={'class': 'form-control'}),
            'risk_rating': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make fields conditional based on customer type
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True
        self.fields['phone_primary'].required = True
        self.fields['national_id'].required = True

    def clean(self):
        cleaned_data = super().clean()
        customer_type = cleaned_data.get('customer_type')
        
        # Validate based on customer type
        if customer_type == 'individual':
            required_fields = ['first_name', 'last_name', 'date_of_birth']
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, 'This field is required for individual customers.')
        
        elif customer_type == 'business':
            if not cleaned_data.get('business_name'):
                self.add_error('business_name', 'Business name is required for business customers.')
        
        return cleaned_data


class QuickCustomerForm(forms.ModelForm):
    """Simplified form for quick customer creation"""
    
    class Meta:
        model = Customer
        fields = [
            'customer_type', 'first_name', 'last_name', 'email', 'phone_primary',
            'national_id', 'date_of_birth', 'monthly_income', 'employment_type',
            'business_name', 'business_registration_number', 'business_type',
            'annual_revenue', 'years_in_business'
        ]
        widgets = {
            'customer_type': forms.Select(attrs={'class': 'form-select'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_primary': forms.TextInput(attrs={'class': 'form-control'}),
            'national_id': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'monthly_income': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'employment_type': forms.Select(attrs={'class': 'form-select'}),
            'business_name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'business_type': forms.Select(attrs={'class': 'form-select'}, choices=[
                ('', 'Select Type'),
                ('corporation', 'Corporation'),
                ('llc', 'LLC'),
                ('partnership', 'Partnership'),
                ('sole_proprietorship', 'Sole Proprietorship'),
                ('nonprofit', 'Non-Profit'),
            ]),
            'annual_revenue': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'years_in_business': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make fields not required by default - we'll validate in clean()
        self.fields['first_name'].required = False
        self.fields['last_name'].required = False
        self.fields['business_name'].required = False

    def clean(self):
        cleaned_data = super().clean()
        customer_type = cleaned_data.get('customer_type')
        
        # Validate based on customer type
        if customer_type == 'individual':
            # For individuals, require first_name and last_name
            if not cleaned_data.get('first_name'):
                self.add_error('first_name', 'First name is required for individual customers.')
            if not cleaned_data.get('last_name'):
                self.add_error('last_name', 'Last name is required for individual customers.')
        
        elif customer_type == 'business':
            # For businesses, require business_name
            if not cleaned_data.get('business_name'):
                self.add_error('business_name', 'Business name is required for business customers.')
        
        return cleaned_data


class CustomerDocumentForm(forms.ModelForm):
    """Form for uploading customer documents"""
    
    class Meta:
        model = CustomerDocument
        fields = [
            'document_type', 'document_name', 'file_path', 'description',
            'issue_date', 'expiry_date', 'document_number'
        ]
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'document_name': forms.TextInput(attrs={'class': 'form-control'}),
            'file_path': forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'issue_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'document_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        document = super().save(commit=False)
        if document.file_path:
            document.file_size = document.file_path.size
        if commit:
            document.save()
        return document


class CustomerSearchForm(forms.Form):
    """Form for searching customers"""
    
    search_query = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, email, customer ID, or national ID...'
        })
    )
    customer_type = forms.ChoiceField(
        choices=[('', 'All Types')] + Customer.CUSTOMER_TYPE,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    risk_rating = forms.ChoiceField(
        choices=[('', 'All Ratings')] + [
            ('low', 'Low Risk'),
            ('medium', 'Medium Risk'),
            ('high', 'High Risk'),
            ('unrated', 'Not Rated'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_active = forms.ChoiceField(
        choices=[('', 'All'), ('true', 'Active'), ('false', 'Inactive')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class CustomerDocumentReviewForm(forms.ModelForm):
    """Form for reviewing customer documents"""
    
    class Meta:
        model = CustomerDocument
        fields = ['status', 'review_notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'review_notes': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }


class CustomerBulkUploadForm(forms.Form):
    """Form for bulk customer upload"""
    
    file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx,.csv'
        }),
        help_text='Upload Excel (.xlsx) or CSV file with customer data. Maximum file size: 10MB'
    )
    
    def clean_file(self):
        file = self.cleaned_data['file']
        
        # Check file size (10MB limit)
        if file.size > 10 * 1024 * 1024:
            raise forms.ValidationError('File size cannot exceed 10MB')
        
        # Check file extension
        valid_extensions = ['.xlsx', '.csv']
        if not any(file.name.lower().endswith(ext) for ext in valid_extensions):
            raise forms.ValidationError('Only Excel (.xlsx) and CSV files are allowed')
        
        return file
