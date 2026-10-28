from rest_framework import serializers

from apps.events.models import Event, TicketType
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
