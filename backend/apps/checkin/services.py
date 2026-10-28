"""Ticket validation at the door (requirements.md §3.8, ADR-0004).

The ticket goes from VALID to USED with one conditional UPDATE:

    UPDATE ticketing_ticket SET status = 'USED', ... WHERE id = %s AND status = 'VALID'

When two phones scan the same ticket at once, PostgreSQL makes the second UPDATE wait for
the first, then re-checks `status = 'VALID'` on the new row version: it no longer matches,
0 rows change, and the second scan reads ALREADY_USED.

Why not one `Ticket.objects.filter(token=..., status=VALID, reservation__event=...).update()`?
The join makes Django write `UPDATE ... WHERE id IN (SELECT ...)`, and on that re-check
PostgreSQL does *not* re-run the subquery (EvalPlanQual only re-evaluates the target row's
own conditions), so both scans could "win". The ticket is therefore looked up first and the
UPDATE filters only on its own columns. test_concurrency guards this.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.checkin.models import CheckInLog
from apps.events.models import Event, EventStaff
from apps.organizations.models import Membership
from apps.ticketing.models import Ticket

Result = CheckInLog.Result


@dataclass(frozen=True)
class ScanOutcome:
    result: str
    ticket: Ticket | None
    log: CheckInLog


def can_validate(user: User, event: Event) -> bool:
    """RN-28: the event's assigned staff, and its organization's OWNERs and MANAGERs."""
    is_organizer = Membership.objects.filter(
        user=user,
        organization_id=event.organization_id,
        role__in=[Membership.Role.OWNER, Membership.Role.MANAGER],
    ).exists()
    return is_organizer or EventStaff.objects.filter(event=event, user=user).exists()


def checkin_opens_at(event: Event) -> datetime:
    """RN-29: the door opens this long before the start, and closes when the event ends."""
    return event.start_at - timedelta(hours=settings.CHECKIN_OPENS_HOURS_BEFORE)


def is_checkin_open(event: Event, now: datetime) -> bool:
    return event.status == Event.Status.PUBLISHED and checkin_opens_at(event) <= now <= event.end_at


@transaction.atomic
def scan(*, event: Event, token: str, staff: User, now: datetime | None = None) -> ScanOutcome:
    """Validate one scanned token at `event`. Every attempt is logged (RN-31)."""
    now = now or timezone.now()

    def outcome(result: str, ticket: Ticket | None = None) -> ScanOutcome:
        log = CheckInLog.objects.create(
            event=event, ticket=ticket, staff=staff, result=result, checked_at=now
        )
        return ScanOutcome(result=result, ticket=ticket, log=log)

    if not can_validate(staff, event):
        return outcome(Result.UNAUTHORIZED)
    if not is_checkin_open(event, now):
        return outcome(Result.EVENT_NOT_ACTIVE)

    ticket = Ticket.objects.select_related("reservation").filter(token=token).first()
    if ticket is None:
        return outcome(Result.NOT_FOUND)
    if ticket.reservation.event_id != event.pk:
        return outcome(Result.WRONG_EVENT)

    # The validation itself: one conditional UPDATE on the ticket's own columns.
    validated = Ticket.objects.filter(pk=ticket.pk, status=Ticket.Status.VALID).update(
        status=Ticket.Status.USED, checked_in_at=now, checked_in_by=staff
    )
    ticket.refresh_from_db()
    if validated:
        return outcome(Result.VALID, ticket)
    if ticket.status == Ticket.Status.USED:
        return outcome(Result.ALREADY_USED, ticket)
    return outcome(Result.CANCELLED, ticket)
