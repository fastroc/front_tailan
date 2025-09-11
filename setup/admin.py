from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import CompanySetupStatus


@admin.register(CompanySetupStatus)
class CompanySetupStatusAdmin(admin.ModelAdmin):
    """Enhanced admin interface for setup status management"""

    list_display = [
        "company_link",
        "completion_status",
        "progress_bar",
        "company_info_status",
        "accounts_status",
        "tax_status",
        "balance_status",
        "setup_started_at",
        "setup_completed_at",
    ]

    list_filter = [
        "company_info_complete",
        "accounts_complete",
        "tax_complete",
        "balance_complete",
        "setup_started_at",
        "setup_completed_at",
    ]

    search_fields = ["company__name", "company__legal_name", "notes"]

    readonly_fields = [
        "completion_percentage_display",
        "setup_progress_visual",
        "setup_started_at",
        "setup_completed_at",
        "next_step_display",
    ]

    fieldsets = [
        ("Company Information", {"fields": ["company", "current_step", "notes"]}),
        (
            "Setup Progress",
            {
                "fields": [
                    "completion_percentage_display",
                    "setup_progress_visual",
                    "next_step_display",
                ]
            },
        ),
        (
            "Setup Steps",
            {
                "fields": [
                    ("company_info_complete", "accounts_complete"),
                    ("tax_complete", "balance_complete"),
                ]
            },
        ),
        (
            "Timestamps",
            {
                "fields": ["setup_started_at", "setup_completed_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    ordering = ["-updated_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("company")

    # Custom display methods
    def company_link(self, obj):
        """Company name with link to company admin"""
        url = reverse("admin:company_company_change", args=[obj.company.pk])
        return format_html('<a href="{}">{}</a>', url, obj.company.name)

    company_link.short_description = "Company"
    company_link.admin_order_field = "company__name"

    def completion_status(self, obj):
        """Visual completion status"""
        percentage = obj.completion_percentage
        if percentage >= 100:
            return format_html(
                '<span style="color: green; font-weight: bold;">✅ Complete ({}%)</span>',
                percentage,
            )
        elif percentage >= 85:
            return format_html(
                '<span style="color: orange; font-weight: bold;">🎯 Ready ({}%)</span>',
                percentage,
            )
        elif percentage >= 50:
            return format_html(
                '<span style="color: blue; font-weight: bold;">🔄 In Progress ({}%)</span>',
                percentage,
            )
        elif percentage > 0:
            return format_html(
                '<span style="color: purple; font-weight: bold;">🚀 Started ({}%)</span>',
                percentage,
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">❌ Not Started (0%)</span>'
            )

    completion_status.short_description = "Status"

    def progress_bar(self, obj):
        """Visual progress bar"""
        percentage = obj.completion_percentage
        color = "green" if percentage >= 85 else "orange" if percentage >= 50 else "red"

        return format_html(
            """
            <div style="width: 100px; background: #f0f0f0; border: 1px solid #ddd; border-radius: 3px;">
                <div style="width: {}%; background: {}; height: 20px; border-radius: 3px; text-align: center; color: white; font-size: 12px; line-height: 20px;">
                    {}%
                </div>
            </div>
            """,
            percentage,
            color,
            percentage,
        )

    progress_bar.short_description = "Progress"

    def company_info_status(self, obj):
        return "✅" if obj.company_info_complete else "❌"

    company_info_status.short_description = "Info"

    def accounts_status(self, obj):
        return "✅" if obj.accounts_complete else "❌"

    accounts_status.short_description = "Accounts"

    def tax_status(self, obj):
        return "✅" if obj.tax_complete else "❌"

    tax_status.short_description = "Tax"

    def balance_status(self, obj):
        return "✅" if obj.balance_complete else "❌"

    balance_status.short_description = "Balance"

    def completion_percentage_display(self, obj):
        """Readonly completion percentage display"""
        return f"{obj.completion_percentage}%"

    completion_percentage_display.short_description = "Completion %"

    def setup_progress_visual(self, obj):
        """Visual setup progress with detailed breakdown"""
        steps = obj.get_completion_summary()
        html_parts = ['<div style="margin: 10px 0;">']

        for step_key, step_info in steps.items():
            status_icon = "✅" if step_info["complete"] else "❌"
            required_badge = "🔴 Required" if step_info["required"] else "🟡 Optional"

            html_parts.append(
                f"""
                <div style="padding: 5px; border: 1px solid #ddd; margin: 2px 0; border-radius: 3px;">
                    {status_icon} <strong>{step_info['name']}</strong> 
                    <span style="font-size: 12px; color: #666;">({step_info['weight']}% weight)</span>
                    <br>
                    <span style="font-size: 11px; color: #999;">{required_badge}</span>
                </div>
                """
            )

        html_parts.append("</div>")
        return mark_safe("".join(html_parts))

    setup_progress_visual.short_description = "Detailed Progress"

    def next_step_display(self, obj):
        """Display next step to complete"""
        next_step = obj.next_step
        if next_step == "complete":
            return format_html(
                '<span style="color: green; font-weight: bold;">🎉 Setup Complete!</span>'
            )
        elif next_step:
            step_names = {
                "company_info": "Company Information",
                "essential_accounts": "Essential Accounts",
                "opening_balance": "Opening Balances",
                "tax_setup": "Tax Configuration",
            }
            return format_html(
                '<span style="color: blue; font-weight: bold;">➡️ {}</span>',
                step_names.get(next_step, next_step.replace("_", " ").title()),
            )
        return "Unknown"

    next_step_display.short_description = "Next Step"

    # Custom actions
    actions = ["mark_company_info_complete", "mark_accounts_complete", "reset_setup"]

    def mark_company_info_complete(self, request, queryset):
        """Mark company info step as complete"""
        updated = queryset.update(company_info_complete=True)
        self.message_user(
            request, f"{updated} setup records marked with company info complete."
        )

    mark_company_info_complete.short_description = "Mark company info complete"

    def mark_accounts_complete(self, request, queryset):
        """Mark accounts step as complete"""
        updated = queryset.update(accounts_complete=True)
        self.message_user(
            request, f"{updated} setup records marked with accounts complete."
        )

    mark_accounts_complete.short_description = "Mark accounts complete"

    def reset_setup(self, request, queryset):
        """Reset setup status to beginning"""
        updated = queryset.update(
            company_info_complete=False,
            accounts_complete=False,
            tax_complete=False,
            balance_complete=False,
            setup_started_at=None,
            setup_completed_at=None,
            current_step="",
            notes="",
        )
        self.message_user(request, f"{updated} setup records have been reset.")

    reset_setup.short_description = "Reset setup status"
