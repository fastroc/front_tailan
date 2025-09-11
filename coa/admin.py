from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Account, TaxRate, OpeningBalance


@admin.register(TaxRate)
class TaxRateAdmin(admin.ModelAdmin):
    """Enhanced Tax Rate admin showing company separation with setup integration"""

    list_display = [
        "tax_info_display",
        "company",
        "rate_display",
        "tax_details_display",
        "setup_status_display",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "company",
        "tax_type",
        "is_active",
        "is_default",
        "setup_created",
        "tax_authority",
        "created_at",
    ]
    search_fields = ["name", "company__name", "tax_authority", "description"]
    ordering = ["company__name", "-is_default", "name"]
    raw_id_fields = ["company"]

    fieldsets = (
        (
            "💰 Tax Rate Information",
            {
                "fields": (
                    "company",
                    "name",
                    "rate",
                    ("tax_type", "tax_authority"),
                    "description",
                )
            },
        ),
        (
            "⚙️ Setup & Status",
            {"fields": (("is_active", "is_default", "setup_created"))},
        ),
        (
            "🕒 Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("company")

    def tax_info_display(self, obj):
        """Tax name with enhanced formatting"""
        html = "<strong>{}</strong>".format(obj.name)
        if obj.description:
            description_truncated = obj.description[:50] + ("..." if len(obj.description) > 50 else "")
            html += '<br><small style="color: #666;">{}</small>'.format(description_truncated)
        return mark_safe(html)

    tax_info_display.short_description = "Tax Information"
    tax_info_display.admin_order_field = "name"

    def rate_display(self, obj):
        rate_percentage = "{:.2f}%".format(obj.rate * 100)
        return format_html(
            '<span style="background: #e3f2fd; padding: 2px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            rate_percentage,
        )

    rate_display.short_description = "Rate"
    rate_display.admin_order_field = "rate"

    def tax_details_display(self, obj):
        """Tax type and authority information"""
        parts = []
        if obj.tax_type:
            type_colors = {
                "SALES": "#28a745",
                "PURCHASE": "#dc3545",
                "PAYROLL": "#fd7e14",
                "INCOME": "#6f42c1",
                "OTHER": "#6c757d",
            }
            color = type_colors.get(obj.tax_type, "#6c757d")
            parts.append(
                '<span style="color: {}; font-weight: bold;">{}</span>'.format(color, obj.get_tax_type_display())
            )

        if obj.tax_authority:
            parts.append("<small>Authority: {}</small>".format(obj.tax_authority))

        return mark_safe("<br>".join(parts)) if parts else "-"

    tax_details_display.short_description = "Tax Details"

    def setup_status_display(self, obj):
        """Setup and status indicators"""
        indicators = []
        if obj.is_default:
            indicators.append(
                '<span style="color: #fd7e14; font-weight: bold;">⭐ Default</span>'
            )
        if obj.setup_created:
            indicators.append('<span style="color: #6f42c1;">🔧 Setup</span>')
        return mark_safe("<br>".join(indicators)) if indicators else "-"

    setup_status_display.short_description = "Status"


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    """Enhanced Account admin showing complete company data separation"""

    list_display = [
        "code",
        "name",
        "company",
        "account_type_display",
        "parent_account",
        "is_active",
        "ytd_balance_display",
        "created_at",
    ]
    list_filter = ["company", "account_type", "is_active", "is_locked", "created_at"]
    search_fields = ["name", "code", "company__name", "description"]
    ordering = ["company__name", "code", "name"]
    raw_id_fields = ["parent_account", "tax_rate", "company"]
    readonly_fields = ["get_account_details", "created_at", "updated_at"]

    fieldsets = (
        (
            "🏦 Account Information",
            {"fields": ("company", "code", "name", "account_type", "parent_account")},
        ),
        (
            "⚙️ Settings & Configuration",
            {
                "fields": ("tax_rate", "description", "is_active", "is_locked"),
            },
        ),
        (
            "💰 Financial Information",
            {"fields": ("ytd_balance",), "classes": ("collapse",)},
        ),
        (
            "📊 Account Details",
            {"fields": ("get_account_details",), "classes": ("collapse",)},
        ),
        (
            "🕒 Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("company", "parent_account", "tax_rate")
        )

    def account_type_display(self, obj):
        type_colors = {
            "CURRENT_ASSET": "#4caf50",
            "FIXED_ASSET": "#2196f3",
            "INVENTORY": "#ff9800",
            "EQUITY": "#9c27b0",
            "EXPENSE": "#f44336",
            "REVENUE": "#8bc34a",
            "CURRENT_LIABILITY": "#e91e63",
            "LIABILITY": "#795548",
        }
        color = type_colors.get(obj.account_type, "#607d8b")
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 0.8em;">{}</span>',
            color,
            obj.get_account_type_display(),
        )

    account_type_display.short_description = "Type"
    account_type_display.admin_order_field = "account_type"

    def ytd_balance_display(self, obj):
        balance = obj.ytd_balance
        color = "#4caf50" if balance >= 0 else "#f44336"
        formatted_balance = "${:,.2f}".format(balance)
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            formatted_balance,
        )

    ytd_balance_display.short_description = "YTD Balance"
    ytd_balance_display.admin_order_field = "ytd_balance"

    def get_account_details(self, obj):
        # Get child accounts count
        try:
            children_count = Account.objects.filter(parent_account=obj).count()
        except Exception:
            children_count = 0

        # Calculate hierarchy level
        hierarchy_level = 0
        parent = obj.parent_account
        while parent:
            hierarchy_level += 1
            parent = parent.parent_account
            if hierarchy_level > 10:  # Safety break
                break

        return format_html(
            '<div style="background: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #17a2b8;">'
            '<h4 style="margin: 0 0 10px 0; color: #495057;">🏦 Account Details</h4>'
            "<p><strong>🏢 Company:</strong> {}</p>"
            "<p><strong>🔢 Full Account Code:</strong> {} - {}</p>"
            "<p><strong>📊 Account Type:</strong> {}</p>"
            "<p><strong>🌳 Hierarchy Level:</strong> {}</p>"
            "<p><strong>👥 Child Accounts:</strong> {}</p>"
            "<p><strong>💰 Tax Rate:</strong> {}</p>"
            "<p><strong>🔒 Status:</strong> {}</p>"
            "</div>",
            obj.company.name,
            obj.code,
            obj.name,
            obj.get_account_type_display(),
            hierarchy_level,
            children_count,
            obj.tax_rate.name if obj.tax_rate else "None",
            (
                "🔒 Locked"
                if obj.is_locked
                else ("✅ Active" if obj.is_active else "❌ Inactive")
            ),
        )

    get_account_details.short_description = "Detailed Information"

    # Custom admin actions
    actions = [
        "activate_accounts",
        "deactivate_accounts",
        "lock_accounts",
        "unlock_accounts",
    ]

    def activate_accounts(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, "✅ {} accounts were activated.".format(updated))

    activate_accounts.short_description = "✅ Activate selected accounts"

    def deactivate_accounts(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, "❌ {} accounts were deactivated.".format(updated))

    deactivate_accounts.short_description = "❌ Deactivate selected accounts"

    def lock_accounts(self, request, queryset):
        updated = queryset.update(is_locked=True)
        self.message_user(request, "🔒 {} accounts were locked.".format(updated))

    lock_accounts.short_description = "🔒 Lock selected accounts"

    def unlock_accounts(self, request, queryset):
        updated = queryset.update(is_locked=False)
        self.message_user(request, "🔓 {} accounts were unlocked.".format(updated))

    unlock_accounts.short_description = "🔓 Unlock selected accounts"


@admin.register(OpeningBalance)
class OpeningBalanceAdmin(admin.ModelAdmin):
    """Enhanced Opening Balance admin with full audit trail"""

    list_display = [
        "balance_entry_display",
        "company",
        "account_info_display",
        "balance_amount_display",
        "audit_info_display",
        "is_active",
    ]

    list_filter = [
        "company",
        "is_active",
        "balance_date",
        "entered_at",
        "account__account_type",
        "account__is_essential",
    ]

    search_fields = [
        "account__code",
        "account__name",
        "description",
        "company__name",
        "entered_by__username",
    ]

    ordering = ["company", "-balance_date", "account__code"]

    fieldsets = [
        (
            "💰 Balance Information",
            {
                "fields": [
                    ("company", "account"),
                    ("balance_amount", "balance_date"),
                    "description",
                ]
            },
        ),
        (
            "👤 Audit Trail",
            {
                "fields": [("entered_by",), "is_active"],
                "classes": ["collapse"],
            },
        ),
        (
            "🕒 Timestamps",
            {"fields": ["entered_at"], "classes": ["collapse"]},
        ),
    ]

    readonly_fields = ["entered_at"]
    raw_id_fields = ["company", "account", "entered_by"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "company", "account", "entered_by"
            )
        )

    def save_model(self, request, obj, form, change):
        """Auto-populate entered_by field"""
        if not change:  # Only on create, not update
            obj.entered_by = request.user
        super().save_model(request, obj, form, change)

    def balance_entry_display(self, obj):
        """Balance date with entry information"""
        html = "<strong>{}</strong>".format(obj.balance_date)
        if obj.entered_by:
            html += '<br><small style="color: #666;">Entry by: {}</small>'.format(obj.entered_by.username)
        return mark_safe(html)

    balance_entry_display.short_description = "📅 Balance Entry"
    balance_entry_display.admin_order_field = "balance_date"

    def account_info_display(self, obj):
        """Account code and name with essential flag"""
        html = "<strong>{}</strong>".format(obj.account.code)
        if obj.account.name:
            html += "<br>{}".format(obj.account.name)

        # Add account type indicator
        type_colors = {
            "CURRENT_ASSET": "#4caf50",
            "FIXED_ASSET": "#2196f3",
            "INVENTORY": "#ff9800",
            "EQUITY": "#9c27b0",
            "EXPENSE": "#f44336",
            "REVENUE": "#8bc34a",
            "CURRENT_LIABILITY": "#e91e63",
            "LIABILITY": "#795548",
        }
        color = type_colors.get(obj.account.account_type, "#607d8b")
        html += '<br><small style="color: {}; font-weight: bold;">{}</small>'.format(color, obj.account.get_account_type_display())

        if obj.account.is_essential:
            html += '<br><span style="color: #dc3545; font-size: 11px; font-weight: bold;">🔴 Essential</span>'

        return mark_safe(html)

    account_info_display.short_description = "🏦 Account"

    def balance_amount_display(self, obj):
        """Formatted balance amount with color coding"""
        if obj.balance_amount is not None:
            color = "#28a745" if obj.balance_amount >= 0 else "#dc3545"
            symbol = "+" if obj.balance_amount >= 0 else ""
            formatted_amount = "{:,.2f}".format(obj.balance_amount)
            return format_html(
                '<span style="color: {}; font-weight: bold; font-size: 14px;">{}{}</span>',
                color,
                symbol,
                formatted_amount,
            )
        return format_html('<span style="color: #6c757d;">0.00</span>')

    balance_amount_display.short_description = "💰 Amount"
    balance_amount_display.admin_order_field = "balance_amount"

    def audit_info_display(self, obj):
        """Comprehensive audit trail information"""
        parts = []
        if obj.entered_by:
            parts.append('<strong>Entered by:</strong> {}'.format(obj.entered_by.username))
        
        # Add timestamps
        if parts:
            parts.append('<small>Entered: {}</small>'.format(obj.entered_at.strftime("%m/%d/%Y")))
        
        return mark_safe('<br>'.join(parts)) if parts else 'No audit trail'
    audit_info_display.short_description = '👤 Audit Trail'

    # Enhanced custom actions
    actions = [
        "activate_balances",
        "deactivate_balances",
        "update_account_balances",
        "mark_as_verified",
    ]

    def activate_balances(self, request, queryset):
        """Activate selected opening balances"""
        updated = queryset.update(is_active=True)
        self.message_user(request, "✅ {} opening balances activated.".format(updated))

    activate_balances.short_description = "✅ Activate selected balances"

    def deactivate_balances(self, request, queryset):
        """Deactivate selected opening balances"""
        updated = queryset.update(is_active=False)
        self.message_user(request, "❌ {} opening balances deactivated.".format(updated))

    deactivate_balances.short_description = "❌ Deactivate selected balances"

    def update_account_balances(self, request, queryset):
        """Update current balance on related accounts from opening balance"""
        updated_count = 0
        for balance_entry in queryset.filter(is_active=True):
            if balance_entry.account:
                balance_entry.account.current_balance = balance_entry.balance_amount
                balance_entry.account.save(update_fields=["current_balance"])
                updated_count += 1

        self.message_user(
            request,
            "🔄 {} account current balances updated from opening balance entries.".format(updated_count),
        )

    update_account_balances.short_description = "🔄 Update account current balances"

    def mark_as_verified(self, request, queryset):
        """Mark selected balances as verified by updating description"""
        updated_count = 0
        for balance_entry in queryset:
            if not balance_entry.description or "VERIFIED" not in balance_entry.description:
                current_description = balance_entry.description or ""
                balance_entry.description = "{}\nVERIFIED by {} on {}".format(
                    current_description, 
                    request.user.username, 
                    balance_entry.entered_at.strftime('%Y-%m-%d')
                )
                balance_entry.save()
                updated_count += 1

        self.message_user(
            request, "✓ {} opening balances marked as verified.".format(updated_count)
        )

    mark_as_verified.short_description = "✓ Mark as verified"
