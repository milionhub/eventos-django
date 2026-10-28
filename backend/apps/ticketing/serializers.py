from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.events.models import Event, TicketType
from apps.ticketing import services
from apps.ticketing.models import Reservation, Ticket


class ReserveSerializer(serializers.Serializer):
    ticket_type = serializers.IntegerField(help_text="Id de la categoría de entrada.")


class ReservationEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["slug", "title", "location", "start_at", "end_at"]
        read_only_fields = fields


class ReservationTicketTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketType
        fields = ["id", "name"]
        read_only_fields = fields


class TicketSummarySerializer(serializers.ModelSerializer):
    """The ticket without its token: the token only travels in the ticket detail and QR."""

    class Meta:
        model = Ticket
        fields = ["id", "status"]
        read_only_fields = fields


class ReservationSerializer(serializers.ModelSerializer):
    event = ReservationEventSerializer(read_only=True)
    ticket_type = ReservationTicketTypeSerializer(read_only=True)
    ticket = TicketSummarySerializer(read_only=True)

    class Meta:
        model = Reservation
        fields = ["id", "status", "created_at", "event", "ticket_type", "ticket"]
        read_only_fields = fields


# --- My tickets ----------------------------------------------------------------------------


class MyTicketEventSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = Event
        fields = ["slug", "title", "location", "start_at", "end_at", "status", "organization_name"]
        read_only_fields = fields


class MyTicketReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ["id", "status", "created_at", "cancelled_at"]
        read_only_fields = fields


class MyTicketSerializer(serializers.ModelSerializer):
    """A ticket in "my tickets". No token here: it only travels in the detail and the QR."""

    event = MyTicketEventSerializer(source="reservation.event", read_only=True)
    ticket_type = ReservationTicketTypeSerializer(source="reservation.ticket_type", read_only=True)
    reservation = MyTicketReservationSerializer(read_only=True)

    class Meta:
        model = Ticket
        fields = [
            "id",
            "status",
            "issued_at",
            "checked_in_at",
            "event",
            "ticket_type",
            "reservation",
        ]
        read_only_fields = fields


class MyTicketDetailSerializer(MyTicketSerializer):
    """One ticket for its owner: the token (for the QR) and whether it can still be cancelled."""

    cancel_deadline = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()

    class Meta(MyTicketSerializer.Meta):
        fields = [*MyTicketSerializer.Meta.fields, "token", "cancel_deadline", "can_cancel"]
        read_only_fields = fields

    @extend_schema_field(serializers.DateTimeField())
    def get_cancel_deadline(self, ticket: Ticket):
        return services.cancellation_deadline(ticket.reservation.event)

    def get_can_cancel(self, ticket: Ticket) -> bool:
        """RN-20 to RN-22, so the screen does not have to repeat them."""
        return (
            ticket.reservation.status == Reservation.Status.CONFIRMED
            and ticket.status == Ticket.Status.VALID
            and timezone.now() <= services.cancellation_deadline(ticket.reservation.event)
        )
