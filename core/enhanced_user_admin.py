"""
Enhanced User Admin - Maximum Information Display
Shows all possible user data while maintaining password security
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from users.models import UserProfile


class UserProfileInline(admin.StackedInline):
    """Inline profile editor in User admin"""
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile Information'
    fields = (
        ('login_count', 'last_login_ip'),
        ('created_at',),
    )
    readonly_fields = ('created_at', 'login_count', 'last_login_ip')
    extra = 0


class EnhancedUserAdmin(BaseUserAdmin):
    """Enhanced User Admin with comprehensive user information"""
    
    inlines = [UserProfileInline]
    
    # Enhanced list display - shows maximum user info
    list_display = [
        'username_display',
        'email_display',
        'full_name_display',
        'status_display',
        'company_count_display',
        'last_login_display',
        'date_joined_display',
        'password_status_display'
    ]
    
    # Enhanced filtering options
    list_filter = [
        'is_active',
        'is_staff', 
        'is_superuser',
        'date_joined',
        'last_login',
        'groups',
    ]
    
    # Enhanced search capabilities
    search_fields = [
        'username', 
        'first_name', 
        'last_name', 
        'email',
    ]
    
    # Enhanced fieldsets with all user information
    fieldsets = (
        ('🔐 Authentication', {
            'fields': ('username', 'password_info_display', 'password')
        }),
        ('👤 Personal Information', {
            'fields': ('first_name', 'last_name', 'email')
        }),
        ('🔑 Permissions', {
            'fields': (
                'is_active', 
                'is_staff', 
                'is_superuser',
                'groups', 
                'user_permissions'
            ),
            'classes': ('collapse',)
        }),
        ('📅 Important Dates', {
            'fields': ('last_login', 'date_joined')
        }),
        ('📊 Account Analytics', {
            'fields': ('comprehensive_stats_display',),
            'classes': ('wide',)
        })
    )
    
    readonly_fields = [
        'password_info_display',
        'comprehensive_stats_display',
        'last_login',
        'date_joined'
    ]
    
    def username_display(self, obj):
        """Enhanced username with status indicators"""
        icons = []
        if obj.is_superuser:
            icons.append('👑')
        if obj.is_staff:
            icons.append('🛠️')
        if not obj.is_active:
            icons.append('🚫')
        
        return format_html(
            '{} <strong>{}</strong>',
            ''.join(icons),
            obj.username
        )
    username_display.short_description = "Username"
    username_display.admin_order_field = 'username'
    
    def email_display(self, obj):
        """Enhanced email display with verification status"""
        if obj.email:
            return format_html(
                '📧 <a href="mailto:{}">{}</a>',
                obj.email,
                obj.email
            )
        return format_html('<span style="color: red;">❌ No Email</span>')
    email_display.short_description = "Email"
    email_display.admin_order_field = 'email'
    
    def full_name_display(self, obj):
        """Full name with fallback"""
        full_name = obj.get_full_name()
        if full_name.strip():
            return format_html('👤 {}', full_name)
        return format_html('<span style="color: orange;">⚠️ No Name</span>')
    full_name_display.short_description = "Full Name"
    
    def status_display(self, obj):
        """Comprehensive status display"""
        if obj.is_active:
            color = "green"
            status = "✅ Active"
        else:
            color = "red"
            status = "❌ Inactive"
            
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, status
        )
    status_display.short_description = "Status"
    status_display.admin_order_field = 'is_active'
    
    def company_count_display(self, obj):
        """Show company access count"""
        try:
            from company.models import UserCompanyAccess
            count = UserCompanyAccess.objects.filter(user=obj).count()
            if count > 0:
                return format_html(
                    '<span style="color: green;">🏢 {} companies</span>',
                    count
                )
            return format_html('<span style="color: orange;">⚠️ No access</span>')
        except Exception:
            return format_html('<span style="color: gray;">? Unknown</span>')
    company_count_display.short_description = "Companies"
    
    def last_login_display(self, obj):
        """Enhanced last login display"""
        if obj.last_login:
            days_ago = (timezone.now() - obj.last_login).days
            if days_ago == 0:
                color = "green"
                text = "Today"
            elif days_ago <= 7:
                color = "blue"
                text = f"{days_ago} days ago"
            elif days_ago <= 30:
                color = "orange"
                text = f"{days_ago} days ago"
            else:
                color = "red"
                text = f"{days_ago} days ago"
                
            return format_html(
                '<span style="color: {};">📅 {}</span><br>'
                '<small>{}</small>',
                color, text,
                obj.last_login.strftime('%Y-%m-%d %H:%M')
            )
        return format_html('<span style="color: red;">❌ Never</span>')
    last_login_display.short_description = "Last Login"
    last_login_display.admin_order_field = 'last_login'
    
    def date_joined_display(self, obj):
        """Enhanced join date display"""
        days_ago = (timezone.now().date() - obj.date_joined.date()).days
        return format_html(
            '<span style="color: blue;">📅 {} days ago</span><br>'
            '<small>{}</small>',
            days_ago,
            obj.date_joined.strftime('%Y-%m-%d')
        )
    date_joined_display.short_description = "Joined"
    date_joined_display.admin_order_field = 'date_joined'
    
    def password_status_display(self, obj):
        """Password security status (no password shown!)"""
        if obj.password:
            # Analyze password hash to show security info
            parts = obj.password.split('$')
            if len(parts) >= 2:
                algorithm = parts[0]
                if algorithm == 'pbkdf2_sha256':
                    security = "🔒 Strong"
                    color = "green"
                elif algorithm in ['bcrypt', 'argon2']:
                    security = "🔐 Very Strong"
                    color = "green"
                else:
                    security = "⚠️ Weak"
                    color = "orange"
            else:
                security = "❓ Unknown"
                color = "gray"
                
            return format_html(
                '<span style="color: {};">{}</span>',
                color, security
            )
        return format_html('<span style="color: red;">❌ No Password</span>')
    password_status_display.short_description = "Password"
    
    def password_info_display(self, obj):
        """Detailed password security information"""
        if not obj.password:
            return format_html(
                '<div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 5px;">'
                '<strong style="color: #856404;">⚠️ No Password Set</strong><br>'
                '<small>User cannot log in until password is set.</small>'
                '</div>'
            )
        
        # Parse password hash
        parts = obj.password.split('$')
        if len(parts) >= 3:
            algorithm = parts[0]
            iterations = parts[1] if len(parts) > 1 else 'N/A'
            hash_length = len(obj.password)
            
            # Determine security level
            if algorithm in ['pbkdf2_sha256', 'bcrypt', 'argon2']:
                security_level = "🔐 High Security"
                security_color = "#28a745"
            else:
                security_level = "⚠️ Low Security"
                security_color = "#ffc107"
                
        else:
            algorithm = "Unknown"
            iterations = "N/A"
            hash_length = len(obj.password)
            security_level = "❓ Unknown Security"
            security_color = "#6c757d"
        
        return format_html(
            '''
            <div style="background: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; border-radius: 8px; max-width: 400px;">
                <div style="color: {}; font-weight: bold; margin-bottom: 10px;">{}</div>
                
                <table style="width: 100%; font-size: 12px;">
                    <tr><td><strong>Algorithm:</strong></td><td>{}</td></tr>
                    <tr><td><strong>Iterations:</strong></td><td>{}</td></tr>
                    <tr><td><strong>Hash Length:</strong></td><td>{} characters</td></tr>
                    <tr><td><strong>Created:</strong></td><td>{}</td></tr>
                </table>
                
                <div style="margin-top: 10px; padding: 8px; background: #e7f3ff; border-radius: 4px; font-size: 11px;">
                    <strong>🔒 Security Note:</strong><br>
                    Passwords are securely hashed using industry-standard encryption.<br>
                    Original passwords cannot be retrieved or displayed.<br>
                    Use "Change Password" to reset if needed.
                </div>
                
                <div style="margin-top: 8px;">
                    <a href="{}" style="background: #007cba; color: white; padding: 4px 8px; text-decoration: none; border-radius: 3px; font-size: 11px;">
                        🔑 Change Password
                    </a>
                </div>
            </div>
            ''',
            security_color, security_level,
            algorithm, iterations, hash_length,
            obj.date_joined.strftime('%Y-%m-%d'),
            reverse('admin:auth_user_password_change', args=[obj.id])
        )
    password_info_display.short_description = "Password Security Information"
    
    def comprehensive_stats_display(self, obj):
        """Comprehensive user analytics dashboard"""
        try:
            # Get profile info
            try:
                profile = obj.userprofile
                profile_complete = bool(profile.login_count > 0)
                profile_info = f"� Login Count: {profile.login_count}<br>� Last IP: {profile.last_login_ip or 'Unknown'}"
            except UserProfile.DoesNotExist:
                profile_complete = False
                profile_info = "❌ No profile created"
            
            # Get company access
            try:
                from company.models import UserCompanyAccess
                companies = UserCompanyAccess.objects.filter(user=obj)
                company_info = []
                for access in companies:
                    role_color = {"owner": "green", "admin": "blue", "user": "orange"}.get(access.role, "gray")
                    company_info.append(
                        f'<span style="color: {role_color};">🏢 {access.company.name} ({access.role})</span>'
                    )
                company_display = '<br>'.join(company_info) if company_info else "❌ No company access"
            except Exception:
                company_display = "? Company data unavailable"
            
            # Calculate account age
            account_age = (timezone.now().date() - obj.date_joined.date()).days
            
            # Login frequency
            if obj.last_login:
                days_since_login = (timezone.now() - obj.last_login).days
                if days_since_login == 0:
                    login_status = "🟢 Active today"
                elif days_since_login <= 7:
                    login_status = f"🟡 Last seen {days_since_login} days ago"
                else:
                    login_status = f"🔴 Inactive for {days_since_login} days"
            else:
                login_status = "🔴 Never logged in"
            
            return format_html(
                '''
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; max-width: 600px;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                        
                        <div>
                            <h4 style="color: #495057; margin: 0 0 10px 0;">📊 Account Overview</h4>
                            <table style="font-size: 12px; width: 100%;">
                                <tr><td><strong>User ID:</strong></td><td>#{}</td></tr>
                                <tr><td><strong>Username:</strong></td><td>{}</td></tr>
                                <tr><td><strong>Account Age:</strong></td><td>{} days</td></tr>
                                <tr><td><strong>Profile Complete:</strong></td><td>{}</td></tr>
                                <tr><td><strong>Login Status:</strong></td><td>{}</td></tr>
                            </table>
                        </div>
                        
                        <div>
                            <h4 style="color: #495057; margin: 0 0 10px 0;">🔑 Permissions</h4>
                            <table style="font-size: 12px; width: 100%;">
                                <tr><td><strong>Superuser:</strong></td><td>{}</td></tr>
                                <tr><td><strong>Staff:</strong></td><td>{}</td></tr>
                                <tr><td><strong>Active:</strong></td><td>{}</td></tr>
                                <tr><td><strong>Groups:</strong></td><td>{}</td></tr>
                                <tr><td><strong>Permissions:</strong></td><td>{}</td></tr>
                            </table>
                        </div>
                        
                    </div>
                    
                    <div style="margin-top: 15px;">
                        <h4 style="color: #495057; margin: 0 0 10px 0;">👤 Profile Information</h4>
                        <div style="background: white; padding: 10px; border-radius: 4px; font-size: 12px;">
                            {}
                        </div>
                    </div>
                    
                    <div style="margin-top: 15px;">
                        <h4 style="color: #495057; margin: 0 0 10px 0;">🏢 Company Access</h4>
                        <div style="background: white; padding: 10px; border-radius: 4px; font-size: 12px;">
                            {}
                        </div>
                    </div>
                    
                </div>
                ''',
                # Account Overview
                obj.id, obj.username, account_age,
                "✅ Complete" if profile_complete else "⚠️ Incomplete",
                login_status,
                
                # Permissions
                "✅ Yes" if obj.is_superuser else "❌ No",
                "✅ Yes" if obj.is_staff else "❌ No", 
                "✅ Active" if obj.is_active else "❌ Inactive",
                obj.groups.count(),
                obj.user_permissions.count(),
                
                # Profile & Company
                profile_info,
                company_display
            )
            
        except Exception as e:
            return format_html(
                '<div style="background: #f8d7da; padding: 10px; border-radius: 5px;">'
                '<strong>Error loading user statistics:</strong> {}</div>',
                str(e)
            )
    comprehensive_stats_display.short_description = "Complete User Analytics"


# Unregister default User admin and register enhanced version
admin.site.unregister(User)
admin.site.register(User, EnhancedUserAdmin)
