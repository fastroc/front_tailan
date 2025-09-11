from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        """Run when Django starts up"""
        from django.conf import settings
        
        # Only auto-register admin in development
        if getattr(settings, 'DEBUG', False):
            try:
                from .admin_automation import auto_register_all_models, configure_admin_site
                # Auto-register all models when Django starts
                auto_register_all_models()
                configure_admin_site()
            except ImportError:
                pass  # Fail silently if automation not available
