from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import UserProfile
from company.models import UserCompanyAccess, UserCompanyPreference


class UserProfileInline(admin.StackedInline):
    """Inline profile display in user admin."""
    model = UserProfile
    can_delete = False
    verbose_name_plural = '👤 Profile Information'
    fields = ('login_count', 'last_login_ip', 'created_at')
    readonly_fields = ('created_at',)


class UserCompanyAccessInline(admin.TabularInline):
    """Inline for user company access management."""
    model = UserCompanyAccess
    extra = 0
    verbose_name = '🏢 Company Access'
    verbose_name_plural = '🏢 Company Access & Roles'
    fields = ('company', 'role', 'is_active', 'created_at')
    readonly_fields = ('created_at',)
    raw_id_fields = ('company',)


class UserCompanyPreferenceInline(admin.StackedInline):
    """Inline for user company preferences."""
    model = UserCompanyPreference
    can_delete = False
    verbose_name = '⚙️ Company Preference'
    verbose_name_plural = '⚙️ Company Preferences'
    fields = ('active_company',)
    raw_id_fields = ('active_company',)


class UserAdmin(BaseUserAdmin):
    """Enhanced User admin with company information and profile."""
    inlines = (UserProfileInline, UserCompanyAccessInline, UserCompanyPreferenceInline)
    
    # Enhanced list display
    list_display = (
        'username', 
        'email', 
        'first_name', 
        'last_name', 
        'company_count_display',
        'default_company_display',
        'is_staff', 
        'is_active',
        'get_login_count'
    )
    
    # Enhanced list filters
    list_filter = (
        'is_staff', 
        'is_superuser', 
        'is_active', 
        'date_joined',
        'last_login'
    )
    
    # Enhanced search
    search_fields = (
        'username', 'email', 'first_name', 'last_name',
        'usercompanyaccess__company__name'
    )
    
    # Ordering
    ordering = ('-date_joined',)
    
    # Fields to display in detail view
    fieldsets = BaseUserAdmin.fieldsets + (
        ('🏢 Multi-Company Information', {
            'fields': ('get_company_summary',),
            'classes': ('collapse',),
            'description': 'Company access and preferences are managed in the sections below.'
        }),
    )
    
    readonly_fields = BaseUserAdmin.readonly_fields + ('get_company_summary',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            'company_access__company',
            'company_preference'
        )
    
    def company_count_display(self, obj):
        """Display number of companies user has access to."""
        count = obj.company_access.count()
        if count == 0:
            return format_html('<span style="color: #666;">No access</span>')
        elif count == 1:
            return format_html(
                '<span style="background: #e3f2fd; padding: 2px 6px; border-radius: 3px;">1 company</span>'
            )
        else:
            return format_html(
                '<span style="background: #1976d2; color: white; padding: 2px 6px; border-radius: 3px;">{} companies</span>',
                count
            )
    company_count_display.short_description = '🏢 Companies'
    
    def default_company_display(self, obj):
        """Display user's default company."""
        try:
            default_company = obj.company_preference.active_company
            if default_company:
                return format_html(
                    '<span style="background: #4caf50; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.9em;">{}</span>',
                    default_company.name
                )
            return format_html('<span style="color: #666;">Not set</span>')
        except Exception:
            return format_html('<span style="color: #666;">No preference</span>')
    default_company_display.short_description = '🎯 Default Company'
    
    def get_login_count(self, obj):
        """Get login count from profile."""
        try:
            count = obj.userprofile.login_count
            if count > 50:
                color = '#4caf50'  # Green for active users
            elif count > 10:
                color = '#ff9800'  # Orange for moderate users
            else:
                color = '#666'     # Gray for new users
            
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color,
                count
            )
        except UserProfile.DoesNotExist:
            return format_html('<span style="color: #f44336;">0</span>')
    get_login_count.short_description = '🔢 Logins'
    get_login_count.admin_order_field = 'userprofile__login_count'
    
    def get_company_summary(self, obj):
        """Display comprehensive company access summary."""
        try:
            access_records = obj.company_access.select_related('company').all()
            preference = getattr(obj, 'company_preference', None)
            
            if not access_records:
                return format_html(
                    '<div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px;">'
                    '<h4 style="margin: 0; color: #856404;">⚠️ No Company Access</h4>'
                    '<p style="margin: 5px 0 0 0;">This user has no company access configured.</p>'
                    '</div>'
                )
            
            html_parts = [
                '<div style="background: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #007bff;">'
                '<h4 style="margin: 0 0 15px 0; color: #495057;">🏢 Company Access Summary</h4>'
            ]
            
            # Default company info
            if preference and preference.active_company:
                html_parts.append(
                    '<p><strong>🎯 Default Company:</strong> '
                    '<span style="background: #28a745; color: white; padding: 2px 8px; border-radius: 3px;">'
                    '{}</span></p>'.format(preference.active_company.name)
                )
            
            # Company access list
            html_parts.append('<p><strong>📋 Company Access:</strong></p><ul style="margin: 5px 0;">')
            
            for access in access_records:
                status_color = '#28a745' if hasattr(access, 'is_active') and access.is_active else '#dc3545'
                status_text = '✅ Active' if hasattr(access, 'is_active') and access.is_active else '✅ Active'
                role_color = {
                    'owner': '#6f42c1',
                    'admin': '#dc3545', 
                    'manager': '#fd7e14',
                    'accountant': '#20c997',
                    'viewer': '#6c757d'
                }.get(access.role, '#007bff')
                
                html_parts.append(
                    '<li style="margin: 5px 0;">'
                    '<strong>{}</strong> - '
                    '<span style="background: {}; color: white; padding: 1px 6px; border-radius: 3px; font-size: 0.8em;">'
                    '{}</span> '
                    '<span style="color: {}; font-weight: bold;">{}</span>'
                    '</li>'.format(
                        access.company.name,
                        role_color,
                        access.get_role_display(),
                        status_color,
                        status_text
                    )
                )
            
            html_parts.append('</ul></div>')
            
            return format_html(''.join(html_parts))
            
        except Exception as e:
            return format_html(
                '<div style="background: #f8d7da; border: 1px solid #f5c6cb; padding: 10px; border-radius: 5px;">'
                '<strong style="color: #721c24;">Error loading company summary: {}</strong>'
                '</div>',
                str(e)
            )
    get_company_summary.short_description = 'Company Access Summary'


# @admin.register(UserProfile)  # Disabled - using auto-registration
class UserProfileAdmin(admin.ModelAdmin):
    """Enhanced UserProfile admin with company context."""
    list_display = (
        'user', 
        'get_username', 
        'get_email',
        'get_company_count',
        'login_count', 
        'last_login_ip', 
        'created_at'
    )
    
    list_filter = ('created_at', 'login_count')
    search_fields = (
        'user__username', 'user__email', 'user__first_name', 'user__last_name',
        'user__usercompanyaccess__company__name'
    )
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user').prefetch_related(
            'user__company_access'
        )
    
    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'
    get_username.admin_order_field = 'user__username'
    
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'
    get_email.admin_order_field = 'user__email'
    
    def get_company_count(self, obj):
        """Display number of companies for this user."""
        count = obj.user.company_access.count()
        if count == 0:
            return format_html('<span style="color: #666;">0</span>')
        else:
            return format_html(
                '<span style="background: #17a2b8; color: white; padding: 2px 6px; border-radius: 3px;">{}</span>',
                count
            )
    get_company_count.short_description = '🏢 Companies'


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# Customize admin site headers
admin.site.site_header = "Professional Accounting System - Administration"
admin.site.site_title = "Accounting Admin"
admin.site.index_title = "Welcome to Accounting System Administration"
