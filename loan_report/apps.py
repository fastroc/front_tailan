from django.apps import AppConfig


class LoanReportConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'loan_report'
    verbose_name = 'Loan Reports & Analytics'
    
    def ready(self):
        """
        Initialize the loan report module
        """
        # Import signals or other initialization code here if needed
        pass
