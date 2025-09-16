from django import forms
from datetime import date
from ..base import BaseSetupStep
from company.models import Company


class CompanyInfoForm(forms.ModelForm):
    """Form for completing company information setup"""
    
    # Fiscal year selection fields
    fiscal_year_end_month = forms.ChoiceField(
        choices=[
            (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
            (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
            (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
        ],
        initial=12,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Month when your financial year ends"
    )
    
    fiscal_year_end_day = forms.ChoiceField(
        choices=[(i, i) for i in range(1, 32)],
        initial=31,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Day when your financial year ends"
    )
    
    class Meta:
        model = Company
        fields = ['description', 'logo', 'fiscal_year_start']
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief description of your business...'
            }),
            'logo': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'fiscal_year_start': forms.HiddenInput()  # We'll calculate this from end date
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If we have an instance with fiscal_year_start, populate the fields
        if self.instance and self.instance.fiscal_year_start:
            fiscal_start = self.instance.fiscal_year_start
            # Calculate fiscal year end (start + 1 year - 1 day)
            from datetime import timedelta
            try:
                fiscal_end = date(fiscal_start.year + 1, fiscal_start.month, fiscal_start.day) - timedelta(days=1)
                self.fields['fiscal_year_end_month'].initial = fiscal_end.month
                self.fields['fiscal_year_end_day'].initial = fiscal_end.day
            except ValueError:
                # Handle leap year edge case
                fiscal_end = date(fiscal_start.year + 1, fiscal_start.month, 28)
                self.fields['fiscal_year_end_month'].initial = fiscal_end.month
                self.fields['fiscal_year_end_day'].initial = fiscal_end.day
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Calculate fiscal_year_start from the end date
        end_month = int(cleaned_data.get('fiscal_year_end_month', 12))
        end_day = int(cleaned_data.get('fiscal_year_end_day', 31))
        
        print(f"DEBUG: Fiscal year end month: {end_month}, day: {end_day}")
        
        # Calculate the start date (end date + 1 day - 1 year)
        current_year = date.today().year
        try:
            fiscal_end = date(current_year, end_month, end_day)
            # Start is the day after the end date, but previous year
            from datetime import timedelta
            fiscal_start = fiscal_end + timedelta(days=1)
            fiscal_start = fiscal_start.replace(year=fiscal_start.year - 1)
            
            print(f"DEBUG: Calculated fiscal_start: {fiscal_start}")
            cleaned_data['fiscal_year_start'] = fiscal_start
        except ValueError as e:
            # Handle invalid dates (like Feb 31)
            print(f"DEBUG: Date calculation error: {e}")
            raise forms.ValidationError("Invalid fiscal year end date.")
        
        return cleaned_data

    def save(self, commit=True):
        """Override save to ensure fiscal_year_start is properly set"""
        instance = super().save(commit=False)
        
        # Explicitly set fiscal_year_start from cleaned_data
        if hasattr(self, 'cleaned_data') and 'fiscal_year_start' in self.cleaned_data:
            instance.fiscal_year_start = self.cleaned_data['fiscal_year_start']
            print(f"DEBUG: Setting fiscal_year_start to: {instance.fiscal_year_start}")
        
        if commit:
            instance.save()
            print(f"DEBUG: Company saved with fiscal_year_start: {instance.fiscal_year_start}")
        
        return instance


class CompanyInfoSetupStep(BaseSetupStep):
    """Company information setup step"""
    
    name = "Company Information"
    description = "Complete your business profile with additional details"
    priority = 1
    required = False  # Basic info already collected during company creation
    url_name = "company_info"
    template_name = "setup/company_info.html"
    
    def is_complete(self, company):
        """Check if company info is reasonably complete"""
        return bool(company.description)
    
    def get_form_class(self):
        return CompanyInfoForm
    
    def process_form(self, form, company, request):
        """Save company information"""
        # Debug: Print the cleaned data
        print(f"DEBUG: Form cleaned_data: {form.cleaned_data}")
        print(f"DEBUG: Fiscal year start from form: {form.cleaned_data.get('fiscal_year_start')}")
        
        form.instance = company
        saved_company = form.save()
        
        # Debug: Print the saved company data
        print(f"DEBUG: Saved company fiscal_year_start: {saved_company.fiscal_year_start}")
        
        # Update setup status
        from setup.models import CompanySetupStatus
        setup_status, created = CompanySetupStatus.objects.get_or_create(
            company=company
        )
        setup_status.company_info_complete = True
        setup_status.save()
        
        return True
    
    def get_context(self, company, request=None):
        context = super().get_context(company, request)
        
        # Calculate fiscal year end date if fiscal_year_start exists
        fiscal_year_end = None
        if company.fiscal_year_start:
            from datetime import timedelta
            try:
                fiscal_year_end = date(
                    company.fiscal_year_start.year + 1,
                    company.fiscal_year_start.month,
                    company.fiscal_year_start.day
                ) - timedelta(days=1)
            except ValueError:
                # Handle leap year edge case
                fiscal_year_end = date(
                    company.fiscal_year_start.year + 1,
                    company.fiscal_year_start.month,
                    28
                )
        
        context.update({
            'current_description': company.description,
            'current_logo': company.logo,
            'fiscal_year_end': fiscal_year_end,
            'form': self.get_form_class()(instance=company) if request and request.method != 'POST' else None
        })
        return context
