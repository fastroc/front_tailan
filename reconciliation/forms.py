from django import forms
from .models import UploadedFile


class CSVUploadForm(forms.ModelForm):
    """Form for uploading CSV bank statement files"""
    
    class Meta:
        model = UploadedFile
        fields = ['file', 'bank_account_name', 'statement_period']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file'].widget.attrs.update({
            'class': 'form-control',
            'accept': '.csv',
            'required': True
        })
        self.fields['bank_account_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'e.g., Business Account - ANZ'
        })
        self.fields['statement_period'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'e.g., January 2025'
        })
        
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            if not file.name.lower().endswith('.csv'):
                raise forms.ValidationError("Only CSV files are allowed.")
            if file.size > 10 * 1024 * 1024:  # 10MB limit
                raise forms.ValidationError("File size cannot exceed 10MB.")
        return file