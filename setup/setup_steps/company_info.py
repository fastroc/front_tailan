from django import forms
from ..base import BaseSetupStep
from company.models import Company


class CompanyInfoForm(forms.ModelForm):
    """Form for completing company information setup"""
    
    class Meta:
        model = Company
        fields = ['description', 'logo']
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief description of your business...'
            }),
            'logo': forms.FileInput(attrs={
                'class': 'form-control'
            })
        }


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
        form.instance = company
        form.save()
        
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
        context.update({
            'current_description': company.description,
            'current_logo': company.logo,
            'form': self.get_form_class()(instance=company) if request and request.method != 'POST' else None
        })
        return context
