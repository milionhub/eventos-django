from django.contrib import admin

from .models import Reservation, Ticket


class TicketInline(admin.StackedInline):
    model = Ticket
    extra = 0
    can_delete = False
    # The token is a secret: shown read-only, never edited by hand.
    readonly_fields = ["token", "status", "issued_at", "checked_in_at", "checked_in_by"]


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "event", "ticket_type", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["user__email", "event__title"]
    # Seats are counted by the reservation service (ADR-0004): no edits from the admin.
    readonly_fields = [
        "user",
        "event",
        "ticket_type",
        "status",
        "cancelled_at",
        "cancelled_by",
        "created_at",
        "updated_at",
    ]
    inlines = [TicketInline]

    def has_add_permission(self, request) -> bool:
        return False
