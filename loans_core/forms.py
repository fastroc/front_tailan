"""
Forms for loan core functionality
"""
from django import forms
from .models import LoanProduct, LoanApplication, Loan
from loans_customers.models import Customer


class LoanProductForm(forms.ModelForm):
    """Form for creating and editing loan products"""
    
    class Meta:
        model = LoanProduct
        fields = [
            'name', 'code', 'category', 'description',
            'min_amount', 'max_amount', 'min_term_months', 'max_term_months',
            'default_interest_rate', 'allows_prepayment', 'prepayment_penalty_rate',
            'grace_period_days', 'late_fee_amount', 'late_fee_percentage',
            'is_active'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'min_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'max_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'min_term_months': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_term_months': forms.NumberInput(attrs={'class': 'form-control'}),
            'default_interest_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'prepayment_penalty_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'grace_period_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'late_fee_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'late_fee_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'allows_prepayment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class LoanApplicationForm(forms.ModelForm):
    """Form for creating loan applications"""
    
    class Meta:
        model = LoanApplication
        fields = [
            'customer', 'loan_product', 'requested_amount', 'term_months',
            'interest_rate', 'repayment_method', 'payment_frequency',
            'grace_period_months', 'balloon_payment_amount',
            'first_payment_date', 'purpose', 'collateral_description'
        ]
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'loan_product': forms.Select(attrs={'class': 'form-select'}),
            'requested_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'term_months': forms.NumberInput(attrs={'class': 'form-control'}),
            'interest_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'repayment_method': forms.Select(attrs={'class': 'form-select'}),
            'payment_frequency': forms.Select(attrs={'class': 'form-select'}),
            'grace_period_months': forms.NumberInput(attrs={'class': 'form-control'}),
            'balloon_payment_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'first_payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'purpose': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'collateral_description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
        
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        if company:
            # Filter customers and loan products by company
            self.fields['customer'].queryset = Customer.objects.filter(company=company, is_active=True)
            self.fields['loan_product'].queryset = LoanProduct.objects.filter(company=company, is_active=True)
        
        # Set default interest rate based on product selection
        if 'loan_product' in self.data:
            try:
                product_id = int(self.data.get('loan_product'))
                product = LoanProduct.objects.get(id=product_id)
                self.fields['interest_rate'].initial = product.default_interest_rate
            except (ValueError, LoanProduct.DoesNotExist):
                pass


class LoanApplicationApprovalForm(forms.ModelForm):
    """Form for approving/rejecting loan applications"""
    
    class Meta:
        model = LoanApplication
        fields = [
            'status', 'approved_amount', 'interest_rate', 'term_months',
            'approval_date', 'disbursement_date', 'rejection_reason', 'notes'
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'approved_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'interest_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'term_months': forms.NumberInput(attrs={'class': 'form-control'}),
            'approval_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'disbursement_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'rejection_reason': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }


class QuickLoanApplicationForm(forms.Form):
    """Simplified form for quick loan applications"""
    
    # Customer selection or creation
    existing_customer = forms.ModelChoiceField(
        queryset=Customer.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Select Existing Customer"
    )
    
    # New customer fields
    customer_type = forms.ChoiceField(
        choices=Customer.CUSTOMER_TYPE,
        initial='individual',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    first_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    phone_primary = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    national_id = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    monthly_income = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    
    # Loan details
    loan_product = forms.ModelChoiceField(
        queryset=LoanProduct.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    requested_amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    term_months = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    purpose = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        if company:
            self.fields['existing_customer'].queryset = Customer.objects.filter(
                company=company, is_active=True
            )
            self.fields['loan_product'].queryset = LoanProduct.objects.filter(
                company=company, is_active=True
            )
    
    def clean(self):
        cleaned_data = super().clean()
        existing_customer = cleaned_data.get('existing_customer')
        
        # Now that we have a popup for customer creation, 
        # we just require that a customer is selected
        if not existing_customer:
            self.add_error('existing_customer', 'Please select an existing customer or create a new one using the "New Customer" button.')
        
        return cleaned_data


class LoanDisbursementForm(forms.ModelForm):
    """Form for disbursing approved loans"""
    
    class Meta:
        model = Loan
        fields = ['disbursement_date', 'first_payment_date']
        widgets = {
            'disbursement_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'first_payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class LoanApplicationBulkUploadForm(forms.Form):
    """Form for bulk uploading loan applications from Excel/CSV"""
    file = forms.FileField(
        validators=[
            # File size validation (10MB max)
            lambda file: file.size <= 10 * 1024 * 1024 or forms.ValidationError('File size must be less than 10MB.')
        ],
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx,.csv',
            'id': 'id_file'
        }),
        help_text='Upload Excel (.xlsx) or CSV file with loan application data. Maximum file size: 10MB.'
    )
    
    def clean_file(self):
        file = self.cleaned_data['file']
        if file:
            # Check file extension
            allowed_extensions = ['.xlsx', '.csv']
            file_extension = file.name.lower().split('.')[-1]
            if f'.{file_extension}' not in allowed_extensions:
                raise forms.ValidationError('Only Excel (.xlsx) and CSV files are supported.')
        return file
