"""RN-04 under concurrency. Needs PostgreSQL (row locks): never run this on SQLite."""

import threading

import pytest
from django.db import connection

from apps.organizations.models import Membership
from apps.organizations.services import LastOwner, change_member_role
from apps.organizations.tests.factories import MembershipFactory

Role = Membership.Role


@pytest.mark.django_db(transaction=True)
def test_two_owners_demoting_each_other_at_once_leave_one_owner():
    first = MembershipFactory(role=Role.OWNER)
    second = MembershipFactory(organization=first.organization, role=Role.OWNER)
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def demote(membership: Membership) -> None:
        try:
            barrier.wait()  # start both transactions as close together as possible
            change_member_role(membership=membership, role=Role.MANAGER)
            outcomes.append("ok")
        except LastOwner:
            outcomes.append("last_owner")
        finally:
            connection.close()  # each thread has its own connection

    threads = [threading.Thread(target=demote, args=(m,)) for m in (first, second)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["last_owner", "ok"]
    assert Membership.objects.filter(organization=first.organization, role=Role.OWNER).count() == 1
