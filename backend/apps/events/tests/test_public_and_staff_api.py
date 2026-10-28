from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.events.models import Event, EventStaff
from apps.events.tests.factories import EventFactory, TicketTypeFactory
from apps.organizations.models import Membership, Organization
from apps.organizations.tests.factories import MembershipFactory, OrganizationFactory

pytestmark = pytest.mark.django_db
Role = Membership.Role
Status = Event.Status


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def in_days(days: float):
    return timezone.now() + timedelta(days=days)


@pytest.fixture
def org() -> Organization:
    return OrganizationFactory(slug="sala-apolo")


# --- public endpoints ---------------------------------------------------------------------


def published(**kwargs) -> Event:
    event = EventFactory(status=Status.PUBLISHED, **kwargs)
    TicketTypeFactory(event=event, capacity=30, reserved_count=10)
    TicketTypeFactory(event=event, capacity=5, reserved_count=5)  # sold out
    return event


def test_public_list_shows_only_published_upcoming_events_without_login():
    visible = published(title="Jazz", start_at=in_days(3), end_at=in_days(3.1))
    published(title="Ya pasó", start_at=in_days(-2), end_at=in_days(-1.9))  # finished
    EventFactory(title="Borrador")
    EventFactory(title="Cancelado", status=Status.CANCELLED)

    response = APIClient().get(reverse("public-events"))

    assert response.status_code == 200
    assert [e["slug"] for e in response.json()["results"]] == [visible.slug]
    assert response.json()["results"][0]["available"] == 20  # 20 + 0


def test_public_list_ignores_a_stale_token():
    published()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer not-a-valid-token")

    assert client.get(reverse("public-events")).status_code == 200


def test_public_list_search_and_date_filter():
    published(title="Noche de Jazz", location="Barcelona", start_at=in_days(3), end_at=in_days(3.1))
    published(title="Indie", location="Bilbao", start_at=in_days(30), end_at=in_days(30.1))
    url = reverse("public-events")

    by_title = APIClient().get(url, {"q": "jazz"}).json()["results"]
    by_place = APIClient().get(url, {"q": "bilbao"}).json()["results"]
    later = APIClient().get(url, {"from": in_days(10).date().isoformat()}).json()["results"]

    assert [e["title"] for e in by_title] == ["Noche de Jazz"]
    assert [e["title"] for e in by_place] == ["Indie"]
    assert [e["title"] for e in later] == ["Indie"]
    assert APIClient().get(url, {"from": "mañana"}).status_code == 400


def test_public_detail_shows_availability_per_category():
    event = published()

    data = APIClient().get(reverse("public-event", kwargs={"slug": event.slug})).json()

    assert data["available"] == 20
    assert [(t["available"], t["sold_out"]) for t in data["ticket_types"]] == [
        (20, False),
        (0, True),
    ]
    assert "reserved_count" not in data["ticket_types"][0]  # internal numbers stay private


@pytest.mark.parametrize("status", [Status.DRAFT, Status.CANCELLED])
def test_unpublished_events_are_not_public(status):
    event = EventFactory(status=status)

    response = APIClient().get(reverse("public-event", kwargs={"slug": event.slug}))

    assert response.status_code == 404


# --- STAFF visibility (requirements.md §4) ---------------------------------------------------


def test_staff_only_see_the_events_they_are_assigned_to(org):
    assigned, other = EventFactory(organization=org), EventFactory(organization=org)
    staff = MembershipFactory(organization=org, role=Role.STAFF).user
    EventStaff.objects.create(event=assigned, user=staff)
    client = client_for(staff)

    listing = client.get(reverse("events", kwargs={"org_slug": org.slug})).json()
    mine = client.get(reverse("event", kwargs={"org_slug": org.slug, "event_id": assigned.pk}))
    theirs = client.get(reverse("event", kwargs={"org_slug": org.slug, "event_id": other.pk}))
    edit = client.patch(
        reverse("event", kwargs={"org_slug": org.slug, "event_id": assigned.pk}), {"title": "X"}
    )

    assert [e["id"] for e in listing["results"]] == [assigned.pk]
    assert (mine.status_code, theirs.status_code, edit.status_code) == (200, 404, 403)


# --- ticket types and staff endpoints: permissions ---------------------------------------

CALLERS = ["OWNER", "MANAGER", "STAFF", "outsider"]
NEW_TYPE = {"name": "VIP", "capacity": 5}
ENDPOINTS = {
    "ticket_types.get": ("get", "ticket-types", None, (200, 200, 403, 404)),
    "ticket_types.post": ("post", "ticket-types", NEW_TYPE, (201, 201, 403, 404)),
    "ticket_type.patch": ("patch", "ticket-type", {"capacity": 6}, (200, 200, 403, 404)),
    "ticket_type.delete": ("delete", "ticket-type", None, (204, 204, 403, 404)),
    "staff.get": ("get", "staff", None, (200, 200, 403, 404)),
    "staff.post": ("post", "staff", "member", (201, 201, 403, 404)),
    "assignment.delete": ("delete", "staff-assignment", None, (204, 204, 403, 404)),
}  # fmt: skip


@pytest.mark.parametrize("caller", CALLERS)
@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_permission_matrix(org, endpoint, caller):
    event = EventFactory(organization=org)
    ticket_type = TicketTypeFactory(event=event, capacity=5)
    newcomer = MembershipFactory(organization=org, role=Role.STAFF).user
    assignment = EventStaff.objects.create(
        event=event, user=MembershipFactory(organization=org, role=Role.STAFF).user
    )
    if caller == "outsider":
        user = MembershipFactory(role=Role.OWNER).user
    else:
        user = MembershipFactory(organization=org, role=caller).user
        if caller == "STAFF":
            EventStaff.objects.create(event=event, user=user)  # even assigned staff can't manage

    method, name, data, expected = ENDPOINTS[endpoint]
    if data == "member":
        data = {"user": newcomer.pk}
    kwargs = {"org_slug": org.slug, "event_id": event.pk}
    if name == "ticket-type":
        kwargs["ticket_type_id"] = ticket_type.pk
    if name == "staff-assignment":
        kwargs["assignment_id"] = assignment.pk
    response = getattr(client_for(user), method)(reverse(name, kwargs=kwargs), data)

    assert response.status_code == expected[CALLERS.index(caller)]


def test_capacity_errors_are_explained(org):
    manager = MembershipFactory(organization=org, role=Role.MANAGER).user
    event = EventFactory(organization=org, capacity=10)

    response = client_for(manager).post(
        reverse("ticket-types", kwargs={"org_slug": org.slug, "event_id": event.pk}),
        {"name": "General", "capacity": 11},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "capacity_exceeded"


def test_assigning_a_non_member_is_explained(org):
    manager = MembershipFactory(organization=org, role=Role.MANAGER).user
    event = EventFactory(organization=org)
    stranger = MembershipFactory(role=Role.STAFF).user  # member of another organization

    response = client_for(manager).post(
        reverse("staff", kwargs={"org_slug": org.slug, "event_id": event.pk}),
        {"user": stranger.pk},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "not_a_member"
