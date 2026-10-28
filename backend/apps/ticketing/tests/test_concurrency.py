"""ADR-0004 under real concurrency. Needs PostgreSQL: never run these on SQLite.

Each thread opens its own database connection, and a barrier releases them all at once so
the requests really overlap inside PostgreSQL.
"""

import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import connection

from apps.accounts.tests.factories import UserFactory
from apps.events.models import Event
from apps.events.services import cancel_event
from apps.ticketing.models import Reservation
from apps.ticketing.services import (
    AlreadyCancelled,
    AlreadyReserved,
    SoldOut,
    cancel_reservation,
    reserve,
)
from apps.ticketing.tests.factories import assert_counters_match_reservations, bookable_ticket_type

pytestmark = pytest.mark.django_db(transaction=True)


def run_at_once(attempts: list) -> Counter:
    """Run `reserve(**kwargs)` for each attempt, all at the same time. Returns the outcomes."""
    barrier = threading.Barrier(len(attempts))

    def attempt(kwargs) -> str:
        try:
            barrier.wait()
            reserve(**kwargs)
            return "confirmed"
        except SoldOut:
            return "sold_out"
        except AlreadyReserved:
            return "already_reserved"
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=len(attempts)) as pool:
        return Counter(pool.map(attempt, attempts))


def test_50_people_competing_for_10_seats():
    """The headline test of the project: never oversell."""
    ticket_type = bookable_ticket_type(capacity=10)
    users = UserFactory.create_batch(50)

    outcomes = run_at_once([{"user": u, "ticket_type_id": ticket_type.pk} for u in users])

    ticket_type.refresh_from_db()
    assert outcomes == {"confirmed": 10, "sold_out": 40}
    assert ticket_type.reserved_count == 10
    assert Reservation.objects.filter(status=Reservation.Status.CONFIRMED).count() == 10
    assert_counters_match_reservations()


def test_a_double_click_books_once_and_does_not_leak_seats():
    """Five simultaneous clicks of one user: one reservation, and the four rejected
    attempts give their incremented seat back (the transaction rolls back)."""
    ticket_type = bookable_ticket_type(capacity=10)
    user = UserFactory()

    outcomes = run_at_once([{"user": user, "ticket_type_id": ticket_type.pk}] * 5)

    ticket_type.refresh_from_db()
    assert outcomes == {"confirmed": 1, "already_reserved": 4}
    assert ticket_type.reserved_count == 1
    assert_counters_match_reservations()


# --- cancellations under concurrency --------------------------------------------------------


def run_threads(functions: list) -> list:
    """Run every function at the same time; return what each returned or raised."""
    barrier = threading.Barrier(len(functions))

    def run(function):
        try:
            barrier.wait()
            return function()
        except Exception as exc:  # collected for the assertions, not swallowed
            return exc
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=len(functions)) as pool:
        return list(pool.map(run, functions))


def test_cancelling_the_same_reservation_at_once_frees_one_seat():
    ticket_type = bookable_ticket_type(capacity=10)
    reservation = reserve(user=UserFactory(), ticket_type_id=ticket_type.pk)

    results = run_threads(
        [lambda: cancel_reservation(reservation=reservation, cancelled_by=reservation.user)] * 5
    )

    assert sum(isinstance(r, Reservation) for r in results) == 1
    assert sum(isinstance(r, AlreadyCancelled) for r in results) == 4
    ticket_type.refresh_from_db()
    assert ticket_type.reserved_count == 0  # not -4
    assert_counters_match_reservations()


def test_bookings_racing_an_event_cancellation_never_survive_it():
    ticket_type = bookable_ticket_type(capacity=50)
    users = UserFactory.create_batch(20)

    bookings = [lambda u=u: reserve(user=u, ticket_type_id=ticket_type.pk) for u in users]
    results = run_threads([*bookings, lambda: cancel_event(event=ticket_type.event)])

    assert isinstance(results[-1], Event)  # the cancellation itself succeeded
    assert not Reservation.objects.filter(status=Reservation.Status.CONFIRMED).exists()
    assert_counters_match_reservations()  # all back to 0


def test_counters_stay_consistent_while_people_book_and_cancel_at_once():
    ticket_type = bookable_ticket_type(capacity=10)
    existing = [reserve(user=u, ticket_type_id=ticket_type.pk) for u in UserFactory.create_batch(5)]
    newcomers = UserFactory.create_batch(15)

    cancels = [lambda r=r: cancel_reservation(reservation=r, cancelled_by=r.user) for r in existing]
    bookings = [lambda u=u: reserve(user=u, ticket_type_id=ticket_type.pk) for u in newcomers]
    run_threads([*cancels, *bookings])

    ticket_type.refresh_from_db()
    assert ticket_type.reserved_count <= ticket_type.capacity
    assert_counters_match_reservations()
