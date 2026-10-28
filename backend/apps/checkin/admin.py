from django.contrib import admin

from .models import CheckInLog


@admin.register(CheckInLog)
class CheckInLogAdmin(admin.ModelAdmin):
    """An audit trail: read-only."""

    list_display = ["checked_at", "event", "result", "staff", "ticket"]
    list_filter = ["result"]
    search_fields = ["event__title", "staff__email"]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
