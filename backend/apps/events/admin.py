from django.contrib import admin

from .models import Event, EventStaff, TicketType


class TicketTypeInline(admin.TabularInline):
    model = TicketType
    extra = 0
    readonly_fields = ["reserved_count"]


class EventStaffInline(admin.TabularInline):
    model = EventStaff
    extra = 0
    autocomplete_fields = ["user"]


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["title", "organization", "status", "start_at", "capacity"]
    list_filter = ["status"]
    search_fields = ["title", "slug", "organization__name"]
    readonly_fields = ["slug", "published_at", "cancelled_at", "created_at", "updated_at"]
    inlines = [TicketTypeInline, EventStaffInline]
