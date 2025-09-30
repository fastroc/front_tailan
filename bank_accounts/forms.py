from django import forms
from django.core.validators import FileExtensionValidator
from .models import Account


class BankStatementUploadForm(forms.Form):
    """Enhanced form for uploading bank statements with Mongolian support"""
    
    statement_file = forms.FileField(
        label='Bank Statement File',
        help_text='Upload Excel (.xlsx, .xls) or CSV files. Mongolian Cyrillic files are automatically detected and translated.',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['csv', 'xlsx', 'xls'],
                message='Please upload Excel (.xlsx, .xls) or CSV files only.'
            )
        ],
        widget=forms.FileInput(
            attrs={
                'class': 'form-control',
                'accept': '.csv,.xlsx,.xls',
                'id': 'statementFile',
                'data-supported-formats': 'Excel (.xlsx, .xls) and CSV files'
            }
        )
    )
    
    account = forms.ModelChoiceField(
        queryset=Account.objects.none(),  # Will be set in __init__
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        help_text='Select the bank account for these transactions'
    )
    
    preserve_original = forms.BooleanField(
        initial=True,
        required=False,
        label='Preserve Original Document',
        help_text='Keep the original document unchanged for legal compliance',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    auto_verify_high_confidence = forms.BooleanField(
        initial=True,
        required=False,
        label='Auto-approve high confidence translations',
        help_text='Automatically verify translations with >80% confidence',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        if company:
            self.fields['account'].queryset = Account.objects.filter(
                company=company,
                account_type='CURRENT_ASSET',
                is_bank_account=True,
                is_active=True
            ).order_by('code', 'name')
    
    def clean_statement_file(self):
        file = self.cleaned_data.get('statement_file')
        
        if file:
            # Check file size (max 10MB)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File size cannot exceed 10MB.')
            
            # Check file type by content if possible
            file_name = file.name.lower()
            if not (file_name.endswith('.csv') or file_name.endswith('.xlsx') or file_name.endswith('.xls')):
                raise forms.ValidationError('Invalid file type. Only CSV and Excel files are supported.')
        
        return file


class TranslationVerificationForm(forms.Form):
    """Form for verifying translation results"""
    
    header_verified = forms.BooleanField(
        required=False,
        label='Header information is correctly translated',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    verification_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add any verification notes or corrections...'
            }
        ),
        label='Verification Notes'
    )
