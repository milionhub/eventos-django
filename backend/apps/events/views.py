from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.schema import ErrorSerializer
from apps.events import selectors, services
from apps.events.models import Event
from apps.events.serializers import EventDetailSerializer, EventSerializer, EventWriteSerializer
from apps.organizations.mixins import OrganizationScopedMixin
from apps.organizations.models import Membership

Role = Membership.Role
# requirements.md §4: OWNER and MANAGER run events. STAFF only sees the events they are
# assigned to, which arrives with EventStaff (block 6).
ORGANIZERS = frozenset({Role.OWNER, Role.MANAGER})


class EventScopedMixin(OrganizationScopedMixin):
    """Adds `get_event()`: the event from the URL, only within the URL's organization."""

    def get_event(self) -> Event:
        event = selectors.event_of(self.organization, self.kwargs["event_id"])
        if event is None:
            raise Http404
        return event


@extend_schema(tags=["events"])
@extend_schema_view(
    get=extend_schema(
        operation_id="events_list",
        parameters=[OpenApiParameter("status", enum=Event.Status.values, required=False)],
    )
)
class EventListView(OrganizationScopedMixin, generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    roles_by_method = {"GET": ORGANIZERS, "POST": ORGANIZERS}
    serializer_class = EventSerializer

    def get_queryset(self):
        status_filter = serializers.ChoiceField(choices=Event.Status.choices, required=False)
        status_value = self.request.query_params.get("status")
        if status_value:
            status_value = status_filter.run_validation(status_value)  # 400 if unknown
        return selectors.events_of(self.organization, status=status_value)

    @extend_schema(
        operation_id="events_create",
        request=EventWriteSerializer,
        responses={201: EventDetailSerializer, 400: ErrorSerializer},
    )
    def post(self, request: Request, org_slug: str) -> Response:
        serializer = EventWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = services.create_event(
            organization=self.organization, user=request.user, **serializer.validated_data
        )
        return Response(EventDetailSerializer(event).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["events"])
class EventDetailView(EventScopedMixin, APIView):
    permission_classes = [IsAuthenticated]
    roles_by_method = {"GET": ORGANIZERS, "PATCH": ORGANIZERS}

    @extend_schema(operation_id="events_retrieve", responses=EventDetailSerializer)
    def get(self, request: Request, org_slug: str, event_id: int) -> Response:
        return Response(EventDetailSerializer(self.get_event()).data)

    @extend_schema(
        operation_id="events_update",
        request=EventWriteSerializer,
        responses={200: EventDetailSerializer, 400: ErrorSerializer, 409: ErrorSerializer},
    )
    def patch(self, request: Request, org_slug: str, event_id: int) -> Response:
        serializer = EventWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        event = services.update_event(event=self.get_event(), **serializer.validated_data)
        return Response(EventDetailSerializer(event).data)


@extend_schema(tags=["events"])
class EventPublishView(EventScopedMixin, APIView):
    permission_classes = [IsAuthenticated]
    roles_by_method = {"POST": ORGANIZERS}

    @extend_schema(
        operation_id="events_publish",
        request=None,
        responses={200: EventDetailSerializer, 409: ErrorSerializer},
    )
    def post(self, request: Request, org_slug: str, event_id: int) -> Response:
        event = services.publish_event(event=self.get_event())
        return Response(EventDetailSerializer(event).data)


@extend_schema(tags=["events"])
class EventCancelView(EventScopedMixin, APIView):
    permission_classes = [IsAuthenticated]
    roles_by_method = {"POST": ORGANIZERS}

    @extend_schema(
        operation_id="events_cancel",
        request=None,
        responses={200: EventDetailSerializer, 409: ErrorSerializer},
    )
    def post(self, request: Request, org_slug: str, event_id: int) -> Response:
        event = services.cancel_event(event=self.get_event())
        return Response(EventDetailSerializer(event).data)
