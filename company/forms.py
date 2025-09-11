from django import forms
from django.core.exceptions import ValidationError
from .models import Company


class SimpleCompanyForm(forms.ModelForm):
    """Simple company creation form - KISS principle!"""
    
    class Meta:
        model = Company
        fields = ['name', 'description', 'logo']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter company name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Brief description of your company (optional)',
                'rows': 3
            }),
            'logo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }
        
        labels = {
            'name': 'Company Name',
            'description': 'Description',
            'logo': 'Company Logo',
        }
        
        help_texts = {
            'name': 'This will be displayed throughout the system',
            'description': 'Tell us what your company does (optional)',
            'logo': 'Upload a company logo (optional)',
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            if len(name) < 2:
                raise ValidationError('Company name must be at least 2 characters long.')
        return name
    
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


class CompanySettingsForm(forms.ModelForm):
    """Simple company settings form"""
    
    class Meta:
        model = Company
        fields = ['name', 'description', 'logo', 'is_active']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter company name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Brief description of your company (optional)',
                'rows': 3
            }),
            'logo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        
        labels = {
            'name': 'Company Name',
            'description': 'Description',
            'logo': 'Company Logo',
            'is_active': 'Company is Active',
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            if len(name) < 2:
                raise ValidationError('Company name must be at least 2 characters long.')
        return name
