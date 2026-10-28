from datetime import timedelta

import factory
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.events.models import Event, TicketType
from apps.organizations.tests.factories import OrganizationFactory


class EventFactory(factory.django.DjangoModelFactory):
    """A draft event one week from now, two hours long."""

    class Meta:
        model = Event

    organization = factory.SubFactory(OrganizationFactory)
    created_by = factory.SubFactory(UserFactory)
    title = factory.Sequence(lambda n: f"Concierto {n}")
    slug = factory.Sequence(lambda n: f"concierto-{n}")
    location = "Sala Apolo, Barcelona"
    start_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))
    end_at = factory.LazyAttribute(lambda event: event.start_at + timedelta(hours=2))
    capacity = 100


class TicketTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TicketType

    event = factory.SubFactory(EventFactory)
    name = factory.Sequence(lambda n: f"General {n}")
    capacity = 50
