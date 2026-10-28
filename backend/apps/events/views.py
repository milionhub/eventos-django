from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import generics, serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.schema import ErrorSerializer
from apps.events import selectors, services
from apps.events.models import Event
from apps.events.serializers import (
    AssignStaffSerializer,
    EventDetailSerializer,
    EventSerializer,
    EventStaffSerializer,
    EventWriteSerializer,
    PublicEventDetailSerializer,
    PublicEventSerializer,
    TicketTypeSerializer,
    TicketTypeWriteSerializer,
)
from apps.organizations.mixins import ALL_ROLES, OrganizationScopedMixin
from apps.organizations.models import Membership

Role = Membership.Role
# requirements.md §4: OWNER and MANAGER run events; STAFF only reads the events they are
# assigned to (and gets 404 for the rest, as if they did not exist).
ORGANIZERS = frozenset({Role.OWNER, Role.MANAGER})


class EventScopedMixin(OrganizationScopedMixin):
    """Adds `get_event()`: the event from the URL, only within what the caller may see."""

    @property
    def staff_user(self):
        return self.request.user if self.membership.role == Role.STAFF else None

    def get_event(self) -> Event:
        event = selectors.event_of(
            self.organization, self.kwargs["event_id"], staff_user=self.staff_user
        )
        if event is None:
            raise Http404
        return event


# --- Events -----------------------------------------------------------------------------


@extend_schema(tags=["events"])
@extend_schema_view(
    get=extend_schema(
        operation_id="events_list",
        parameters=[OpenApiParameter("status", enum=Event.Status.values, required=False)],
    )
)
class EventListView(EventScopedMixin, generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    roles_by_method = {"GET": ALL_ROLES, "POST": ORGANIZERS}
    serializer_class = EventSerializer

    def get_queryset(self):
        status_value = self.request.query_params.get("status")
        if status_value:  # 400 if unknown
            status_value = serializers.ChoiceField(Event.Status.choices).run_validation(
                status_value
            )
        return selectors.events_of(
            self.organization, status=status_value, staff_user=self.staff_user
        )

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
    roles_by_method = {"GET": ALL_ROLES, "PATCH": ORGANIZERS}

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
        event = services.cancel_event(event=self.get_event(), by=request.user)
        return Response(EventDetailSerializer(event).data)


# --- Ticket types ------------------------------------------------------------------------


@extend_schema(tags=["events"])
class TicketTypeListView(EventScopedMixin, APIView):
    permission_classes = [IsAuthenticated]
    roles_by_method = {"GET": ORGANIZERS, "POST": ORGANIZERS}

    @extend_schema(operation_id="ticket_types_list", responses=TicketTypeSerializer(many=True))
    def get(self, request: Request, org_slug: str, event_id: int) -> Response:
        ticket_types = selectors.ticket_types_of(self.get_event())
        return Response(TicketTypeSerializer(ticket_types, many=True).data)

    @extend_schema(
        operation_id="ticket_types_create",
        request=TicketTypeWriteSerializer,
        responses={201: TicketTypeSerializer, 409: ErrorSerializer},
    )
    def post(self, request: Request, org_slug: str, event_id: int) -> Response:
        serializer = TicketTypeWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket_type = services.create_ticket_type(
            event=self.get_event(), **serializer.validated_data
        )
        return Response(TicketTypeSerializer(ticket_type).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["events"])
class TicketTypeDetailView(EventScopedMixin, APIView):
    permission_classes = [IsAuthenticated]
    roles_by_method = {"PATCH": ORGANIZERS, "DELETE": ORGANIZERS}

    def get_ticket_type(self):
        return get_object_or_404(
            selectors.ticket_types_of(self.get_event()), pk=self.kwargs["ticket_type_id"]
        )

    @extend_schema(
        operation_id="ticket_types_update",
        request=TicketTypeWriteSerializer,
        responses={200: TicketTypeSerializer, 409: ErrorSerializer},
    )
    def patch(self, request: Request, org_slug: str, event_id: int, ticket_type_id: int):
        serializer = TicketTypeWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        ticket_type = services.update_ticket_type(
            ticket_type=self.get_ticket_type(), **serializer.validated_data
        )
        return Response(TicketTypeSerializer(ticket_type).data)

    @extend_schema(
        operation_id="ticket_types_destroy",
        responses={204: OpenApiResponse(), 409: ErrorSerializer},
    )
    def delete(self, request: Request, org_slug: str, event_id: int, ticket_type_id: int):
        services.delete_ticket_type(ticket_type=self.get_ticket_type())
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Staff ---------------------------------------------------------------------------------


@extend_schema(tags=["events"])
class StaffListView(EventScopedMixin, APIView):
    permission_classes = [IsAuthenticated]
    roles_by_method = {"GET": ORGANIZERS, "POST": ORGANIZERS}

    @extend_schema(operation_id="staff_list", responses=EventStaffSerializer(many=True))
    def get(self, request: Request, org_slug: str, event_id: int) -> Response:
        return Response(EventStaffSerializer(selectors.staff_of(self.get_event()), many=True).data)

    @extend_schema(
        operation_id="staff_create",
        request=AssignStaffSerializer,
        responses={201: EventStaffSerializer, 400: ErrorSerializer, 409: ErrorSerializer},
    )
    def post(self, request: Request, org_slug: str, event_id: int) -> Response:
        serializer = AssignStaffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = services.assign_staff(
            event=self.get_event(), user_id=serializer.validated_data["user"]
        )
        return Response(EventStaffSerializer(assignment).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["events"])
class StaffDetailView(EventScopedMixin, APIView):
    permission_classes = [IsAuthenticated]
    roles_by_method = {"DELETE": ORGANIZERS}

    @extend_schema(operation_id="staff_destroy", responses={204: OpenApiResponse()})
    def delete(self, request: Request, org_slug: str, event_id: int, assignment_id: int):
        assignment = get_object_or_404(selectors.staff_of(self.get_event()), pk=assignment_id)
        services.unassign_staff(assignment=assignment)
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Public ----------------------------------------------------------------------------------


@extend_schema(tags=["public"])
@extend_schema_view(
    get=extend_schema(
        operation_id="public_events_list",
        parameters=[
            OpenApiParameter("q", str, description="Busca en el título y la ubicación."),
            OpenApiParameter("from", str, description="Fecha (AAAA-MM-DD) de inicio mínima."),
        ],
    )
)
class PublicEventListView(generics.ListAPIView):
    """Anyone, signed in or not, can browse published events."""

    permission_classes = [AllowAny]
    authentication_classes = []  # an expired token must not turn a public page into a 401
    serializer_class = PublicEventSerializer

    def get_queryset(self):
        params = self.request.query_params
        from_date = params.get("from")
        if from_date:  # 400 if malformed
            from_date = serializers.DateField().run_validation(from_date)
        return selectors.public_events(q=params.get("q", "").strip()[:100], from_date=from_date)


@extend_schema(tags=["public"])
class PublicEventDetailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(operation_id="public_events_retrieve", responses=PublicEventDetailSerializer)
    def get(self, request: Request, slug: str) -> Response:
        event = selectors.public_event(slug)
        if event is None:  # drafts and cancelled events are not public
            raise Http404
        return Response(PublicEventDetailSerializer(event).data)
