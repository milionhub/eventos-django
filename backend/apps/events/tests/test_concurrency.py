"""RN-13 under concurrency. Needs PostgreSQL (row locks): never run this on SQLite."""

import threading

import pytest
from django.db import connection

from apps.events.services import CapacityExceeded, create_ticket_type
from apps.events.tests.factories import EventFactory


@pytest.mark.django_db(transaction=True)
def test_two_categories_created_at_once_never_exceed_the_capacity():
    event = EventFactory(capacity=100)
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def create(name: str) -> None:
        try:
            barrier.wait()  # both fit alone (60 ≤ 100) but not together (120 > 100)
            create_ticket_type(event=event, name=name, capacity=60)
            outcomes.append("ok")
        except CapacityExceeded:
            outcomes.append("exceeded")
        finally:
            connection.close()

    threads = [threading.Thread(target=create, args=(name,)) for name in ("General", "VIP")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["exceeded", "ok"]
    assert sum(event.ticket_types.values_list("capacity", flat=True)) == 60
