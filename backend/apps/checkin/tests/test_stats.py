"""Organizer stats (requirements.md R5): occupancy, check-ins and who may see them (§4)."""

from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.checkin import selectors
from apps.checkin.models import CheckInLog
from apps.checkin.services import scan
from apps.checkin.tests.factories import open_event, staff_of
from apps.events.models import Event, TicketType
from apps.events.tests.factories import EventFactory, TicketTypeFactory
from apps.organizations.models import Membership
from apps.organizations.tests.factories import MembershipFactory, OrganizationFactory
from apps.ticketing.models import Ticket
from apps.ticketing.services import cancel_reservation, reserve

pytestmark = pytest.mark.django_db
Role = Membership.Role


def book(ticket_type: TicketType) -> Ticket:
    """A confirmed reservation for a new attendee (the event must not have started)."""
    return reserve(user=UserFactory(), ticket_type_id=ticket_type.pk).ticket


def check_in(ticket: Ticket) -> None:
    Ticket.objects.filter(pk=ticket.pk).update(
        status=Ticket.Status.USED, checked_in_at=timezone.now()
    )


def move_to_the_past(event: Event) -> None:
    """Finished yesterday. Bookings must be made before calling this."""
    start = timezone.now() - timedelta(days=1)
    Event.objects.filter(pk=event.pk).update(start_at=start, end_at=start + timedelta(hours=2))


# --- event stats ------------------------------------------------------------------------------


def test_event_stats_per_category():
    event = open_event()
    general = TicketTypeFactory(event=event, name="General", capacity=10)
    vip = TicketTypeFactory(event=event, name="VIP", capacity=4)
    in_general = [book(general) for _ in range(3)]
    in_vip = book(vip)
    check_in(in_general[0])
    check_in(in_general[1])
    check_in(in_vip)
    cancel_reservation(
        reservation=in_general[2].reservation, cancelled_by=UserFactory(), as_organizer=True
    )

    stats = selectors.event_stats(event)

    rows = {t.name: (t.capacity, t.reserved_count, t.checked_in) for t in stats.ticket_types}
    assert rows == {"General": (10, 2, 2), "VIP": (4, 1, 1)}
    assert (stats.seats, stats.reserved, stats.checked_in, stats.cancelled) == (14, 3, 3, 1)


def test_event_stats_count_every_scan_result_including_zeros():
    event = open_event()
    staff = staff_of(event)
    ticket = book(TicketTypeFactory(event=event))
    scan(event=event, token=ticket.token, staff=staff)
    scan(event=event, token=ticket.token, staff=staff)
    scan(event=event, token="does-not-exist", staff=staff)

    scans = selectors.event_stats(event).scans

    assert scans["VALID"] == 1
    assert scans["ALREADY_USED"] == 1
    assert scans["NOT_FOUND"] == 1
    assert set(scans) == set(CheckInLog.Result.values)
    assert sum(scans.values()) == 3


def test_event_stats_of_an_event_without_categories():
    stats = selectors.event_stats(EventFactory())

    assert (stats.seats, stats.reserved, stats.checked_in, stats.cancelled) == (0, 0, 0, 0)


# --- organization stats -----------------------------------------------------------------------


def test_organization_totals_cover_published_events_finished_ones_included():
    organization = OrganizationFactory()
    upcoming = open_event(organization=organization)
    upcoming_type = TicketTypeFactory(event=upcoming, capacity=10)
    check_in(book(upcoming_type))
    book(upcoming_type)

    finished = open_event(organization=organization, start_at=timezone.now() + timedelta(days=1))
    finished_type = TicketTypeFactory(event=finished, capacity=5)
    check_in(book(finished_type))
    move_to_the_past(finished)

    TicketTypeFactory(event=EventFactory(organization=organization), capacity=100)  # draft
    cancelled = open_event(organization=organization, status=Event.Status.CANCELLED)
    TicketTypeFactory(event=cancelled, capacity=100)
    open_event()  # another organization

    stats = selectors.organization_stats(organization, timezone.now())

    assert stats.active_events == 1
    assert (stats.seats, stats.reserved, stats.checked_in) == (15, 3, 2)
    assert [e.pk for e in stats.upcoming] == [upcoming.pk]


def test_upcoming_events_are_not_inflated_by_joining_categories_and_tickets():
    """Two categories by three used tickets: a plain join would multiply the figures."""
    organization = OrganizationFactory()
    event = open_event(organization=organization)
    general = TicketTypeFactory(event=event, capacity=10)
    vip = TicketTypeFactory(event=event, capacity=5)
    for ticket in [book(general), book(general), book(vip)]:
        check_in(ticket)
    book(vip)

    (row,) = selectors.organization_stats(organization, timezone.now()).upcoming

    assert (row.seats, row.reserved, row.checked_in) == (15, 4, 3)


def test_upcoming_events_come_soonest_first_and_are_limited():
    organization = OrganizationFactory()
    now = timezone.now()
    later = open_event(organization=organization, start_at=now + timedelta(days=3))
    sooner = open_event(organization=organization, start_at=now + timedelta(days=1))
    open_event(organization=organization, start_at=now + timedelta(days=5))

    stats = selectors.organization_stats(organization, now, upcoming_limit=2)

    assert [e.pk for e in stats.upcoming] == [sooner.pk, later.pk]
    assert stats.upcoming[0].seats == 0  # no categories yet: 0, not None
    assert stats.active_events == 3


def queries_for_organization_with(events: int) -> int:
    organization = OrganizationFactory()
    for _ in range(events):
        event = open_event(organization=organization)
        for _ in range(2):
            check_in(book(TicketTypeFactory(event=event)))
    with CaptureQueriesContext(connection) as queries:
        selectors.organization_stats(organization, timezone.now())
    return len(queries)


def test_organization_stats_take_the_same_queries_for_1_or_5_events():
    assert queries_for_organization_with(1) == queries_for_organization_with(5)


# --- API --------------------------------------------------------------------------------------


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def event_stats_url(event: Event) -> str:
    return reverse(
        "event-stats", kwargs={"org_slug": event.organization.slug, "event_id": event.pk}
    )


def org_stats_url(event: Event) -> str:
    return reverse("organization-stats", kwargs={"org_slug": event.organization.slug})


def test_event_stats_endpoint():
    event = open_event()
    check_in(book(TicketTypeFactory(event=event, name="General", capacity=10)))
    owner = MembershipFactory(organization=event.organization, role=Role.OWNER).user

    response = client_for(owner).get(event_stats_url(event))

    assert response.status_code == 200
    data = response.json()
    assert data["ticket_types"] == [
        {
            "id": data["ticket_types"][0]["id"],
            "name": "General",
            "capacity": 10,
            "reserved": 1,
            "checked_in": 1,
        }
    ]
    assert (data["seats"], data["reserved"], data["checked_in"]) == (10, 1, 1)
    assert data["scans"]["VALID"] == 0  # checked in directly, without scanning


def test_organization_stats_endpoint():
    event = open_event()
    book(TicketTypeFactory(event=event, capacity=8))
    manager = MembershipFactory(organization=event.organization, role=Role.MANAGER).user

    data = client_for(manager).get(org_stats_url(event)).json()

    assert (data["active_events"], data["seats"], data["reserved"]) == (1, 8, 1)
    assert data["upcoming"][0]["id"] == event.pk
    assert data["upcoming"][0]["reserved"] == 1


@pytest.mark.parametrize("url", [event_stats_url, org_stats_url])
@pytest.mark.parametrize(
    ("role", "expected"), [(Role.OWNER, 200), (Role.MANAGER, 200), (Role.STAFF, 403)]
)
def test_only_organizers_see_stats(url, role, expected):
    event = open_event()
    user = MembershipFactory(organization=event.organization, role=role).user

    assert client_for(user).get(url(event)).status_code == expected


@pytest.mark.parametrize("url", [event_stats_url, org_stats_url])
def test_stats_of_other_organizations_are_404(url):
    event = open_event()
    outsider = MembershipFactory(role=Role.OWNER).user  # owner of another organization

    assert client_for(outsider).get(url(event)).status_code == 404


def test_an_event_id_from_another_organization_is_404():
    mine = open_event()
    owner = MembershipFactory(organization=mine.organization, role=Role.OWNER).user
    theirs = open_event()
    url = reverse("event-stats", kwargs={"org_slug": mine.organization.slug, "event_id": theirs.pk})

    assert client_for(owner).get(url).status_code == 404


@pytest.mark.parametrize("url", [event_stats_url, org_stats_url])
def test_stats_require_an_account(url):
    assert APIClient().get(url(open_event())).status_code == 401
