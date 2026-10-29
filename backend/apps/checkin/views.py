from django.http import Http404
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.checkin import selectors, services
from apps.checkin.models import CheckInLog
from apps.checkin.serializers import (
    CheckinActivitySerializer,
    CheckinEventSerializer,
    EventStatsSerializer,
    OrganizationStatsSerializer,
    ScanRequestSerializer,
    ScanResultSerializer,
)
from apps.events.models import Event
from apps.events.views import ORGANIZERS, EventScopedMixin
from apps.organizations.mixins import OrganizationScopedMixin


def _event_or_404(request: Request, event_id: int) -> Event:
    # Events of other organizations do not exist for this user (RN-06).
    event = selectors.event_in_my_organizations(request.user, event_id)
    if event is None:
        raise Http404
    return event


@extend_schema(tags=["checkin"])
class CheckinEventListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(operation_id="checkin_events_list", responses=CheckinEventSerializer(many=True))
    def get(self, request: Request) -> Response:
        now = timezone.now()
        events = selectors.validatable_events(request.user, now)
        return Response(CheckinEventSerializer(events, many=True, context={"now": now}).data)


@extend_schema(tags=["checkin"])
class ScanView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "checkin"  # RNF-05: tokens cannot be brute-forced

    @extend_schema(
        operation_id="checkin_scan",
        request=ScanRequestSerializer,
        responses={
            200: ScanResultSerializer,
            403: ScanResultSerializer,
            404: OpenApiResponse(),
            429: OpenApiResponse(),
        },
    )
    def post(self, request: Request, event_id: int) -> Response:
        event = _event_or_404(request, event_id)
        serializer = ScanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        outcome = services.scan(
            event=event, token=serializer.validated_data["token"], staff=request.user
        )
        data = ScanResultSerializer(
            {
                "result": outcome.result,
                "ticket": outcome.ticket,
                "checked_at": outcome.log.checked_at,
            }
        ).data
        # Every other result is a normal answer for the door; only a missing permission is
        # an HTTP error (RN-32), and it is logged all the same.
        unauthorized = outcome.result == CheckInLog.Result.UNAUTHORIZED
        return Response(data, status=status.HTTP_403_FORBIDDEN if unauthorized else 200)


@extend_schema(tags=["checkin"])
class CheckinActivityView(APIView):
    """How many are in and the latest attempts, for the scanner screen."""

    permission_classes = [IsAuthenticated]

    @extend_schema(operation_id="checkin_activity", responses=CheckinActivitySerializer)
    def get(self, request: Request, event_id: int) -> Response:
        event = _event_or_404(request, event_id)
        if not services.can_validate(request.user, event):
            return Response(status=status.HTTP_403_FORBIDDEN)
        data = {"stats": selectors.checkin_stats(event), "logs": selectors.recent_logs(event)}
        return Response(CheckinActivitySerializer(data).data)


# --- Organizer stats (mounted under organizations/<org_slug>/) ---------------------------------
# §4: only OWNER and MANAGER see stats; STAFF gets 403 and other organizations 404.


@extend_schema(tags=["stats"])
class EventStatsView(EventScopedMixin, APIView):
    permission_classes = [IsAuthenticated]
    roles_by_method = {"GET": ORGANIZERS}

    @extend_schema(operation_id="event_stats", responses=EventStatsSerializer)
    def get(self, request: Request, org_slug: str, event_id: int) -> Response:
        return Response(EventStatsSerializer(selectors.event_stats(self.get_event())).data)


@extend_schema(tags=["stats"])
class OrganizationStatsView(OrganizationScopedMixin, APIView):
    permission_classes = [IsAuthenticated]
    roles_by_method = {"GET": ORGANIZERS}

    @extend_schema(operation_id="organization_stats", responses=OrganizationStatsSerializer)
    def get(self, request: Request, org_slug: str) -> Response:
        stats = selectors.organization_stats(self.organization, timezone.now())
        return Response(OrganizationStatsSerializer(stats).data)
