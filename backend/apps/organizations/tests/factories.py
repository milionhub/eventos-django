import factory

from apps.accounts.tests.factories import UserFactory
from apps.organizations.models import Membership, Organization


class OrganizationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Organization

    name = factory.Sequence(lambda n: f"Organización {n}")
    slug = factory.Sequence(lambda n: f"organizacion-{n}")


class MembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Membership

    user = factory.SubFactory(UserFactory)
    organization = factory.SubFactory(OrganizationFactory)
    role = Membership.Role.OWNER
