from datetime import timedelta

import pytest
from django.utils import timezone

from apps.checkin.models import CheckInLog
from apps.checkin.services import checkin_opens_at, scan
from apps.checkin.tests.factories import open_event, staff_of, ticket_for
from apps.events.models import Event
from apps.organizations.models import Membership
from apps.organizations.tests.factories import MembershipFactory
from apps.ticketing.models import Ticket
from apps.ticketing.services import cancel_reservation

pytestmark = pytest.mark.django_db
Result = CheckInLog.Result


@pytest.fixture
def event() -> Event:
    return open_event()


@pytest.fixture
def staff(event):
    return staff_of(event)


# --- the seven results (RN-32) ------------------------------------------------------------


def test_valid_marks_the_ticket_used_and_logs_it(event, staff):
    ticket = ticket_for(event)

    outcome = scan(event=event, token=ticket.token, staff=staff)

    ticket.refresh_from_db()
    assert outcome.result == Result.VALID
    assert ticket.status == Ticket.Status.USED
    assert ticket.checked_in_by == staff
    assert ticket.checked_in_at is not None
    assert outcome.log.ticket == ticket and outcome.log.result == Result.VALID


def test_a_second_scan_is_already_used_and_keeps_the_first_time(event, staff):
    ticket = ticket_for(event)
    first = scan(event=event, token=ticket.token, staff=staff)

    second = scan(event=event, token=ticket.token, staff=staff)

    assert second.result == Result.ALREADY_USED
    assert second.ticket.checked_in_at == first.ticket.checked_in_at  # "used at 20:03"


def test_cancelled_ticket(event, staff):
    ticket = ticket_for(event)
    cancel_reservation(reservation=ticket.reservation, cancelled_by=staff, as_organizer=True)

    assert scan(event=event, token=ticket.token, staff=staff).result == Result.CANCELLED


def test_unknown_token_is_logged_without_storing_what_was_scanned(event, staff):
    outcome = scan(event=event, token="no-existe", staff=staff)

    assert outcome.result == Result.NOT_FOUND
    assert outcome.log.ticket is None


def test_a_ticket_for_another_event(event, staff):
    other = ticket_for(open_event(organization=event.organization))

    outcome = scan(event=event, token=other.token, staff=staff)

    other.refresh_from_db()
    assert outcome.result == Result.WRONG_EVENT
    assert other.status == Ticket.Status.VALID  # untouched


def test_unauthorized_users_are_rejected_and_logged(event):
    ticket = ticket_for(event)
    unassigned = MembershipFactory(organization=event.organization, role=Membership.Role.STAFF).user

    outcome = scan(event=event, token=ticket.token, staff=unassigned)

    ticket.refresh_from_db()
    assert outcome.result == Result.UNAUTHORIZED
    assert ticket.status == Ticket.Status.VALID
    assert CheckInLog.objects.filter(staff=unassigned, result=Result.UNAUTHORIZED).exists()


# --- RN-29: the door window ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("offset", "expected"),
    [
        (-timedelta(minutes=1), Result.EVENT_NOT_ACTIVE),  # one minute too early
        (timedelta(0), Result.VALID),  # exactly when the door opens
    ],
)
def test_the_door_opens_3_hours_before(event, staff, offset, expected):
    ticket = ticket_for(event)

    outcome = scan(
        event=event, token=ticket.token, staff=staff, now=checkin_opens_at(event) + offset
    )

    assert outcome.result == expected


def test_the_door_closes_when_the_event_ends(event, staff):
    ticket = ticket_for(event)

    outcome = scan(
        event=event, token=ticket.token, staff=staff, now=event.end_at + timedelta(minutes=1)
    )

    assert outcome.result == Result.EVENT_NOT_ACTIVE


def test_nothing_is_validated_at_a_cancelled_event(event, staff):
    ticket = ticket_for(event)
    Event.objects.filter(pk=event.pk).update(status=Event.Status.CANCELLED)
    event.refresh_from_db()

    assert scan(event=event, token=ticket.token, staff=staff).result == Result.EVENT_NOT_ACTIVE


# --- RN-28: who can validate --------------------------------------------------------------


@pytest.mark.parametrize("role", [Membership.Role.OWNER, Membership.Role.MANAGER])
def test_owners_and_managers_validate_without_being_assigned(event, role):
    organizer = MembershipFactory(organization=event.organization, role=role).user

    assert scan(event=event, token=ticket_for(event).token, staff=organizer).result == Result.VALID


def test_staff_assigned_elsewhere_cannot_validate_here(event):
    elsewhere = staff_of(open_event(organization=event.organization))

    assert scan(event=event, token=ticket_for(event).token, staff=elsewhere).result == (
        Result.UNAUTHORIZED
    )


# --- RN-31: every attempt is logged ---------------------------------------------------------


def test_every_attempt_is_logged(event, staff):
    ticket = ticket_for(event)
    tokens = [ticket.token, ticket.token, "nope"]

    results = [scan(event=event, token=t, staff=staff).result for t in tokens]

    assert results == [Result.VALID, Result.ALREADY_USED, Result.NOT_FOUND]
    assert (
        list(CheckInLog.objects.filter(event=event).order_by("pk").values_list("result", flat=True))
        == results
    )


def test_logs_are_timestamped_with_the_scan_time(event, staff):
    moment = timezone.now()

    log = scan(event=event, token="x", staff=staff, now=moment).log

    assert log.checked_at == moment
