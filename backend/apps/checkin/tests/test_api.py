from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from apps.checkin.tests.factories import open_event, staff_of, ticket_for
from apps.events.models import Event, EventStaff
from apps.organizations.models import Membership
from apps.organizations.tests.factories import MembershipFactory

pytestmark = pytest.mark.django_db
Role = Membership.Role


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def scan_url(event) -> str:
    return reverse("checkin-scan", kwargs={"event_id": event.pk})


# --- events where I can validate --------------------------------------------------------------


def test_lists_only_events_i_can_validate_with_their_door_window():
    event = open_event()
    staff = staff_of(event)
    open_event(organization=event.organization)  # same organization, not assigned
    later = open_event(organization=event.organization, start_at=timezone.now() + timedelta(days=2))
    EventStaff.objects.create(event=later, user=staff)

    data = client_for(staff).get(reverse("checkin-events")).json()

    assert [(e["id"], e["is_open"]) for e in data] == [(event.pk, True), (later.pk, False)]
    assert data[1]["opens_at"]


def test_organizers_see_all_their_events_but_not_finished_ones():
    event = open_event()
    owner = MembershipFactory(organization=event.organization, role=Role.OWNER).user
    past = timezone.now() - timedelta(days=1)
    open_event(organization=event.organization, start_at=past, end_at=past + timedelta(hours=2))
    open_event(organization=event.organization, status=Event.Status.DRAFT)

    data = client_for(owner).get(reverse("checkin-events")).json()

    assert [e["id"] for e in data] == [event.pk]


# --- scanning ----------------------------------------------------------------------------------


def test_scan_returns_what_the_door_needs_and_nothing_more():
    event = open_event()
    ticket = ticket_for(event, first_name="Laura", last_name="Gómez")

    response = client_for(staff_of(event)).post(scan_url(event), {"token": ticket.token})

    assert response.status_code == 200
    body = response.json()
    assert body["result"] == "VALID"
    assert body["ticket"]["holder_name"] == "Laura Gómez"
    assert body["ticket"]["ticket_type"] == "General"
    assert "email" not in str(body) and ticket.token not in str(body)


def test_business_results_are_200_for_the_door():
    event = open_event()
    staff = staff_of(event)

    response = client_for(staff).post(scan_url(event), {"token": "no-existe"})

    assert (response.status_code, response.json()["result"]) == (200, "NOT_FOUND")
    assert response.json()["ticket"] is None


def test_unauthorized_is_403_and_still_logged():
    event = open_event()
    unassigned = MembershipFactory(organization=event.organization, role=Role.STAFF).user

    response = client_for(unassigned).post(scan_url(event), {"token": "x"})

    assert (response.status_code, response.json()["result"]) == (403, "UNAUTHORIZED")
    assert event.checkin_logs.filter(staff=unassigned).exists()


def test_other_organizations_events_are_404():
    event = open_event()
    stranger = MembershipFactory(role=Role.OWNER).user  # owner somewhere else

    response = client_for(stranger).post(scan_url(event), {"token": "x"})

    assert response.status_code == 404
    assert not event.checkin_logs.exists()


def test_scanning_requires_an_account():
    assert APIClient().post(scan_url(open_event()), {"token": "x"}).status_code == 401


def test_scanning_is_throttled(monkeypatch):
    monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", {"checkin": "3/min"})
    event = open_event()
    client = client_for(staff_of(event))

    statuses = [client.post(scan_url(event), {"token": "x"}).status_code for _ in range(4)]

    assert statuses == [200, 200, 200, 429]


# --- activity ------------------------------------------------------------------------------


def test_activity_counts_people_in_and_lists_the_latest_attempts():
    event = open_event()
    staff = staff_of(event)
    tickets = [ticket_for(event) for _ in range(3)]
    client = client_for(staff)
    client.post(scan_url(event), {"token": tickets[0].token})
    client.post(scan_url(event), {"token": tickets[0].token})

    data = client.get(reverse("checkin-activity", kwargs={"event_id": event.pk})).json()

    assert data["stats"] == {"validated": 1, "expected": 3}
    assert [log["result"] for log in data["logs"]] == ["ALREADY_USED", "VALID"]


def test_activity_is_only_for_those_who_can_validate():
    event = open_event()
    unassigned = MembershipFactory(organization=event.organization, role=Role.STAFF).user

    response = client_for(unassigned).get(
        reverse("checkin-activity", kwargs={"event_id": event.pk})
    )

    assert response.status_code == 403
