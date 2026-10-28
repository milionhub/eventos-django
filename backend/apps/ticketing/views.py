from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core.schema import ErrorSerializer
from apps.ticketing import services
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
