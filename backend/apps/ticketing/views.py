from django.http import Http404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core.schema import ErrorSerializer
from apps.ticketing import selectors, services
from apps.ticketing.serializers import ReservationSerializer, ReserveSerializer


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
