from django.contrib import admin
from .models import (
    ShortenedURL, Click, QRCode, Domain, 
    UserProfile, LinkGroup
)


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'links_created', 'clicks_received', 'created_at']
    list_filter = ['plan', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['links_created', 'clicks_received']


@admin.register(ShortenedURL)
class ShortenedURLAdmin(admin.ModelAdmin):
    list_display = ['short_code', 'original_url_truncated', 'user', 'clicks', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at', 'domain', 'user']
    search_fields = ['short_code', 'original_url', 'title', 'user__username']
    readonly_fields = ['clicks', 'created_at', 'updated_at']
    
    def original_url_truncated(self, obj):
        return obj.original_url[:50] + '...' if len(obj.original_url) > 50 else obj.original_url
    original_url_truncated.short_description = 'Original URL'


@admin.register(Click)
class ClickAdmin(admin.ModelAdmin):
    list_display = ['url', 'ip_address', 'device_type', 'browser', 'country', 'clicked_at']
    list_filter = ['device_type', 'browser', 'country', 'clicked_at']
    search_fields = ['url__short_code', 'ip_address', 'country', 'city']
    readonly_fields = ['clicked_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('url')


@admin.register(QRCode)
class QRCodeAdmin(admin.ModelAdmin):
    list_display = ['url', 'size', 'fill_color', 'back_color', 'created_at']
    list_filter = ['size', 'created_at']
    search_fields = ['url__short_code']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(LinkGroup)
class LinkGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'color', 'created_at']
    list_filter = ['created_at', 'user']
    search_fields = ['name', 'description', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
