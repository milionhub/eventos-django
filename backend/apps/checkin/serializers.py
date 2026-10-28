from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.checkin import services
from apps.checkin.models import CheckInLog
from apps.events.models import Event
from apps.events.serializers import ImageUrlField
from apps.ticketing.models import Ticket


class CheckinEventSerializer(serializers.ModelSerializer):
    """An event where the user can validate, with its door window (RN-29)."""

    organization_name = serializers.CharField(source="organization.name", read_only=True)
    image_url = ImageUrlField()
    opens_at = serializers.SerializerMethodField()
    is_open = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id",
            "slug",
            "title",
            "location",
            "image_url",
            "start_at",
            "end_at",
            "organization_name",
            "opens_at",
            "is_open",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.DateTimeField())
    def get_opens_at(self, event: Event):
        return services.checkin_opens_at(event)

    def get_is_open(self, event: Event) -> bool:
        return services.is_checkin_open(event, self.context["now"])


class ScannedTicketSerializer(serializers.ModelSerializer):
    """Just what the door needs to check the person: category and name (no email)."""

    ticket_type = serializers.CharField(source="reservation.ticket_type.name")
    holder_name = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = ["id", "ticket_type", "holder_name", "checked_in_at"]
        read_only_fields = fields

    def get_holder_name(self, ticket: Ticket) -> str:
        user = ticket.reservation.user
        return f"{user.first_name} {user.last_name}".strip() or "Sin nombre"


class ScanRequestSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=64, trim_whitespace=True)


class ScanResultSerializer(serializers.Serializer):
    result = serializers.ChoiceField(choices=CheckInLog.Result.choices)
    ticket = ScannedTicketSerializer(allow_null=True)
    checked_at = serializers.DateTimeField()


class CheckInLogSerializer(serializers.ModelSerializer):
    ticket = ScannedTicketSerializer(allow_null=True, read_only=True)

    class Meta:
        model = CheckInLog
        fields = ["id", "result", "checked_at", "ticket"]
        read_only_fields = fields


class CheckinStatsSerializer(serializers.Serializer):
    validated = serializers.IntegerField()
    expected = serializers.IntegerField()


class CheckinActivitySerializer(serializers.Serializer):
    stats = CheckinStatsSerializer()
    logs = CheckInLogSerializer(many=True)
