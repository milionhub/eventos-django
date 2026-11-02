"""What the full demo contains. Seeding takes seconds (every booking is a real transaction),
so all these read-only tests share one seed, rolled back at the end of the module."""

import uuid

import pytest
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Count, Q
from django.test.utils import override_settings

from apps.accounts.models import User
from apps.checkin.models import CheckInLog
from apps.demo.catalog import DEMO_DOMAIN
from apps.demo.services import DemoDataExists, remove_demo, seed_demo
from apps.events.models import Event, TicketType
from apps.events.services import create_event
from apps.organizations.models import Membership, Organization
from apps.organizations.services import create_organization
from apps.ticketing.models import Reservation, Ticket

pytestmark = pytest.mark.django_db


@pytest.fixture(scope="module", autouse=True)
def seeded(django_db_setup, django_db_blocker, tmp_path_factory):
    media = tmp_path_factory.mktemp("media")
    with (
        django_db_blocker.unblock(),
        override_settings(MEDIA_ROOT=media),
        pytest.MonkeyPatch.context() as patch,
    ):
        # `_reencode` has its own tests; here it would only add a second per photo.
        patch.setattr(
            "apps.events.services._reencode",
            lambda upload: ContentFile(b"webp", name=f"{uuid.uuid4().hex}.webp"),
        )
        with transaction.atomic():
            seed_demo(attendees=40)
            yield media
            transaction.set_rollback(True)


def test_counters_match_the_rows_they_count():
    """The point of going through the services: nothing can disagree."""
    categories = TicketType.objects.annotate(
        confirmed=Count("reservations", filter=Q(reservations__status="CONFIRMED"))
    )
    assert categories.exists()
    for category in categories:
        assert category.reserved_count == category.confirmed, category


def test_every_used_ticket_has_exactly_one_valid_scan():
    used = Ticket.objects.filter(status=Ticket.Status.USED)
    assert used.exists()
    for ticket in used:
        assert ticket.checkin_logs.filter(result=CheckInLog.Result.VALID).count() == 1


def test_covers_every_event_state():
    assert Event.objects.filter(status=Event.Status.DRAFT).exists()
    assert Event.objects.filter(status=Event.Status.CANCELLED).exists()
    published = Event.objects.filter(status=Event.Status.PUBLISHED)
    assert any(event.is_finished for event in published)
    assert any(not event.is_finished for event in published)
    # Images are real files, and some events keep none to show the date poster.
    assert Event.objects.exclude(image="").exists()
    assert Event.objects.filter(image="").exists()


def test_covers_every_role():
    roles = set(Membership.objects.values_list("role", flat=True))
    assert roles == set(Membership.Role.values)
    assert User.objects.filter(email=f"admin{DEMO_DOMAIN}", is_superuser=True).exists()


def test_the_door_saw_every_kind_of_result():
    results = set(CheckInLog.objects.values_list("result", flat=True))
    assert results == set(CheckInLog.Result.values)


def test_lucia_has_tickets_in_every_state():
    tickets = Ticket.objects.filter(reservation__user__email=f"lucia{DEMO_DOMAIN}")
    assert set(tickets.values_list("status", flat=True)) == set(Ticket.Status.values)


def test_past_rows_are_dated_in_the_past():
    finished = [event for event in Event.objects.all() if event.is_finished]
    assert finished
    for event in finished:
        for reservation in Reservation.objects.filter(event=event):
            assert reservation.created_at < event.start_at


def test_refuses_to_run_twice():
    with pytest.raises(DemoDataExists):
        seed_demo(attendees=40)


def test_remove_only_touches_the_demo(seeded, django_capture_on_commit_callbacks):
    real = User.objects.create_user(email="real@example.com", password="x")
    organization = create_organization(user=real, name="Sala de verdad")
    any_event = Event.objects.first()
    create_event(
        organization=organization,
        user=real,
        title="Evento de verdad",
        location="Aquí",
        start_at=any_event.start_at,
        end_at=any_event.end_at,
        capacity=10,
    )
    assert list(seeded.glob("events/*"))

    with django_capture_on_commit_callbacks(execute=True):
        remove_demo()

    assert list(Organization.objects.values_list("name", flat=True)) == ["Sala de verdad"]
    assert list(Event.objects.values_list("title", flat=True)) == ["Evento de verdad"]
    assert list(User.objects.values_list("email", flat=True)) == ["real@example.com"]
    assert not list(seeded.glob("events/*"))
