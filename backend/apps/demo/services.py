"""Demo data for screenshots, manual testing and `docker compose --profile demo`.

Everything goes through the real services (reserve, scan, cancel_event...), with their `now`
argument set to the past: the events of a month ago went through the same rules as a live
one, so the counters and logs cannot disagree with what the app would have produced. Only
the users are inserted in bulk, because hashing hundreds of passwords one by one takes minutes.

Removing the demo only touches rows it can recognise as its own, so it is safe on a database
that also holds real work: see `_demo_organizations`.
"""

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from django.contrib.auth.hashers import make_password
from django.core.files import File
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.models import User
from apps.checkin.models import CheckInLog
from apps.checkin.services import checkin_opens_at, scan
from apps.demo.catalog import (
    DEMO_DOMAIN,
    DEMO_PASSWORD,
    EVENTS,
    FIRST_NAMES,
    LAST_NAMES,
    ORGANIZATIONS,
    STAFF_ACCOUNTS,
    DemoEvent,
    Kind,
    Lucia,
    Org,
)
from apps.events.models import Event, TicketType
from apps.events.services import (
    assign_staff,
    cancel_event,
    create_event,
    create_ticket_type,
    publish_event,
    set_event_image,
)
from apps.organizations.models import Membership, Organization
from apps.organizations.services import add_member, create_organization
from apps.ticketing.models import Reservation, Ticket
from apps.ticketing.services import cancel_reservation, cancellation_deadline, reserve

IMAGES = Path(__file__).parent / "images"
MADRID = ZoneInfo("Europe/Madrid")
CANCELLED_SHARE = 0.06
# A draft with no categories still needs a venue capacity.
DEFAULT_CAPACITY = 100


class DemoDataExists(Exception):
    pass


@dataclass(frozen=True)
class SeedSummary:
    organizations: int
    users: int
    events: int
    reservations: int
    scans: int


def _demo_organizations() -> QuerySet[Organization]:
    """A slug alone could match an organization someone really created; its owner settles it."""
    return Organization.objects.filter(
        slug__in=[org.slug for org in ORGANIZATIONS],
        memberships__role=Membership.Role.OWNER,
        memberships__user__email__endswith=DEMO_DOMAIN,
    ).distinct()


@transaction.atomic
def remove_demo() -> None:
    """Delete the demo's rows and image files. Nothing else in the database is touched."""
    organization_ids = list(_demo_organizations().values_list("pk", flat=True))
    events = Event.objects.filter(organization_id__in=organization_ids)
    images = [event.image for event in events if event.image]

    # Booked and scanned rows are protected on purpose: they go first, in dependency order.
    CheckInLog.objects.filter(event__in=events).delete()
    Ticket.objects.filter(reservation__event__in=events).delete()
    Reservation.objects.filter(event__in=events).delete()
    TicketType.objects.filter(event__in=events).delete()
    events.delete()
    Organization.objects.filter(pk__in=organization_ids).delete()
    User.objects.filter(email__endswith=DEMO_DOMAIN).delete()

    def delete_files() -> None:
        for image in images:
            image.storage.delete(image.name)

    transaction.on_commit(delete_files)


@transaction.atomic
def seed_demo(
    *, attendees: int = 320, seed: int = 2026, now: datetime | None = None
) -> SeedSummary:
    """Create the whole demo, or nothing if anything fails. Dates are relative to `now`."""
    now = now or timezone.now()
    slugs = [org.slug for org in ORGANIZATIONS]
    if (
        Organization.objects.filter(slug__in=slugs).exists()
        or User.objects.filter(email__endswith=DEMO_DOMAIN).exists()
    ):
        raise DemoDataExists()

    rng = random.Random(seed)
    accounts = _create_users(attendees, rng)
    public = [user for user in accounts.values() if user.email.startswith("attendee.")]
    organizations = {org.key: _create_organization(org, accounts) for org in ORGANIZATIONS}
    for spec in EVENTS:
        _create_event(spec, organizations[spec.org], accounts["lucia"], public, rng, now)

    return SeedSummary(
        organizations=len(organizations),
        users=len(accounts),
        events=len(EVENTS),
        reservations=Reservation.objects.filter(event__organization__slug__in=slugs).count(),
        scans=CheckInLog.objects.filter(event__organization__slug__in=slugs).count(),
    )


def _create_users(attendees: int, rng: random.Random) -> dict[str, User]:
    password = make_password(DEMO_PASSWORD)
    users = [
        User(
            email=f"{key}{DEMO_DOMAIN}",
            first_name=first,
            last_name=last,
            password=password,
            is_staff=is_admin,
            is_superuser=is_admin,
        )
        for key, first, last, is_admin in STAFF_ACCOUNTS
    ]
    for n in range(attendees):
        first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
        email = f"attendee.{slugify(first)}.{slugify(last)}.{n}{DEMO_DOMAIN}"
        users.append(User(email=email, first_name=first, last_name=last, password=password))
    User.objects.bulk_create(users)
    return {user.email.removesuffix(DEMO_DOMAIN): user for user in users}


def _create_organization(org: Org, accounts: dict[str, User]) -> Organization:
    organization = create_organization(
        user=accounts[org.owner], name=org.name, description=org.description
    )
    for key, role in org.members:
        add_member(organization=organization, email=accounts[key].email, role=role)
    return organization


def _start_of(spec: DemoEvent, now: datetime) -> datetime:
    if spec.from_now is not None:
        return now + spec.from_now
    day = now.astimezone(MADRID) + timedelta(days=spec.day)
    return day.replace(hour=spec.hour, minute=0, second=0, microsecond=0)


def _between(rng: random.Random, start: datetime, end: datetime) -> datetime:
    return start + (end - start) * rng.random()


def _create_event(
    spec: DemoEvent,
    organization: Organization,
    lucia: User,
    public: list[User],
    rng: random.Random,
    now: datetime,
) -> None:
    start = _start_of(spec, now)
    created = min(now, start) - timedelta(days=21)
    owner = organization.memberships.get(role=Membership.Role.OWNER).user

    event = create_event(
        organization=organization,
        user=owner,
        title=spec.title,
        location=spec.location,
        description=spec.description,
        start_at=start,
        end_at=start + timedelta(hours=spec.hours),
        capacity=sum(c.capacity for c in spec.categories) or DEFAULT_CAPACITY,
    )
    Event.objects.filter(pk=event.pk).update(created_at=created)
    categories = [
        (
            create_ticket_type(
                event=event,
                name=c.name,
                capacity=c.capacity,
                description=c.description,
                now=created,
            ),
            c.fill,
        )
        for c in spec.categories
    ]
    if spec.image:
        with (IMAGES / f"{spec.image}.webp").open("rb") as image:
            set_event_image(event=event, upload=File(image, name=image.name), now=created)
    if spec.kind == Kind.DRAFT:
        return

    published = created + timedelta(days=1)
    publish_event(event=event, now=published)
    event.refresh_from_db()
    for membership in organization.memberships.filter(role=Membership.Role.STAFF):
        assign_staff(event=event, user_id=membership.user_id)

    # Booking stops before anything that ends it: the cancellation, or the attendees' deadline.
    cancelled_at = now - timedelta(days=1)
    closing = cancelled_at - timedelta(days=1) if spec.kind == Kind.CANCELLED else None
    closing = closing or min(now, start) - timedelta(hours=3)

    booked = _book(spec, categories, public, lucia, rng, published, closing)
    _backdate(booked)
    _cancel_some(spec, event, booked, owner, lucia, rng, closing)

    if spec.kind == Kind.CANCELLED:
        cancel_event(event=event, by=owner, now=cancelled_at)
    elif spec.show:
        _scan_door(spec, event, booked, organization, lucia, rng, now)


def _book(
    spec: DemoEvent,
    categories: list[tuple[TicketType, float]],
    public: list[User],
    lucia: User,
    rng: random.Random,
    opened: datetime,
    closing: datetime,
) -> dict[Reservation, datetime]:
    """Each category's share of bookings, each by a different person, at a random past time."""
    wanted = sum(round(ticket_type.capacity * fill) for ticket_type, fill in categories)
    crowd = rng.sample(public, min(wanted, len(public)))
    if spec.lucia:
        crowd.insert(0, lucia)
    booked: dict[Reservation, datetime] = {}
    for ticket_type, fill in categories:
        for _ in range(round(ticket_type.capacity * fill)):
            if not crowd:
                return booked
            when = _between(rng, opened, closing)
            booked[reserve(user=crowd.pop(0), ticket_type_id=ticket_type.pk, now=when)] = when
    return booked


def _backdate(booked: dict[Reservation, datetime]) -> None:
    """`auto_now_add` stamped today; these rows really belong to the moment they simulate."""
    reservations, tickets = [], []
    for reservation, when in booked.items():
        reservation.created_at = when
        reservation.ticket.issued_at = when
        reservations.append(reservation)
        tickets.append(reservation.ticket)
    Reservation.objects.bulk_update(reservations, ["created_at"])
    Ticket.objects.bulk_update(tickets, ["issued_at"])


def _cancel_some(
    spec: DemoEvent,
    event: Event,
    booked: dict[Reservation, datetime],
    owner: User,
    lucia: User,
    rng: random.Random,
    closing: datetime,
) -> None:
    """A few people change their mind; every tenth is cancelled by the organizer instead.
    Sold-out categories stay sold out: giving a seat back would hide that state from the demo."""
    full = {c.name for c in spec.categories if c.fill == 1.0}
    deadline = min(cancellation_deadline(event), closing + timedelta(hours=1))
    candidates = [r for r in booked if r.ticket_type.name not in full and r.user_id != lucia.pk]
    for n, reservation in enumerate(rng.sample(candidates, int(len(candidates) * CANCELLED_SHARE))):
        by_organizer = n % 10 == 9
        cancel_reservation(
            reservation=reservation,
            cancelled_by=owner if by_organizer else reservation.user,
            as_organizer=by_organizer,
            now=_between(rng, booked[reservation], deadline),
        )
        del booked[reservation]
    if spec.lucia == Lucia.CANCELS:
        mine = next(r for r in booked if r.user_id == lucia.pk)
        cancel_reservation(reservation=mine, cancelled_by=lucia, now=deadline)
        del booked[mine]


def _scan_door(
    spec: DemoEvent,
    event: Event,
    booked: dict[Reservation, datetime],
    organization: Organization,
    lucia: User,
    rng: random.Random,
    now: datetime,
) -> None:
    """People arrive around the start. Then the mistakes every door sees, one of each kind,
    so the activity feed and the stats have something other than green ticks."""
    door = (
        organization.memberships.filter(role=Membership.Role.STAFF).first()
        or organization.memberships.get(role=Membership.Role.OWNER)
    ).user
    opens = checkin_opens_at(event)
    until = min(now, event.start_at + timedelta(hours=1))
    earliest = max(opens, until - timedelta(hours=2))

    tokens = [r.ticket.token for r in booked if r.user_id != lucia.pk and rng.random() < spec.show]
    if spec.lucia == Lucia.ATTENDS:
        tokens.append(next(r for r in booked if r.user_id == lucia.pk).ticket.token)
    for token in tokens:
        scan(event=event, token=token, staff=door, now=_between(rng, earliest, until))

    def mistake(token: str, staff: User = door, at: datetime | None = None) -> None:
        scan(event=event, token=token, staff=staff, now=at or _between(rng, earliest, until))

    mistake("codigo-que-no-existe")
    if tokens:
        mistake(tokens[0])  # the same ticket, a second time
    mistake("demasiado-pronto", at=opens - timedelta(minutes=20))
    mistake("sin-permiso", staff=lucia)
    cancelled = Ticket.objects.filter(
        reservation__event=event, status=Ticket.Status.CANCELLED
    ).first()
    if cancelled:
        mistake(cancelled.token)
    elsewhere = Ticket.objects.exclude(reservation__event=event).first()
    if elsewhere:
        mistake(elsewhere.token)
