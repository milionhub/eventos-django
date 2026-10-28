from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.events import services
from apps.events.models import Event, TicketType


class TicketTypeSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketType
        fields = ["id", "name", "capacity", "reserved_count"]
        read_only_fields = fields


class EventSerializer(serializers.ModelSerializer):
    """An event in the organizer's list."""

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

    ticket_types = TicketTypeSummarySerializer(many=True, read_only=True)
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
        fields = ["title", "description", "location", "image_url", "start_at", "end_at", "capacity"]
        extra_kwargs = {"capacity": {"min_value": 1}}
