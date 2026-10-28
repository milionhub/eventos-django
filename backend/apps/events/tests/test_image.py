"""Event image upload (ADR-0008): only real images, re-encoded, never trusted as sent."""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from apps.events.models import Event
from apps.events.services import (
    EventNotEditable,
    ImageTooLarge,
    InvalidImage,
    cancel_event,
    remove_event_image,
    set_event_image,
)
from apps.events.tests.factories import EventFactory
from apps.organizations.models import Membership
from apps.organizations.tests.factories import MembershipFactory

pytestmark = pytest.mark.django_db
Role = Membership.Role


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def image_file(fmt="PNG", size=(2400, 1350), name="cartel.png", exif=None) -> SimpleUploadedFile:
    buffer = io.BytesIO()
    image = Image.new("RGB", size, (255, 90, 78))
    kwargs = {"exif": exif} if exif is not None else {}
    image.save(buffer, format=fmt, **kwargs)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f"image/{fmt.lower()}")


def stored(event: Event) -> Image.Image:
    event.image.open("rb")
    return Image.open(io.BytesIO(event.image.read()))


# --- service ------------------------------------------------------------------------------


def test_uploads_are_re_encoded_as_webp_and_resized():
    event = set_event_image(event=EventFactory(), upload=image_file())

    image = stored(event)
    assert image.format == "WEBP"
    assert image.size == (1600, 900)  # max width, same aspect ratio
    assert event.image.name.startswith("events/") and event.image.name.endswith(".webp")
    assert "cartel" not in event.image.name  # the client's file name is never used


def test_exif_metadata_is_dropped():
    exif = Image.Exif()
    exif[0x010F] = "Móvil de alguien"  # camera make; GPS would be stripped just the same
    event = set_event_image(event=EventFactory(), upload=image_file("JPEG", exif=exif.tobytes()))

    assert not stored(event).getexif()


def test_a_text_file_named_png_is_rejected():
    fake = SimpleUploadedFile("cartel.png", b"<?php system($_GET['x']); ?>", "image/png")

    with pytest.raises(InvalidImage):
        set_event_image(event=EventFactory(), upload=fake)


def test_other_image_formats_are_rejected():
    with pytest.raises(InvalidImage):
        set_event_image(event=EventFactory(), upload=image_file("GIF", name="a.gif"))


def test_files_over_5_mb_are_rejected(monkeypatch):
    monkeypatch.setattr("apps.events.services.MAX_IMAGE_BYTES", 100)

    with pytest.raises(ImageTooLarge):
        set_event_image(event=EventFactory(), upload=image_file())


def test_replacing_or_removing_deletes_the_old_file(media_root, django_capture_on_commit_callbacks):
    event = EventFactory()
    with django_capture_on_commit_callbacks(execute=True):
        first = set_event_image(event=event, upload=image_file()).image.name
    with django_capture_on_commit_callbacks(execute=True):
        second = set_event_image(event=event, upload=image_file()).image.name
    assert not (media_root / first).exists()
    assert (media_root / second).exists()

    with django_capture_on_commit_callbacks(execute=True):
        event = remove_event_image(event=event)

    assert not event.image
    assert not (media_root / second).exists()


def test_cancelled_events_keep_their_image():
    event = EventFactory()
    cancel_event(event=event)

    with pytest.raises(EventNotEditable):
        set_event_image(event=event, upload=image_file())


# --- API ----------------------------------------------------------------------------------


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.mark.parametrize(
    ("role", "expected"),
    [(Role.OWNER, 200), (Role.MANAGER, 200), (Role.STAFF, 403), (None, 404)],
)
def test_upload_permissions(role, expected):
    event = EventFactory()
    if role is None:
        user = MembershipFactory(role=Role.OWNER).user  # owner of another organization
    else:
        user = MembershipFactory(organization=event.organization, role=role).user
    url = reverse("event-image", kwargs={"org_slug": event.organization.slug, "event_id": event.pk})

    response = client_for(user).put(url, {"image": image_file()}, format="multipart")

    assert response.status_code == expected
    if expected == 200:
        assert response.json()["image_url"].startswith("/media/events/")


def test_the_image_shows_up_in_the_public_api():
    event = set_event_image(event=EventFactory(status=Event.Status.PUBLISHED), upload=image_file())

    data = APIClient().get(reverse("public-event", kwargs={"slug": event.slug})).json()

    assert data["image_url"] == event.image.url


def test_invalid_files_are_explained_over_http():
    event = EventFactory()
    owner = MembershipFactory(organization=event.organization, role=Role.OWNER).user
    url = reverse("event-image", kwargs={"org_slug": event.organization.slug, "event_id": event.pk})
    fake = SimpleUploadedFile("x.png", b"not an image", "image/png")

    response = client_for(owner).put(url, {"image": fake}, format="multipart")

    assert (response.status_code, response.json()["code"]) == (400, "invalid_image")


def test_the_rest_of_the_api_still_only_takes_json():
    event = EventFactory()
    owner = MembershipFactory(organization=event.organization, role=Role.OWNER).user
    url = reverse("event", kwargs={"org_slug": event.organization.slug, "event_id": event.pk})

    response = client_for(owner).patch(url, {"title": "X"}, format="multipart")

    assert response.status_code == 415
