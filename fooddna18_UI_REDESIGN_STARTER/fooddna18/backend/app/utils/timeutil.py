"""
FoodDNA — Timezone-safe datetime helpers (fix for issue 1.1).

Problem: backend stored naive UTC datetimes and serialised them with
isoformat() which does NOT append a timezone indicator.  Browsers
receiving "2026-10-16T10:30:00" treat it as local time, so an IST
user sees 5h30m off.  The fix: always append "Z" so the string is
unambiguously UTC.

Rules:
- Store naive UTC in MySQL (unchanged — avoids migration-level
  column-type change).
- utcnow() replacement uses timezone.utc then strips tzinfo so
  SQLAlchemy keeps storing a naive datetime column value.
- iso_utc(dt) appends "Z"; returns None for None inputs.
"""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """
    Drop-in replacement for the deprecated datetime.utcnow().
    Returns a *naive* datetime representing the current UTC instant.
    Using datetime.now(timezone.utc) is recommended by Python docs
    to avoid the deprecated API; we then strip tzinfo so SQLAlchemy
    columns typed DATETIME (without timezone) receive a naive value.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso_utc(dt: datetime | None) -> str | None:
    """
    Serialise a naive UTC datetime to an ISO-8601 string with a
    trailing 'Z' so all clients parse it correctly as UTC.

    Returns None when dt is None (safe for optional columns).
    """
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
