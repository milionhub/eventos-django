from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.http import Http404, StreamingHttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import generics, serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core.schema import ErrorSerializer
from apps.events.views import ORGANIZERS, EventScopedMixin
from apps.ticketing import selectors, services
from apps.ticketing.exports import attendees_csv
from apps.ticketing.models import Ticket
from apps.ticketing.qr import ticket_qr_svg
from apps.ticketing.renderers import CSVRenderer, SVGRenderer
from apps.ticketing.serializers import (
    AttendeeSerializer,
    MyTicketDetailSerializer,
    MyTicketSerializer,
    ReservationSerializer,
    ReserveSerializer,
)


@extend_schema(tags=["reservations"])
class ReservationCreateView(APIView):
    """Any signed-in user can book (ADR-0005: no guest bookings)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "reservations"  # RNF-05

    @extend_schema(
        operation_id="reservations_create",
        request=ReserveSerializer,
        responses={
            201: ReservationSerializer,
            404: ErrorSerializer,
            409: ErrorSerializer,
            429: OpenApiResponse(description="Demasiadas peticiones."),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = ReserveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reservation = services.reserve(
            user=request.user, ticket_type_id=serializer.validated_data["ticket_type"]
        )
        return Response(ReservationSerializer(reservation).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["reservations"])
class ReservationCancelView(APIView):
    """The attendee cancels their own reservation (RN-20). Organizers cancel from the
    attendee list (Phase 5), with their own window (RN-21)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="reservations_cancel",
        request=None,
        responses={200: ReservationSerializer, 404: ErrorSerializer, 409: ErrorSerializer},
    )
    def post(self, request: Request, reservation_id) -> Response:
        reservation = selectors.reservation_of(request.user, reservation_id)
        if reservation is None:
            raise Http404
        reservation = services.cancel_reservation(
            reservation=reservation, cancelled_by=request.user
        )
        return Response(ReservationSerializer(reservation).data)


# --- My tickets ---------------------------------------------------------------------------
# Scoped to the signed-in user: another user's ticket is a 404, never a 403.


@extend_schema(tags=["my tickets"])
class MyTicketListView(APIView):
    permission_classes = [IsAuthenticated]

    # A person's own tickets are few and the screen groups them (upcoming / past), so the
    # list is not paginated.
    @extend_schema(operation_id="my_tickets_list", responses=MyTicketSerializer(many=True))
    def get(self, request: Request) -> Response:
        return Response(MyTicketSerializer(selectors.tickets_of(request.user), many=True).data)


@extend_schema(tags=["my tickets"])
class MyTicketDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(operation_id="my_tickets_retrieve", responses=MyTicketDetailSerializer)
    def get(self, request: Request, ticket_id) -> Response:
        ticket = selectors.ticket_of(request.user, ticket_id)
        if ticket is None:
            raise Http404
        return Response(MyTicketDetailSerializer(ticket).data)


@extend_schema(tags=["my tickets"])
class MyTicketQRView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [SVGRenderer]

    @extend_schema(
        operation_id="my_tickets_qr",
        responses={(200, "image/svg+xml"): OpenApiTypes.BINARY},
    )
    def get(self, request: Request, ticket_id) -> Response:
        ticket = selectors.ticket_of(request.user, ticket_id)
        if ticket is None:
            raise Http404
        # The QR is the entry pass: never keep it in a shared or browser cache.
        return Response(ticket_qr_svg(ticket.token), headers={"Cache-Control": "no-store"})


# --- Organizer side: attendees (mounted under organizations/<org>/events/<id>/) ---------------
# §4: only OWNER and MANAGER see attendees; STAFF gets 403 and other organizations 404.

ATTENDEE_FILTERS = [
    OpenApiParameter("q", description="Busca en nombre, apellidos y email.", required=False),
    OpenApiParameter("status", enum=Ticket.Status.values, required=False),
]


def _attendee_filters(request: Request) -> dict:
    params = request.query_params
    ticket_status = params.get("status")
    if ticket_status:  # 400 if unknown
        ticket_status = serializers.ChoiceField(Ticket.Status.choices).run_validation(ticket_status)
    return {"q": params.get("q", "").strip()[:100], "ticket_status": ticket_status}


def _timezone(request: Request) -> ZoneInfo:
    """The browser's time zone (RNF-04), so the CSV shows the times the organizer sees."""
    name = request.query_params.get("tz") or "UTC"
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValidationError({"tz": "Zona horaria desconocida."}) from error


@extend_schema(tags=["attendees"])
@extend_schema_view(get=extend_schema(operation_id="attendees_list", parameters=ATTENDEE_FILTERS))
class AttendeeListView(EventScopedMixin, generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    roles_by_method = {"GET": ORGANIZERS}
    serializer_class = AttendeeSerializer

    def get_queryset(self):
        return selectors.attendees_of(self.get_event(), **_attendee_filters(self.request))


@extend_schema(tags=["attendees"])
class AttendeeCancelView(EventScopedMixin, APIView):
    """An organizer cancels someone's reservation until the event ends (RN-21)."""

    permission_classes = [IsAuthenticated]
    roles_by_method = {"POST": ORGANIZERS}

    @extend_schema(
        operation_id="attendees_cancel",
        request=None,
        responses={200: AttendeeSerializer, 404: ErrorSerializer, 409: ErrorSerializer},
    )
    def post(self, request: Request, org_slug: str, event_id: int, reservation_id) -> Response:
        reservation = selectors.reservation_in(self.get_event(), reservation_id)
        if reservation is None:
            raise Http404
        services.cancel_reservation(
            reservation=reservation, cancelled_by=request.user, as_organizer=True
        )
        reservation = selectors.attendees_of(reservation.event).get(pk=reservation.pk)
        return Response(AttendeeSerializer(reservation).data)


@extend_schema(tags=["attendees"])
class AttendeeExportView(EventScopedMixin, APIView):
    permission_classes = [IsAuthenticated]
    roles_by_method = {"GET": ORGANIZERS}
    renderer_classes = [CSVRenderer]

    @extend_schema(
        operation_id="attendees_export",
        parameters=[
            *ATTENDEE_FILTERS,
            OpenApiParameter("tz", description="Zona horaria IANA, p. ej. Europe/Madrid."),
        ],
        responses={(200, "text/csv"): OpenApiTypes.BINARY},
    )
    def get(self, request: Request, org_slug: str, event_id: int) -> StreamingHttpResponse:
        event = self.get_event()
        tz = _timezone(request)
        reservations = selectors.attendees_of(event, **_attendee_filters(request))
        response = StreamingHttpResponse(
            attendees_csv(reservations.iterator(chunk_size=500), tz),
            content_type="text/csv; charset=utf-8",
        )
        response["Content-Disposition"] = f'attachment; filename="asistentes-{event.slug}.csv"'
        response["Cache-Control"] = "no-store"  # personal data
        return response
