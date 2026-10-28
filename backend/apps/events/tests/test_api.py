from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.events.models import Event
from apps.events.tests.factories import EventFactory, TicketTypeFactory
from apps.organizations.models import Membership, Organization
from apps.organizations.tests.factories import MembershipFactory, OrganizationFactory

pytestmark = pytest.mark.django_db
Role = Membership.Role


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def org() -> Organization:
    return OrganizationFactory(slug="sala-apolo")


@pytest.fixture
def manager(org):
    return MembershipFactory(organization=org, role=Role.MANAGER).user


def iso(days: float) -> str:
    return (timezone.now() + timedelta(days=days)).isoformat()


EVENT_DATA = {
    "title": "Jazz en Apolo",
    "location": "Barcelona",
    "start_at": iso(7),
    "end_at": iso(7.1),
    "capacity": 200,
}


# --- happy path -------------------------------------------------------------------


def test_create_edit_and_publish_an_event(org, manager):
    client = client_for(manager)
    created = client.post(reverse("events", kwargs={"org_slug": org.slug}), EVENT_DATA)
    assert created.status_code == 201
    event = created.json()
    assert event["status"] == "DRAFT"
    assert event["publish_blockers"] == ["Añade al menos una categoría de entrada."]

    url = reverse("event", kwargs={"org_slug": org.slug, "event_id": event["id"]})
    edited = client.patch(url, {"description": "Noche de jazz"})
    assert edited.json()["description"] == "Noche de jazz"

    TicketTypeFactory(event_id=event["id"], capacity=150)
    detail = client.get(url).json()
    assert detail["publish_blockers"] == []
    assert detail["allocated_capacity"] == 150

    published = client.post(
        reverse("event-publish", kwargs={"org_slug": org.slug, "event_id": event["id"]})
    )
    assert published.status_code == 200
    assert published.json()["status"] == "PUBLISHED"


def test_list_is_paginated_scoped_and_filterable(org, manager):
    EventFactory.create_batch(2, organization=org)
    EventFactory(organization=org, status=Event.Status.CANCELLED)
    EventFactory()  # another organization's event

    client = client_for(manager)
    everything = client.get(reverse("events", kwargs={"org_slug": org.slug})).json()
    cancelled = client.get(
        reverse("events", kwargs={"org_slug": org.slug}), {"status": "CANCELLED"}
    ).json()

    assert everything["count"] == 3
    assert cancelled["count"] == 1
    bad = client.get(reverse("events", kwargs={"org_slug": org.slug}), {"status": "WHATEVER"})
    assert bad.status_code == 400


# --- business errors over HTTP -----------------------------------------------------


def test_publish_explains_why_it_cannot(org, manager):
    event = EventFactory(organization=org)

    response = client_for(manager).post(
        reverse("event-publish", kwargs={"org_slug": org.slug, "event_id": event.pk})
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "not_publishable",
        "detail": "Añade al menos una categoría de entrada.",
    }


def test_invalid_dates_are_rejected(org, manager):
    response = client_for(manager).post(
        reverse("events", kwargs={"org_slug": org.slug}), {**EVENT_DATA, "end_at": iso(6)}
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_dates"


def test_status_and_slug_cannot_be_set_by_the_client(org, manager):
    response = client_for(manager).post(
        reverse("events", kwargs={"org_slug": org.slug}),
        {**EVENT_DATA, "status": "PUBLISHED", "slug": "otro"},
    )

    assert (response.json()["status"], response.json()["slug"]) == ("DRAFT", "jazz-en-apolo")


# --- permission matrix and isolation -------------------------------------------------

ENDPOINTS = {
    "list": ("get", "events", None),
    "create": ("post", "events", EVENT_DATA),
    "detail": ("get", "event", None),
    "edit": ("patch", "event", {"title": "Nuevo"}),
    "publish": ("post", "event-publish", None),
    "cancel": ("post", "event-cancel", None),
}

EXPECTED = {
    #             OWNER  MANAGER  STAFF  outsider
    "list":     (200,   200,     200,   404),  # STAFF: only assigned events
    "create":   (201,   201,     403,   404),
    "detail":   (200,   200,     404,   404),  # STAFF: not assigned here
    "edit":     (200,   200,     403,   404),
    "publish":  (200,   200,     403,   404),
    "cancel":   (200,   200,     403,   404),
}  # fmt: skip

CALLERS = ["OWNER", "MANAGER", "STAFF", "outsider"]


@pytest.mark.parametrize("caller", CALLERS)
@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_permission_matrix(org, endpoint, caller):
    event = EventFactory(organization=org)
    TicketTypeFactory(event=event)  # publishable
    if caller == "outsider":
        user = MembershipFactory(role=Role.OWNER).user  # owner of another organization
    else:
        user = MembershipFactory(organization=org, role=caller).user

    method, name, data = ENDPOINTS[endpoint]
    kwargs = {"org_slug": org.slug}
    if name != "events":
        kwargs["event_id"] = event.pk
    response = getattr(client_for(user), method)(reverse(name, kwargs=kwargs), data)

    assert response.status_code == EXPECTED[endpoint][CALLERS.index(caller)]


def test_another_organizations_event_is_404_through_my_organization(org, manager):
    foreign = EventFactory()  # belongs to some other organization

    for name in ["event", "event-publish", "event-cancel"]:
        method = "get" if name == "event" else "post"
        response = getattr(client_for(manager), method)(
            reverse(name, kwargs={"org_slug": org.slug, "event_id": foreign.pk})
        )
        assert response.status_code == 404, name

    foreign.refresh_from_db()
    assert foreign.status == Event.Status.DRAFT
