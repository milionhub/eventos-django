"""RN-01 under concurrency. Needs PostgreSQL (unique index): never run this on SQLite."""

import threading

import pytest
from django.db import connection

from apps.accounts.models import User
from apps.accounts.services import EmailAlreadyRegistered, register_user


@pytest.mark.django_db(transaction=True)
def test_simultaneous_sign_ups_with_one_email_create_one_account():
    """Both requests can pass the "already registered?" check; the unique index decides."""
    barrier = threading.Barrier(5)
    outcomes: list[str] = []

    def sign_up(email: str) -> None:
        try:
            barrier.wait()
            register_user(email=email, password="Concierto-2026")
            outcomes.append("created")
        except EmailAlreadyRegistered:
            outcomes.append("taken")
        finally:
            connection.close()  # each thread has its own connection

    emails = [
        "ana@example.com",
        "Ana@example.com",
        "ana@EXAMPLE.com",
        "ANA@example.com",
        "ana@example.com",
    ]
    threads = [threading.Thread(target=sign_up, args=(email,)) for email in emails]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["created"] + ["taken"] * 4
    assert User.objects.count() == 1
