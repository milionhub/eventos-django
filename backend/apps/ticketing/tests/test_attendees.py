"""The organizer's attendee list, cancellations and CSV export (requirements.md R5, RN-21)."""

import csv
import io
from datetime import UTC, datetime, timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.events.models import Event, TicketType
from apps.organizations.models import Membership
from apps.organizations.tests.factories import MembershipFactory
from apps.ticketing import selectors
from apps.ticketing.exports import safe_cell
from apps.ticketing.models import Reservation, Ticket
from apps.ticketing.services import cancel_reservation, reserve
from apps.ticketing.tests.factories import bookable_ticket_type

pytestmark = pytest.mark.django_db
Role = Membership.Role


def book(ticket_type: TicketType, **user_kwargs) -> Reservation:
    return reserve(user=UserFactory(**user_kwargs), ticket_type_id=ticket_type.pk)


def organizer_of(event: Event, role: str = Role.MANAGER):
    return MembershipFactory(organization=event.organization, role=role).user


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def url(name: str, event: Event, **kwargs) -> str:
    return reverse(
        name, kwargs={"org_slug": event.organization.slug, "event_id": event.pk, **kwargs}
    )


def cancel_url(reservation: Reservation) -> str:
    return url("attendee-cancel", reservation.event, reservation_id=reservation.pk)


# --- the list ---------------------------------------------------------------------------------


def test_lists_every_reservation_newest_first_cancelled_included():
    ticket_type = bookable_ticket_type()
    first = book(ticket_type)
    second = book(ticket_type)
    cancel_reservation(reservation=first, cancelled_by=first.user)

    attendees = list(selectors.attendees_of(ticket_type.event))

    assert [r.pk for r in attendees] == [second.pk, first.pk]
    assert attendees[1].status == Reservation.Status.CANCELLED


@pytest.mark.parametrize(
    ("q", "found"),
    [
        ("ana", True),
        ("GÓMEZ", True),
        ("ana gómez", True),  # one word in each field
        ("gómez ana", True),
        ("ana.g@", True),  # email
        ("ana pérez", False),  # every word must match
    ],
)
def test_search_by_name_or_email_word_by_word(q, found):
    ticket_type = bookable_ticket_type()
    book(ticket_type, first_name="Ana", last_name="Gómez", email="ana.g@example.com")
    book(ticket_type, first_name="Luis", last_name="Pérez", email="luis@example.com")

    names = [r.user.first_name for r in selectors.attendees_of(ticket_type.event, q=q)]

    assert names == (["Ana"] if found else [])


def test_filter_by_ticket_status():
    ticket_type = bookable_ticket_type()
    inside = book(ticket_type)
    Ticket.objects.filter(reservation=inside).update(status=Ticket.Status.USED)
    book(ticket_type)

    used = selectors.attendees_of(ticket_type.event, ticket_status=Ticket.Status.USED)

    assert [r.pk for r in used] == [inside.pk]


def test_list_endpoint_is_paginated_and_never_shows_the_ticket_token():
    ticket_type = bookable_ticket_type(name="General")
    reservation = book(ticket_type, first_name="Ana", email="ana@example.com")

    response = client_for(organizer_of(ticket_type.event)).get(url("attendees", ticket_type.event))

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    (row,) = data["results"]
    assert row["id"] == str(reservation.pk)
    assert row["user"]["email"] == "ana@example.com"
    assert row["ticket_type"]["name"] == "General"
    assert row["ticket"]["status"] == "VALID"
    assert reservation.ticket.token not in response.content.decode()


def test_list_endpoint_applies_search_and_status():
    ticket_type = bookable_ticket_type()
    book(ticket_type, first_name="Ana")
    book(ticket_type, first_name="Luis")
    client = client_for(organizer_of(ticket_type.event))
    base = url("attendees", ticket_type.event)

    assert client.get(base, {"q": "ana"}).json()["count"] == 1
    assert client.get(base, {"status": "USED"}).json()["count"] == 0
    assert client.get(base, {"status": "NOPE"}).status_code == 400


def queries_to_list(attendees: int) -> int:
    ticket_type = bookable_ticket_type(capacity=50)
    for _ in range(attendees):
        book(ticket_type)
    client = client_for(organizer_of(ticket_type.event))
    with CaptureQueriesContext(connection) as queries:
        client.get(url("attendees", ticket_type.event))
    return len(queries)


def test_listing_takes_the_same_queries_for_2_or_15_attendees():
    assert queries_to_list(2) == queries_to_list(15)


# --- cancelling as organizer (RN-21) ----------------------------------------------------------


def test_organizer_cancels_and_the_seat_is_released():
    ticket_type = bookable_ticket_type()
    reservation = book(ticket_type)
    organizer = organizer_of(ticket_type.event)

    response = client_for(organizer).post(cancel_url(reservation))

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert response.json()["ticket"]["status"] == "CANCELLED"
    reservation.refresh_from_db()
    assert reservation.cancelled_by == organizer
    ticket_type.refresh_from_db()
    assert ticket_type.reserved_count == 0


def test_organizers_can_cancel_after_the_attendee_deadline():
    """RN-20 stops attendees 2 h before the start; organizers go on until the end."""
    ticket_type = bookable_ticket_type()
    reservation = book(ticket_type)
    start = timezone.now() + timedelta(minutes=30)
    Event.objects.filter(pk=ticket_type.event_id).update(
        start_at=start, end_at=start + timedelta(hours=2)
    )

    response = client_for(organizer_of(ticket_type.event)).post(cancel_url(reservation))

    assert response.status_code == 200


def test_nobody_cancels_once_the_event_is_over():
    ticket_type = bookable_ticket_type()
    reservation = book(ticket_type)
    start = timezone.now() - timedelta(hours=3)
    Event.objects.filter(pk=ticket_type.event_id).update(
        start_at=start, end_at=start + timedelta(hours=2)
    )

    response = client_for(organizer_of(ticket_type.event)).post(cancel_url(reservation))

    assert response.status_code == 409
    assert response.json()["code"] == "cancellation_closed"


@pytest.mark.parametrize(
    ("prepare", "code"),
    [
        (lambda r: Ticket.objects.filter(reservation=r).update(status="USED"), "ticket_used"),
        (lambda r: cancel_reservation(reservation=r, cancelled_by=r.user), "already_cancelled"),
    ],
)
def test_used_or_cancelled_reservations_cannot_be_cancelled(prepare, code):
    reservation = book(bookable_ticket_type())
    prepare(reservation)

    response = client_for(organizer_of(reservation.event)).post(cancel_url(reservation))

    assert response.status_code == 409
    assert response.json()["code"] == code


def test_a_reservation_of_another_event_is_404():
    mine = bookable_ticket_type().event
    theirs = book(bookable_ticket_type())
    organizer = organizer_of(mine)
    MembershipFactory(organization=theirs.event.organization, user=organizer, role=Role.OWNER)

    response = client_for(organizer).post(url("attendee-cancel", mine, reservation_id=theirs.pk))

    assert response.status_code == 404


# --- CSV --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ('=HYPERLINK("http://evil","Clic")', '\'=HYPERLINK("http://evil","Clic")'),
        ("+34 600 000 000", "'+34 600 000 000"),
        ("-1", "'-1"),
        ("@SUM(A1)", "'@SUM(A1)"),
        ("\tTab", "'\tTab"),
        ("Ana", "Ana"),
        ("Ana=Luis", "Ana=Luis"),  # only a leading trigger matters
        ("", ""),
    ],
)
def test_safe_cell_neutralizes_formulas(value, expected):
    assert safe_cell(value) == expected


def download(event: Event, **params):
    response = client_for(organizer_of(event)).get(url("attendees-csv", event), params)
    body = b"".join(response.streaming_content).decode("utf-8") if response.streaming else ""
    return response, body


def rows_of(body: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(body.removeprefix("﻿")), delimiter=";"))


def test_csv_download_for_spreadsheets():
    ticket_type = bookable_ticket_type(name="VIP")
    ticket_type.event.slug = "noche-de-jazz"
    ticket_type.event.save(update_fields=["slug"])
    book(ticket_type, first_name="Ana", last_name="Gómez", email="ana@example.com")

    response, body = download(ticket_type.event)

    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv; charset=utf-8"
    assert response["Content-Disposition"] == 'attachment; filename="asistentes-noche-de-jazz.csv"'
    assert response["Cache-Control"] == "no-store"
    assert body.startswith("﻿")  # Excel reads the accents as UTF-8
    header, row = rows_of(body)
    assert header == ["Nombre", "Apellidos", "Email", "Categoría", "Estado", "Reservada", "Entrada"]
    assert row[:5] == ["Ana", "Gómez", "ana@example.com", "VIP", "Válida"]
    assert row[6] == ""  # not checked in


def test_csv_neutralizes_a_malicious_name():
    ticket_type = bookable_ticket_type()
    book(ticket_type, first_name='=HYPERLINK("http://evil","Clic")', last_name="@x")

    _, body = download(ticket_type.event)

    row = rows_of(body)[1]
    assert row[0] == '\'=HYPERLINK("http://evil","Clic")'
    assert row[1] == "'@x"


def test_csv_times_are_in_the_requested_time_zone():
    ticket_type = bookable_ticket_type()
    reservation = book(ticket_type)
    checked_in = datetime(2026, 7, 1, 19, 30, tzinfo=UTC)
    Reservation.objects.filter(pk=reservation.pk).update(created_at=checked_in)
    Ticket.objects.filter(reservation=reservation).update(status="USED", checked_in_at=checked_in)

    _, body = download(ticket_type.event, tz="Europe/Madrid")

    row = rows_of(body)[1]
    assert row[4:] == ["Utilizada", "2026-07-01 21:30", "2026-07-01 21:30"]  # UTC+2 in July


def test_csv_defaults_to_utc_and_rejects_unknown_time_zones():
    ticket_type = bookable_ticket_type()
    book(ticket_type)
    client = client_for(organizer_of(ticket_type.event))
    csv_url = url("attendees-csv", ticket_type.event)

    assert client.get(csv_url, {"tz": "Mars/Olympus"}).status_code == 400
    assert client.get(csv_url, {"tz": "../../etc/passwd"}).status_code == 400
    assert client.get(csv_url).status_code == 200


def test_csv_exports_what_the_filters_show():
    ticket_type = bookable_ticket_type()
    book(ticket_type, first_name="Ana")
    book(ticket_type, first_name="Luis")

    _, body = download(ticket_type.event, q="luis")

    assert [row[0] for row in rows_of(body)[1:]] == ["Luis"]


# --- who may see attendees (§4) ---------------------------------------------------------------


def endpoints(reservation: Reservation) -> list[tuple[str, str]]:
    event = reservation.event
    return [
        ("get", url("attendees", event)),
        ("get", url("attendees-csv", event)),
        ("post", cancel_url(reservation)),
    ]


@pytest.mark.parametrize("index", [0, 1, 2])
def test_staff_cannot_see_or_cancel_attendees(index):
    reservation = book(bookable_ticket_type())
    staff = organizer_of(reservation.event, role=Role.STAFF)
    method, path = endpoints(reservation)[index]

    assert getattr(client_for(staff), method)(path).status_code == 403
    reservation.refresh_from_db()
    assert reservation.status == Reservation.Status.CONFIRMED


@pytest.mark.parametrize("index", [0, 1, 2])
def test_other_organizations_get_404(index):
    reservation = book(bookable_ticket_type())
    outsider = MembershipFactory(role=Role.OWNER).user
    method, path = endpoints(reservation)[index]

    assert getattr(client_for(outsider), method)(path).status_code == 404


@pytest.mark.parametrize("index", [0, 1, 2])
def test_attendees_require_an_account(index):
    reservation = book(bookable_ticket_type())
    method, path = endpoints(reservation)[index]

    assert getattr(APIClient(), method)(path).status_code == 401
