from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.events import services
from apps.events.models import Event, EventStaff, TicketType


@extend_schema_field(OpenApiTypes.STR)
class ImageUrlField(serializers.Field):
    """The uploaded image as a `/media/...` path, or "" when there is none (ADR-0008)."""

    def __init__(self, **kwargs):
        super().__init__(source="image", read_only=True, **kwargs)

    def to_representation(self, value) -> str:
        return value.url if value else ""


# --- Organizer side -----------------------------------------------------------------------


class TicketTypeSerializer(serializers.ModelSerializer):
    available = serializers.IntegerField(read_only=True)

    class Meta:
        model = TicketType
        fields = ["id", "name", "description", "capacity", "reserved_count", "available"]
        read_only_fields = fields


class TicketTypeWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketType
        fields = ["name", "description", "capacity"]
        extra_kwargs = {"capacity": {"min_value": 1}}


class EventSerializer(serializers.ModelSerializer):
    """An event in the organizer's list."""

    image_url = ImageUrlField()
    is_finished = serializers.BooleanField(read_only=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "slug",
            "location",
            "image_url",
            "start_at",
            "end_at",
            "capacity",
            "status",
            "is_finished",
            "published_at",
            "cancelled_at",
        ]
        read_only_fields = fields


class EventDetailSerializer(EventSerializer):
    """One event for its organizers, with what is needed to manage and publish it."""

    ticket_types = TicketTypeSerializer(many=True, read_only=True)
    allocated_capacity = serializers.SerializerMethodField()
    publish_blockers = serializers.SerializerMethodField()

    class Meta(EventSerializer.Meta):
        fields = [
            *EventSerializer.Meta.fields,
            "description",
            "created_at",
            "ticket_types",
            "allocated_capacity",
            "publish_blockers",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.IntegerField())
    def get_allocated_capacity(self, event: Event) -> int:
        return services.allocated_capacity(event)

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_publish_blockers(self, event: Event) -> list[str]:
        if event.status != Event.Status.DRAFT:
            return []
        return services.publish_blockers(event)


class EventWriteSerializer(serializers.ModelSerializer):
    """Input for create and edit. Business rules are checked by the services."""

    class Meta:
        model = Event
        fields = ["title", "description", "location", "start_at", "end_at", "capacity"]
        extra_kwargs = {"capacity": {"min_value": 1}}


class EventStaffSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = EventStaff
        fields = ["id", "user", "created_at"]
        read_only_fields = fields


class AssignStaffSerializer(serializers.Serializer):
    user = serializers.IntegerField(help_text="Id de un usuario miembro de la organización.")


# --- Public side ----------------------------------------------------------------------------


class PublicEventSerializer(serializers.ModelSerializer):
    image_url = ImageUrlField()
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    available = serializers.IntegerField(read_only=True, help_text="Plazas libres en total.")

    class Meta:
        model = Event
        fields = [
            "slug",
            "title",
            "location",
            "image_url",
            "start_at",
            "end_at",
            "organization_name",
            "available",
        ]
        read_only_fields = fields


class PublicTicketTypeSerializer(serializers.ModelSerializer):
    available = serializers.IntegerField(read_only=True)
    sold_out = serializers.SerializerMethodField()

    class Meta:
        model = TicketType
        fields = ["id", "name", "description", "available", "sold_out"]
        read_only_fields = fields

    def get_sold_out(self, ticket_type: TicketType) -> bool:
        return ticket_type.available <= 0


class PublicEventDetailSerializer(serializers.ModelSerializer):
    image_url = ImageUrlField()
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    is_finished = serializers.BooleanField(read_only=True)
    available = serializers.SerializerMethodField()
    ticket_types = PublicTicketTypeSerializer(many=True, read_only=True)

    class Meta:
        model = Event
        fields = [
            "slug",
            "title",
            "description",
            "location",
            "image_url",
            "start_at",
            "end_at",
            "organization_name",
            "is_finished",
            "available",
            "ticket_types",
        ]
        read_only_fields = fields

    def get_available(self, event: Event) -> int:
        return sum(ticket_type.available for ticket_type in event.ticket_types.all())


class EventImageSerializer(serializers.Serializer):
    image = serializers.FileField(help_text="JPG, PNG o WebP de hasta 5 MB.")
