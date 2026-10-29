import pytest

from apps.accounts.tests.factories import UserFactory
from apps.events.models import Event, EventStaff, TicketType
from apps.events.services import (
    AlreadyAssigned,
    CapacityBelowReserved,
    CapacityExceeded,
    DuplicateTicketTypeName,
    EventNotEditable,
    LastTicketType,
    NotAMember,
    TicketTypeInUse,
    assign_staff,
    cancel_event,
    create_ticket_type,
    delete_ticket_type,
    publish_event,
    update_ticket_type,
)
from apps.events.tests.factories import EventFactory, TicketTypeFactory
from apps.organizations.models import Membership
from apps.organizations.services import remove_member
from apps.organizations.tests.factories import MembershipFactory

pytestmark = pytest.mark.django_db
Role = Membership.Role


# --- ticket types: RN-13 (sum of quotas ≤ event capacity) ----------------------------------


def test_renaming_a_category_keeps_its_capacity_checks_out_of_the_way():
    ticket_type = TicketTypeFactory(name="General", capacity=50)

    update_ticket_type(ticket_type=ticket_type, name="Pista", description="De pie")

    ticket_type.refresh_from_db()
    assert (ticket_type.name, ticket_type.description, ticket_type.capacity) == (
        "Pista",
        "De pie",
        50,
    )


def test_categories_fit_exactly_into_the_capacity():
    event = EventFactory(capacity=100)

    create_ticket_type(event=event, name="General", capacity=80)
    create_ticket_type(event=event, name="VIP", capacity=20)

    assert sum(event.ticket_types.values_list("capacity", flat=True)) == 100


def test_a_category_cannot_exceed_the_remaining_capacity():
    event = EventFactory(capacity=100)
    create_ticket_type(event=event, name="General", capacity=80)

    with pytest.raises(CapacityExceeded):
        create_ticket_type(event=event, name="VIP", capacity=21)


def test_growing_a_category_counts_the_others_but_not_itself():
    event = EventFactory(capacity=100)
    general = create_ticket_type(event=event, name="General", capacity=60)
    create_ticket_type(event=event, name="VIP", capacity=30)

    update_ticket_type(ticket_type=general, capacity=70)  # 70 + 30 = 100
    with pytest.raises(CapacityExceeded):
        update_ticket_type(ticket_type=general, capacity=71)


def test_category_names_are_unique_per_event():
    event = EventFactory()
    create_ticket_type(event=event, name="VIP", capacity=10)

    with pytest.raises(DuplicateTicketTypeName):
        create_ticket_type(event=event, name="VIP", capacity=10)


# --- RN-14 and RN-15 --------------------------------------------------------------------


def test_quota_cannot_drop_below_reserved_tickets():
    ticket_type = TicketTypeFactory(capacity=50, reserved_count=30)

    update_ticket_type(ticket_type=ticket_type, capacity=30)
    with pytest.raises(CapacityBelowReserved):
        update_ticket_type(ticket_type=ticket_type, capacity=29)


def test_categories_with_reservations_cannot_be_deleted():
    ticket_type = TicketTypeFactory(reserved_count=1)

    with pytest.raises(TicketTypeInUse):
        delete_ticket_type(ticket_type=ticket_type)


def test_unused_categories_can_be_deleted():
    ticket_type = TicketTypeFactory()

    delete_ticket_type(ticket_type=ticket_type)

    assert not TicketType.objects.filter(pk=ticket_type.pk).exists()


def test_a_published_event_keeps_at_least_one_category():
    ticket_type = TicketTypeFactory()
    publish_event(event=ticket_type.event)

    with pytest.raises(LastTicketType):
        delete_ticket_type(ticket_type=ticket_type)


def test_categories_of_cancelled_events_are_frozen():
    event = EventFactory()
    cancel_event(event=event)

    with pytest.raises(EventNotEditable):
        create_ticket_type(event=event, name="VIP", capacity=10)


# --- staff --------------------------------------------------------------------------------


def test_assign_a_member_as_staff():
    event = EventFactory()
    member = MembershipFactory(organization=event.organization, role=Role.STAFF)

    assignment = assign_staff(event=event, user_id=member.user_id)

    assert assignment.user == member.user


def test_only_members_can_be_assigned():
    with pytest.raises(NotAMember):
        assign_staff(event=EventFactory(), user_id=UserFactory().pk)


def test_nobody_is_assigned_twice():
    event = EventFactory()
    member = MembershipFactory(organization=event.organization, role=Role.STAFF)
    assign_staff(event=event, user_id=member.user_id)

    with pytest.raises(AlreadyAssigned):
        assign_staff(event=event, user_id=member.user_id)


def test_leaving_the_organization_removes_staff_assignments():
    event = EventFactory()
    MembershipFactory(organization=event.organization, role=Role.OWNER)
    member = MembershipFactory(organization=event.organization, role=Role.STAFF)
    assign_staff(event=event, user_id=member.user_id)
    elsewhere = EventFactory()  # same person, staff of another organization's event
    MembershipFactory(organization=elsewhere.organization, user=member.user, role=Role.STAFF)
    assign_staff(event=elsewhere, user_id=member.user_id)

    remove_member(membership=member)

    assert list(EventStaff.objects.values_list("event_id", flat=True)) == [elsewhere.pk]


def test_events_are_draft_by_default_for_these_tests():
    assert EventFactory().status == Event.Status.DRAFT
