"""Tenant isolation across the whole API: another organization's resources answer 404.

The organizer routes are read from the URLconf, so a new endpoint is covered the day it is
added, and one with an unknown URL parameter fails until `object_ids` learns about it.
"""

import pytest
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework.test import APIClient

from apps.checkin.tests.factories import open_event, staff_of, ticket_for
from apps.events.models import Event
from apps.events.tests.factories import TicketTypeFactory
from apps.organizations.models import Membership
from apps.organizations.tests.factories import MembershipFactory
from apps.ticketing.models import Reservation, Ticket

pytestmark = pytest.mark.django_db

ORGANIZER_PREFIX = "api/v1/organizations/<slug:org_slug>/"
METHODS = ["get", "post", "put", "patch", "delete"]


def routes(resolver: URLResolver, prefix: str = ""):
    for entry in resolver.url_patterns:
        if isinstance(entry, URLResolver):
            yield from routes(entry, prefix + str(entry.pattern))
        elif isinstance(entry, URLPattern) and hasattr(entry.callback, "cls"):  # DRF views
            yield prefix + str(entry.pattern), entry.callback.cls


def organizer_routes() -> list[tuple[str, str]]:
    """(route, method) for every handler under organizations/<org_slug>/."""
    return [
        (route, method)
        for route, view in routes(get_resolver())
        if route.startswith(ORGANIZER_PREFIX)
        for method in METHODS
        if hasattr(view, method)
    ]


def url_for(route: str, values: dict[str, object]) -> str:
    url = "/" + route
    for name, value in values.items():
        for converter in ("slug", "int", "uuid"):
            url = url.replace(f"<{converter}:{name}>", str(value))
    assert "<" not in url, f"{route}: unknown URL parameter, add it to object_ids()"
    return url


@pytest.fixture
def victim():
    """An organization with one of everything an organizer route can point at."""
    event = open_event()
    owner = MembershipFactory(organization=event.organization, role=Membership.Role.OWNER)
    ticket = ticket_for(event)
    staff_of(event)
    return event, owner, ticket


def object_ids(event: Event, owner: Membership, ticket: Ticket) -> dict[str, object]:
    return {
        "event_id": event.pk,
        "ticket_type_id": event.ticket_types.get().pk,
        "assignment_id": event.staff.get().pk,
        "member_id": owner.pk,
        "reservation_id": ticket.reservation.pk,
    }


@pytest.fixture
def intruder() -> tuple[APIClient, Membership]:
    """OWNER of another organization: every role there, none here."""
    membership = MembershipFactory(role=Membership.Role.OWNER)
    TicketTypeFactory(event=open_event(organization=membership.organization))
    client = APIClient()
    client.force_authenticate(membership.user)
    return client, membership


def assert_untouched(event: Event, ticket: Ticket) -> None:
    event.refresh_from_db()
    ticket.refresh_from_db()
    assert event.status == Event.Status.PUBLISHED
    assert ticket.status == Ticket.Status.VALID
    assert ticket.reservation.status == Reservation.Status.CONFIRMED
    assert event.staff.exists()
    assert event.ticket_types.exists()


def test_the_route_list_is_not_empty():
    assert len(organizer_routes()) > 20


@pytest.mark.parametrize(("route", "method"), organizer_routes())
def test_another_organizations_routes_answer_404(victim, intruder, route, method):
    """Not a member: the organization itself does not exist for them (no 403 that confirms it)."""
    event, _, ticket = victim
    client, _ = intruder
    url = url_for(route, {"org_slug": event.organization.slug, **object_ids(*victim)})

    response = getattr(client, method)(url, {}, format="json")

    assert response.status_code == 404, f"{method.upper()} {url} → {response.status_code}"
    assert_untouched(event, ticket)


@pytest.mark.parametrize(
    ("route", "method"),
    [(r, m) for r, m in organizer_routes() if r.count("<") > 1],
)
def test_own_organization_with_another_organizations_ids_answers_404(
    victim, intruder, route, method
):
    """A member of their own organization cannot reach foreign objects by swapping the ids."""
    event, _, ticket = victim
    client, membership = intruder
    url = url_for(route, {"org_slug": membership.organization.slug, **object_ids(*victim)})

    response = getattr(client, method)(url, {}, format="json")

    assert response.status_code == 404, f"{method.upper()} {url} → {response.status_code}"
    assert_untouched(event, ticket)


def test_door_endpoints_hide_other_organizations_events(victim, intruder):
    event, _, ticket = victim
    client, _ = intruder

    scan = client.post(f"/api/v1/checkin/events/{event.pk}/scan/", {"token": ticket.token})
    activity = client.get(f"/api/v1/checkin/events/{event.pk}/activity/")

    assert (scan.status_code, activity.status_code) == (404, 404)
    assert_untouched(event, ticket)


def test_someone_elses_ticket_and_reservation_answer_404(victim, intruder):
    event, _, ticket = victim
    client, _ = intruder

    responses = [
        client.get(f"/api/v1/me/tickets/{ticket.pk}/"),
        client.get(f"/api/v1/me/tickets/{ticket.pk}/qr.svg"),
        client.post(f"/api/v1/reservations/{ticket.reservation.pk}/cancel/"),
    ]

    assert [r.status_code for r in responses] == [404, 404, 404]
    assert_untouched(event, ticket)
