from django.apps import AppConfig


class FinancialRulesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'financial_rules'
    verbose_name = 'Financial Rules'
    
    def ready(self):
        """Initialize the financial rules system when Django starts"""
        pass
