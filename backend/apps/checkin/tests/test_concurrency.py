"""RN-30 under real concurrency. Needs PostgreSQL: never run these on SQLite."""

import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import connection

from apps.checkin.models import CheckInLog
from apps.checkin.services import scan
from apps.checkin.tests.factories import open_event, staff_of, ticket_for
from apps.ticketing.models import Ticket

pytestmark = pytest.mark.django_db(transaction=True)


def scan_at_once(event, token: str, scanners: list) -> Counter:
    barrier = threading.Barrier(len(scanners))

    def attempt(staff) -> str:
        try:
            barrier.wait()
            return scan(event=event, token=token, staff=staff).result
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=len(scanners)) as pool:
        return Counter(pool.map(attempt, scanners))


def test_two_doors_scanning_the_same_ticket_let_one_person_in():
    """The headline test of the phase: two simultaneous scans → 1 VALID + 1 ALREADY_USED."""
    event = open_event()
    ticket = ticket_for(event)
    doors = [staff_of(event), staff_of(event)]

    outcomes = scan_at_once(event, ticket.token, doors)

    ticket.refresh_from_db()
    assert outcomes == {"VALID": 1, "ALREADY_USED": 1}
    assert ticket.status == Ticket.Status.USED
    assert CheckInLog.objects.filter(result="VALID").count() == 1


def test_ten_scans_at_once_still_validate_once():
    event = open_event()
    ticket = ticket_for(event)
    staff = staff_of(event)

    outcomes = scan_at_once(event, ticket.token, [staff] * 10)

    assert outcomes == {"VALID": 1, "ALREADY_USED": 9}
    assert CheckInLog.objects.filter(event=event).count() == 10  # every attempt logged
