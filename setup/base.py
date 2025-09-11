"""
Base classes for modular setup steps
"""

class BaseSetupStep:
    """Base class for all setup steps"""
    
    name = ""
    description = ""
    priority = 0
    required = False
    url_name = ""
    template_name = ""
    
    def __init__(self, company=None):
        self.company = company
    
    def is_complete(self, company):
        """Check if this setup step is complete for the company"""
        raise NotImplementedError("Subclasses must implement is_complete()")
    
    def get_context(self, company, request=None):
        """Get context data for rendering the setup step"""
        return {
            'step_name': self.name,
            'step_description': self.description,
            'is_complete': self.is_complete(company),
            'company': company
        }
    
    def can_start(self, company):
        """Check if this step can be started (dependencies met)"""
        return True
    
    def get_form_class(self):
        """Return the form class for this setup step"""
        return None
    
    def process_form(self, form, company, request):
        """Process the completed form"""
        raise NotImplementedError("Subclasses must implement process_form()")
    
    def get_success_url(self, company):
        """URL to redirect to after successful completion"""
        return '/setup/'
    
    def get_status_class(self, company):
        """Return CSS class for status display"""
        if self.is_complete(company):
            return 'success'
        elif self.required:
            return 'danger'
        else:
            return 'warning'
    
    def get_status_icon(self, company):
        """Return icon class for status display"""
        if self.is_complete(company):
            return 'bi bi-check-circle-fill text-success'
        elif self.required:
            return 'bi bi-exclamation-circle-fill text-danger'
        else:
            return 'bi bi-clock text-warning'
