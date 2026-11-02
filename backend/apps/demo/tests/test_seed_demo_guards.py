"""What protects real data. Each test starts empty, with a demo as small as possible."""

import uuid
from io import StringIO

import pytest
from django.core.files.base import ContentFile
from django.core.management import CommandError, call_command

from apps.accounts.models import User
from apps.demo.catalog import DEMO_DOMAIN, ORGANIZATIONS
from apps.demo.services import DemoDataExists, remove_demo, seed_demo
from apps.events.models import Event
from apps.organizations.models import Organization
from apps.organizations.services import create_organization

pytestmark = pytest.mark.django_db

ATTENDEES = 3


@pytest.fixture(autouse=True)
def media_and_images(settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = tmp_path
    monkeypatch.setattr(
        "apps.events.services._reencode",
        lambda upload: ContentFile(b"webp", name=f"{uuid.uuid4().hex}.webp"),
    )


@pytest.fixture
def real_organization():
    real = User.objects.create_user(email="real@example.com", password="x")
    return create_organization(user=real, name=ORGANIZATIONS[0].name)


def test_refuses_if_a_real_organization_has_a_demo_slug(real_organization):
    with pytest.raises(DemoDataExists):
        seed_demo(attendees=ATTENDEES)


def test_remove_ignores_a_real_organization_with_a_demo_slug(real_organization):
    remove_demo()
    assert Organization.objects.filter(pk=real_organization.pk).exists()


def test_command_needs_force_without_debug(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError, match="--force"):
        call_command("seed_demo", attendees=ATTENDEES)
    assert not Organization.objects.exists()


def test_command_if_empty_only_fills_once(settings):
    settings.DEBUG = True
    call_command("seed_demo", attendees=ATTENDEES, if_empty=True, stdout=StringIO())
    count = Event.objects.count()
    assert count

    out = StringIO()
    call_command("seed_demo", attendees=ATTENDEES, if_empty=True, stdout=out)

    assert "no se cambia nada" in out.getvalue()
    assert Event.objects.count() == count


def test_command_reset_replaces_the_previous_demo(settings):
    settings.DEBUG = True
    out = StringIO()
    call_command("seed_demo", attendees=ATTENDEES, stdout=out)
    assert f"lucia{DEMO_DOMAIN}" in out.getvalue()
    with pytest.raises(CommandError, match="--reset"):
        call_command("seed_demo", attendees=ATTENDEES, stdout=StringIO())

    count = Event.objects.count()
    call_command("seed_demo", attendees=ATTENDEES, reset=True, stdout=StringIO())
    assert Event.objects.count() == count
