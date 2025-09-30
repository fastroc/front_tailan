from django.contrib import admin
from .models import ReportConfiguration, ReportCache, ReportExport, ReportSchedule


@admin.register(ReportConfiguration)
class ReportConfigurationAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'company', 'report_type', 'date_range', 'is_active', 'is_favorite', 'created_at']
    list_filter = ['report_type', 'date_range', 'is_active', 'is_favorite', 'company']
    search_fields = ['name', 'user__username', 'company__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'user', 'company', 'report_type')
        }),
        ('Configuration', {
            'fields': ('date_range', 'start_date', 'end_date', 'filters')
        }),
        ('Status', {
            'fields': ('is_active', 'is_favorite')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ReportCache)
class ReportCacheAdmin(admin.ModelAdmin):
    list_display = ['report_type', 'company', 'cache_key', 'expires_at', 'created_at', 'is_expired_status']
    list_filter = ['report_type', 'company', 'expires_at']
    search_fields = ['cache_key', 'report_type', 'company__name']
    readonly_fields = ['created_at', 'is_expired_status']
    
    def is_expired_status(self, obj):
        return obj.is_expired()
    is_expired_status.boolean = True
    is_expired_status.short_description = 'Expired'
    
    actions = ['clear_expired_cache']
    
    def clear_expired_cache(self, request, queryset):
        expired_count = 0
        for cache in queryset:
            if cache.is_expired():
                cache.delete()
                expired_count += 1
        self.message_user(request, f'Cleared {expired_count} expired cache entries.')
    clear_expired_cache.short_description = 'Clear expired cache entries'


@admin.register(ReportExport)
class ReportExportAdmin(admin.ModelAdmin):
    list_display = ['user', 'company', 'report_type', 'format', 'status', 'created_at', 'completed_at', 'file_size_mb']
    list_filter = ['format', 'status', 'report_type', 'company']
    search_fields = ['user__username', 'company__name', 'report_type']
    readonly_fields = ['created_at', 'completed_at', 'file_size_mb']
    
    def file_size_mb(self, obj):
        if obj.file_size:
            return f"{obj.file_size / (1024*1024):.2f} MB"
        return "-"
    file_size_mb.short_description = 'File Size'
    
    fieldsets = (
        ('Export Details', {
            'fields': ('user', 'company', 'report_type', 'format', 'status')
        }),
        ('File Information', {
            'fields': ('file_path', 'file_size_mb', 'parameters')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'completed_at', 'expires_at')
        }),
        ('Error Information', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )


@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'company', 'frequency', 'next_run', 'last_run', 'is_active']
    list_filter = ['frequency', 'is_active', 'company']
    search_fields = ['name', 'user__username', 'company__name']
    readonly_fields = ['created_at', 'last_run']
    
    fieldsets = (
        ('Schedule Information', {
            'fields': ('name', 'user', 'company', 'report_config')
        }),
        ('Schedule Settings', {
            'fields': ('frequency', 'next_run', 'last_run', 'is_active')
        }),
        ('Delivery', {
            'fields': ('email_recipients',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_schedules', 'deactivate_schedules']
    
    def activate_schedules(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Activated {updated} report schedules.')
    activate_schedules.short_description = 'Activate selected schedules'
    
    def deactivate_schedules(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Deactivated {updated} report schedules.')
    deactivate_schedules.short_description = 'Deactivate selected schedules'
