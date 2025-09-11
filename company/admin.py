from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html
from .models import Company, UserCompanyAccess, UserCompanyPreference


class UserCompanyAccessInline(admin.TabularInline):
    model = UserCompanyAccess
    extra = 0
    fields = ["user", "role", "created_at"]  # Removed is_active
    readonly_fields = ["created_at"]
    verbose_name = "User Access"
    verbose_name_plural = "User Access Permissions"


class UserCompanyPreferenceInline(admin.TabularInline):
    model = UserCompanyPreference
    extra = 0
    fields = ["user", "active_company", "created_at"]
    readonly_fields = ["created_at"]
    verbose_name = "User Preference"
    verbose_name_plural = "User Preferences"


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """Enhanced Company admin interface showing multi-company data structure"""

    inlines = [UserCompanyAccessInline, UserCompanyPreferenceInline]
    list_display = [
        "company_info_display",
        "business_details_display",
        "contact_info_display",
        "setup_status_display",
        "user_count",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "is_active",
        "business_type",
        "industry",
        "country",
        "setup_complete",
        "base_currency",
        "created_at",
        "owner",
    ]
    search_fields = [
        "name",
        "legal_name",
        "industry",
        "business_type",
        "tax_id",
        "email",
        "phone",
        "city",
        "country",
        "description",
        "owner__username",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
        "get_statistics",
        "setup_progress_display",
        "financial_summary_display",
    ]
    ordering = ["-created_at"]

    fieldsets = (
        (
            "🏢 Basic Company Information",
            {
                "fields": (
                    ("name", "legal_name"),
                    ("business_type", "industry"),
                    "tax_id",
                    "description",
                    ("owner", "is_active"),
                )
            },
        ),
        (
            "📞 Contact Information",
            {
                "fields": (
                    ("email", "phone", "website"),
                    "address",
                    ("city", "state", "postal_code"),
                    "country",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "💼 Financial Settings",
            {
                "fields": (("base_currency", "fiscal_year_start"), "setup_complete"),
                "classes": ("collapse",),
            },
        ),
        (
            "📊 Setup Progress & Statistics",
            {
                "fields": (
                    "setup_progress_display",
                    "financial_summary_display",
                    "get_statistics",
                ),
                "classes": ("collapse",),
                "description": "Live data about company setup and usage",
            },
        ),
        (
            "🕒 Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return (
            queryset.select_related("owner")
            .prefetch_related("companysetupstatus_set")
            .annotate(user_count_annotated=Count("user_access", distinct=True))
        )

    # Enhanced display methods
    def company_info_display(self, obj):
        """Company name with legal name and tax info"""
        html = f"<strong>{obj.name}</strong>"
        if obj.legal_name and obj.legal_name != obj.name:
            html += f'<br><small style="color: #666;">Legal: {obj.legal_name}</small>'
        if obj.tax_id:
            html += f'<br><small style="color: #007bff;">Tax ID: {obj.tax_id}</small>'
        return format_html(html)

    company_info_display.short_description = "🏢 Company"
    company_info_display.admin_order_field = "name"

    def business_details_display(self, obj):
        """Business type and industry info"""
        parts = []
        if obj.business_type:
            parts.append(
                f'<span style="color: #28a745; font-weight: bold;">{obj.get_business_type_display()}</span>'
            )
        if obj.industry:
            parts.append(f'<small style="color: #6c757d;">{obj.industry}</small>')
        if obj.base_currency:
            parts.append(
                f'<small style="color: #dc3545;">💱 {obj.base_currency}</small>'
            )
        return format_html("<br>".join(parts)) if parts else "-"

    business_details_display.short_description = "💼 Business"

    def contact_info_display(self, obj):
        """Contact and location info"""
        parts = []
        if obj.email:
            parts.append(f"<small>📧 {obj.email}</small>")
        if obj.phone:
            parts.append(f"<small>📞 {obj.phone}</small>")
        if obj.city and obj.country:
            parts.append(f"<small>� {obj.city}, {obj.country}</small>")
        elif obj.country:
            parts.append(f"<small>📍 {obj.country}</small>")
        return format_html("<br>".join(parts)) if parts else "-"

    contact_info_display.short_description = "📞 Contact"

    def setup_status_display(self, obj):
        """Setup completion status with visual indicators"""
        if obj.setup_complete:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">✅ Complete</span>'
            )

        try:
            setup_status = obj.companysetupstatus_set.first()
            if setup_status:
                percentage = setup_status.completion_percentage
                if percentage >= 85:
                    return format_html(
                        '<span style="color: #fd7e14; font-weight: bold;">🎯 {}%</span>',
                        percentage,
                    )
                elif percentage >= 50:
                    return format_html(
                        '<span style="color: #0d6efd; font-weight: bold;">🔄 {}%</span>',
                        percentage,
                    )
                elif percentage > 0:
                    return format_html(
                        '<span style="color: #6f42c1; font-weight: bold;">🚀 {}%</span>',
                        percentage,
                    )
        except Exception:
            pass

        return format_html(
            '<span style="color: #dc3545; font-weight: bold;">❌ Not Started</span>'
        )

    setup_status_display.short_description = "⚙️ Setup Status"

    def setup_progress_display(self, obj):
        """Detailed setup progress for readonly field"""
        if obj.setup_complete:
            return format_html(
                '<div style="background: #d1edff; padding: 10px; border-left: 4px solid #28a745; border-radius: 3px;">'
                '<strong style="color: #28a745;">✅ Setup Complete</strong><br>'
                "<small>Company is fully configured and ready to use.</small>"
                "</div>"
            )

        try:
            setup_status = obj.companysetupstatus_set.first()
            if setup_status:
                percentage = setup_status.completion_percentage
                next_step = setup_status.next_step
                completion_summary = setup_status.get_completion_summary()

                color = (
                    "#28a745"
                    if percentage >= 85
                    else "#fd7e14" if percentage >= 50 else "#dc3545"
                )

                html = f"""
                <div style="background: #f8f9fa; padding: 10px; border-left: 4px solid {color}; border-radius: 3px;">
                    <strong>Setup Progress: {percentage}%</strong><br>
                """

                if next_step and next_step != "complete":
                    step_names = {
                        "company_info": "Company Information",
                        "essential_accounts": "Essential Accounts",
                        "opening_balance": "Opening Balances",
                        "tax_setup": "Tax Configuration",
                    }
                    html += f"<small>Next Step: {step_names.get(next_step, next_step)}</small><br>"

                html += '<div style="margin-top: 5px;">'
                for step_key, step_info in completion_summary.items():
                    status_icon = "✅" if step_info["complete"] else "❌"
                    html += f'<small>{status_icon} {step_info["name"]} ({step_info["weight"]}%)</small><br>'

                html += "</div></div>"
                return format_html(html)
        except Exception:
            pass

        return format_html(
            '<div style="background: #f8d7da; padding: 10px; border-left: 4px solid #dc3545; border-radius: 3px;">'
            '<strong style="color: #dc3545;">❌ Setup Not Started</strong><br>'
            "<small>Company setup has not been initiated.</small>"
            "</div>"
        )

    setup_progress_display.short_description = "Detailed Setup Progress"

    def financial_summary_display(self, obj):
        """Financial configuration summary"""
        parts = []

        if obj.base_currency:
            parts.append(f"<strong>Base Currency:</strong> {obj.base_currency}")

        if obj.fiscal_year_start:
            parts.append(f"<strong>Fiscal Year:</strong> {obj.fiscal_year_start}")

        # Get account and tax rate counts
        try:
            from coa.models import Account, TaxRate

            account_count = Account.objects.filter(company=obj).count()
            tax_rate_count = TaxRate.objects.filter(company=obj).count()

            parts.append(f"<strong>Accounts:</strong> {account_count}")
            parts.append(f"<strong>Tax Rates:</strong> {tax_rate_count}")
        except Exception:
            pass

        if parts:
            return format_html(
                '<div style="background: #e7f3ff; padding: 10px; border-left: 4px solid #0d6efd; border-radius: 3px;">'
                "{}"
                "</div>",
                "<br>".join(parts),
            )

        return "No financial data configured"

    financial_summary_display.short_description = "Financial Configuration"

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related("owner").annotate(
            user_count_annotated=Count("user_access", distinct=True)
        )

    def user_count(self, obj):
        return getattr(obj, "user_count_annotated", obj.user_access.count())

    user_count.short_description = "👥 Users"
    user_count.admin_order_field = "user_count_annotated"

    def account_count(self, obj):
        from coa.models import Account

        count = Account.objects.filter(company=obj).count()
        return f"{count}"

    account_count.short_description = "🏦 Accounts"

    def tax_rate_count(self, obj):
        from coa.models import TaxRate

        count = TaxRate.objects.filter(company=obj).count()
        return f"{count}"

    tax_rate_count.short_description = "💰 Tax Rates"

    def get_statistics(self, obj):
        from coa.models import Account, TaxRate
        from django.utils.html import format_html

        accounts = Account.objects.filter(company=obj).count()
        tax_rates = TaxRate.objects.filter(company=obj).count()
        users = obj.user_access.count()

        return format_html(
            '<div style="background: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #007bff;">'
            '<h4 style="margin: 0 0 10px 0; color: #495057;">📊 Company Data Overview</h4>'
            "<p><strong>👥 Users with Access:</strong> {}</p>"
            "<p><strong>🏦 Chart of Accounts:</strong> {} accounts</p>"
            "<p><strong>💰 Tax Rates:</strong> {} rates</p>"
            "<p><strong>🏢 Company Status:</strong> {}</p>"
            "</div>",
            users,
            accounts,
            tax_rates,
            "✅ Active" if obj.is_active else "❌ Inactive",
        )

    get_statistics.short_description = "Company Statistics"


@admin.register(UserCompanyAccess)
class UserCompanyAccessAdmin(admin.ModelAdmin):
    """Enhanced User Company Access admin"""

    list_display = ["user", "company", "role", "created_at"]
    list_filter = ["role", "created_at", "company"]
    search_fields = ["user__username", "user__email", "company__name"]
    raw_id_fields = ["user", "company"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    fieldsets = (
        ("🔑 Access Information", {"fields": ("user", "company", "role")}),
        ("🕒 Timestamps", {"fields": ("created_at",), "classes": ("collapse",)}),
    )

    readonly_fields = ["created_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "company")


@admin.register(UserCompanyPreference)
class UserCompanyPreferenceAdmin(admin.ModelAdmin):
    """Enhanced User Company Preference admin"""

    list_display = ["user", "active_company", "created_at"]
    list_filter = ["created_at", "active_company"]
    search_fields = ["user__username", "active_company__name"]
    raw_id_fields = ["user", "active_company"]
    ordering = ["-created_at"]

    fieldsets = (
        ("⚙️ Preference Information", {"fields": ("user", "active_company")}),
        (
            "🕒 Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "active_company")


# Customize admin site headers
admin.site.site_header = "🏢 Multi-Company Accounting System - Administration"
admin.site.site_title = "Accounting Admin"
admin.site.index_title = "📊 Multi-Company Data Structure Dashboard"
