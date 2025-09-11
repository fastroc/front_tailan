"""
Automated Admin Registration System for Development
Automatically registers all models with enhanced admin interfaces
"""
from django.contrib import admin
from django.apps import apps
from django.utils.html import format_html
from django.urls import reverse
from django.conf import settings

class AutoEnhancedModelAdmin(admin.ModelAdmin):
    """Enhanced admin class that automatically configures itself based on model fields"""
    
    def __init__(self, model, admin_site):
        # Auto-configure based on model
        self.model = model
        self.list_display = self.get_smart_list_display()
        self.list_filter = self.get_smart_list_filter()
        self.search_fields = self.get_smart_search_fields()
        self.list_per_page = getattr(settings, 'ADMIN_PAGINATOR_PAGE_SIZE', 50)
        self.ordering = self.get_smart_ordering()
        
        # Enhanced display options
        self.list_display_links = self.get_smart_display_links()
        self.date_hierarchy = self.get_date_hierarchy()
        
        super().__init__(model, admin_site)
    
    def get_smart_list_display(self):
        """Auto-generate smart list_display"""
        fields = []
        
        # Add ID first if requested AND if it exists
        if (getattr(settings, 'DEBUG', False) and 
            hasattr(self.model, 'id') and
            'id' in [f.name for f in self.model._meta.fields]):
            fields.append('id')
        
        # Priority fields (common important fields)
        priority_fields = ['name', 'title', 'code', 'number', 'amount', 'date', 'created_at']
        
        for field_name in priority_fields:
            if hasattr(self.model, field_name) and field_name not in fields:
                fields.append(field_name)
        
        # Add other fields up to limit
        for field in self.model._meta.fields:
            if (len(fields) < 8 and 
                field.name not in fields and 
                not field.name.endswith('_id') and
                field.get_internal_type() not in ['TextField', 'JSONField']):
                fields.append(field.name)
        
        # Add foreign key display methods
        for field in self.model._meta.fields:
            if field.get_internal_type() == 'ForeignKey' and len(fields) < 10:
                method_name = f'get_{field.name}_display'
                if not hasattr(self, method_name):
                    self.add_foreign_key_display(field.name)
                fields.append(method_name)
        
        return fields or ['__str__']
    
    def add_foreign_key_display(self, field_name):
        """Dynamically add foreign key display method"""
        def display_method(self, obj):
            related_obj = getattr(obj, field_name, None)
            if related_obj:
                try:
                    url = reverse(f'admin:{related_obj._meta.app_label}_{related_obj._meta.model_name}_change', 
                                args=[related_obj.pk])
                    return format_html('<a href="{}">{}</a>', url, str(related_obj))
                except Exception:
                    return str(related_obj)
            return '-'
        
        display_method.short_description = field_name.replace('_', ' ').title()
        display_method.allow_tags = True
        setattr(self.__class__, f'get_{field_name}_display', display_method)
    
    def get_smart_list_filter(self):
        """Auto-generate smart list_filter"""
        filters = []
        
        for field in self.model._meta.fields:
            if len(filters) >= 6:
                break
                
            field_type = field.get_internal_type()
            
            if field_type in ['BooleanField']:
                filters.append(field.name)
            elif field_type in ['DateField', 'DateTimeField']:
                filters.append(field.name)
            elif field_type == 'ForeignKey':
                filters.append(field.name)
            elif (field_type == 'CharField' and 
                  hasattr(field, 'choices') and field.choices):
                filters.append(field.name)
        
        return filters
    
    def get_smart_search_fields(self):
        """Auto-generate smart search_fields"""
        fields = []
        
        for field in self.model._meta.fields:
            if len(fields) >= 5:
                break
                
            field_type = field.get_internal_type()
            
            if field_type in ['CharField', 'TextField']:
                # Add exact and partial matching
                if 'name' in field.name.lower() or 'title' in field.name.lower():
                    fields.append(field.name)
                else:
                    fields.append(f'{field.name}__icontains')
        
        return fields
    
    def get_smart_ordering(self):
        """Auto-generate smart ordering"""
        # Look for common ordering fields
        ordering_fields = ['created_at', 'date', 'name', 'title', 'id']
        
        for field_name in ordering_fields:
            if hasattr(self.model, field_name):
                # Use descending for dates, ascending for names
                if 'date' in field_name or 'created' in field_name:
                    return [f'-{field_name}']
                else:
                    return [field_name]
        
        return []
    
    def get_smart_display_links(self):
        """Auto-generate smart display_links"""
        if hasattr(self.model, 'name'):
            return ['name']
        elif hasattr(self.model, 'title'):
            return ['title']
        return None
    
    def get_date_hierarchy(self):
        """Auto-generate date_hierarchy"""
        for field in self.model._meta.fields:
            if (field.get_internal_type() in ['DateField', 'DateTimeField'] and 
                'created' in field.name):
                return field.name
        return None


def auto_register_all_models():
    """
    Automatically register all models from all apps with enhanced admin
    Only runs in DEBUG mode for development
    """
    if not getattr(settings, 'DEBUG', False):
        return
    
    registered_count = 0
    
    for app_config in apps.get_app_configs():
        # Skip Django's built-in apps
        if app_config.name.startswith('django.'):
            continue
        
        app_models = []
        
        for model in app_config.get_models():
            # Skip if already registered (avoid conflicts with manual registrations)
            if admin.site.is_registered(model):
                continue
            
            # Register with enhanced admin
            try:
                admin.site.register(model, AutoEnhancedModelAdmin)
                app_models.append(model.__name__)
                registered_count += 1
            except Exception as e:
                if settings.DEBUG:
                    print(f"Could not register {model}: {e}")
        
        if app_models and settings.DEBUG:
            print(f"✅ Auto-registered {len(app_models)} models from {app_config.name}: {', '.join(app_models)}")
    
    if settings.DEBUG and registered_count > 0:
        print(f"🚀 Total auto-registered models: {registered_count}")
    elif settings.DEBUG:
        print("ℹ️ All models already registered - automation complete")


# Enhanced admin site configuration
def configure_admin_site():
    """Configure admin site with enhanced settings"""
    if getattr(settings, 'DEBUG', False):
        # Site headers
        admin.site.site_header = getattr(settings, 'ADMIN_SITE_HEADER', 
                                       "🏢 Multi-Company Accounting System - Development")
        admin.site.site_title = getattr(settings, 'ADMIN_SITE_TITLE', 
                                      "Accounting Admin")
        admin.site.index_title = getattr(settings, 'ADMIN_INDEX_TITLE', 
                                       "Database Management & Structure Viewer")
        
        # Enhanced admin templates
        admin.site.enable_nav_sidebar = True


# Auto-run the registration
if getattr(settings, 'DEBUG', False):
    auto_register_all_models()
    configure_admin_site()
