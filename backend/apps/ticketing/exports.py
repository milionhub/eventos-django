"""The attendee list as CSV, ready to open in a spreadsheet (requirements.md R5).

Two details make it safe and readable in Excel:

- Formula injection: a name such as `=HYPERLINK("http://evil", "Clic")` would run as a
  formula when the organizer opens the file. Any cell starting with = + - @ or a tab/CR is
  prefixed with an apostrophe, which spreadsheets show as plain text (OWASP "CSV Injection").
- Excel in Spanish expects `;` as separator and needs a UTF-8 BOM to read accents.
"""

import csv
from collections.abc import Iterable, Iterator
from datetime import datetime
from zoneinfo import ZoneInfo

from apps.ticketing.models import Reservation, Ticket

FORMULA_TRIGGERS = ("=", "+", "-", "@", "\t", "\r")
DELIMITER = ";"
BOM = "﻿"

HEADER = ["Nombre", "Apellidos", "Email", "Categoría", "Estado", "Reservada", "Entrada"]


def safe_cell(value: str) -> str:
    """Neutralize a cell a spreadsheet would read as a formula."""
    return f"'{value}" if value.startswith(FORMULA_TRIGGERS) else value


def _when(moment: datetime | None, tz: ZoneInfo) -> str:
    return moment.astimezone(tz).strftime("%Y-%m-%d %H:%M") if moment else ""


def attendee_row(reservation: Reservation, tz: ZoneInfo) -> list[str]:
    user, ticket = reservation.user, reservation.ticket
    return [
        safe_cell(cell)
        for cell in [
            user.first_name,
            user.last_name,
            user.email,
            reservation.ticket_type.name,
            Ticket.Status(ticket.status).label,
            _when(reservation.created_at, tz),
            _when(ticket.checked_in_at, tz),
        ]
    ]


class _Echo:
    """csv.writer needs a file; this one hands each line straight back (no buffering)."""

    def write(self, value: str) -> str:
        return value


def attendees_csv(reservations: Iterable[Reservation], tz: ZoneInfo) -> Iterator[str]:
    """The CSV line by line, so a long list streams without building it in memory."""
    writer = csv.writer(_Echo(), delimiter=DELIMITER)
    yield BOM + writer.writerow(HEADER)
    for reservation in reservations:
        yield writer.writerow(attendee_row(reservation, tz))
