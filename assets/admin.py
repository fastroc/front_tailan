"""
Fixed Asset Admin Configuration
Comprehensive admin interfaces for asset management
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse

from .models import AssetType, FixedAsset, DepreciationSchedule, AssetTransaction, AssetDisposal


@admin.register(AssetType)
class AssetTypeAdmin(admin.ModelAdmin):
    """Admin interface for Asset Types"""
    list_display = ['name', 'code', 'default_life_years', 'default_depreciation_method', 'asset_count', 'is_active']
    list_filter = ['is_active', 'default_depreciation_method']
    search_fields = ['name', 'code', 'description']
    ordering = ['name']
    
    def asset_count(self, obj):
        """Display count of assets using this type"""
        count = obj.fixedasset_set.count()
        if count > 0:
            url = reverse('admin:assets_fixedasset_changelist') + f'?asset_type__id__exact={obj.id}'
            return format_html('<a href="{}">{} assets</a>', url, count)
        return '0 assets'
    asset_count.short_description = 'Assets Using Type'


@admin.register(FixedAsset)
class FixedAssetAdmin(admin.ModelAdmin):
    """Comprehensive admin interface for Fixed Assets"""
    
    list_display = [
        'number', 'name', 'asset_type', 'purchase_price', 'book_value_display', 'purchase_date', 
        'status_badge'
    ]
    list_filter = [
        'status', 'asset_type', 'depreciation_method', 'purchase_date'
    ]
    search_fields = ['name', 'number', 'description', 'serial_number', 'location', 'supplier']
    readonly_fields = ['number', 'book_value_display', 'created_at', 'updated_at']
    ordering = ['-created_at']
    date_hierarchy = 'purchase_date'
    
    def status_badge(self, obj):
        """Display status with color coding"""
        status_colors = {
            'draft': 'warning',
            'active': 'success',
            'disposed': 'danger',
            'sold': 'info'
        }
        color = status_colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def book_value_display(self, obj):
        """Display current book value"""
        try:
            # Use the property instead of a method
            accumulated_depreciation = obj.total_accumulated_depreciation
            if accumulated_depreciation is None:
                accumulated_depreciation = 0
            book_value = obj.purchase_price - accumulated_depreciation
            if book_value < 0:
                return format_html('<span style="color: red;">${:,.2f}</span>', book_value)
            return f'${book_value:,.2f}'
        except Exception:
            # Fallback if depreciation calculation fails
            return f'${obj.purchase_price:,.2f}'
    book_value_display.short_description = 'Book Value'


@admin.register(DepreciationSchedule)
class DepreciationScheduleAdmin(admin.ModelAdmin):
    """Admin interface for Depreciation Schedule"""
    list_display = ['asset', 'period_end_date', 'depreciation_amount', 'accumulated_depreciation']
    list_filter = ['period_end_date', 'asset__asset_type']
    search_fields = ['asset__name', 'asset__number']
    ordering = ['-period_end_date', 'asset']


@admin.register(AssetTransaction)
class AssetTransactionAdmin(admin.ModelAdmin):
    """Admin interface for Asset Transactions"""
    list_display = ['asset', 'transaction_type', 'amount', 'description', 'created_at', 'created_by']
    list_filter = ['transaction_type', 'created_at', 'asset__asset_type']
    search_fields = ['asset__name', 'asset__number', 'description']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(AssetDisposal)
class AssetDisposalAdmin(admin.ModelAdmin):
    """Admin interface for Asset Disposals"""
    list_display = ['asset', 'disposal_date', 'disposal_method', 'disposal_value', 'disposal_costs', 'created_by']
    list_filter = ['disposal_method', 'disposal_date', 'asset__asset_type']
    search_fields = ['asset__name', 'asset__number', 'buyer_details']
    readonly_fields = ['created_by', 'created_at']
    ordering = ['-disposal_date']
