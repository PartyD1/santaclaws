"""Google Calendar helper with demo-safe fallbacks for Closer."""

from __future__ import annotations

import os
from datetime import datetime, time, timedelta, timezone
from typing import Any, Iterable
from zoneinfo import ZoneInfo

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency validation catches this.
    load_dotenv = None  # type: ignore[assignment]


DEFAULT_TZ = "America/Los_Angeles"
DEFAULT_CALENDAR_ID = "primary"


class GoogleCalendarError(RuntimeError):
    """Base exception for Google Calendar failures."""


class GoogleCalendarConfigError(GoogleCalendarError):
    """Raised when live Google Calendar credentials are missing."""


def _load_env() -> None:
    """Load `.env` if python-dotenv is available."""

    if load_dotenv is not None:
        load_dotenv()


def _env(name: str) -> str:
    """Return a stripped environment variable."""

    _load_env()
    return os.environ.get(name, "").strip()


def _has_google_config() -> bool:
    """Return whether OAuth values are present."""

    return all(_env(name) for name in ("GCAL_CLIENT_ID", "GCAL_CLIENT_SECRET", "GCAL_REFRESH_TOKEN"))


def _tz(name: str) -> ZoneInfo | timezone:
    """Return a timezone, falling back to Pacific time."""

    try:
        return ZoneInfo(name)
    except Exception:
        return timezone(timedelta(hours=-7), "Pacific")


def _demo_slots(
    duration_minutes: int = 30,
    days_ahead: int = 7,
    hours_range: tuple[int, int] = (9, 17),
    tz: str = DEFAULT_TZ,
) -> list[datetime]:
    """Return deterministic near-future demo slots during business hours."""

    zone = _tz(tz)
    now = datetime.now(zone)
    start_hour, _end_hour = hours_range
    slots: list[datetime] = []
    day = now.date() + timedelta(days=1)
    while len(slots) < 3 and (day - now.date()).days <= max(days_ahead, 1):
        if day.weekday() < 5:
            for hour in (start_hour, start_hour + 2, start_hour + 4):
                candidate = datetime.combine(day, time(hour=hour), zone)
                if candidate > now + timedelta(hours=1):
                    slots.append(candidate)
                    if len(slots) == 3:
                        break
        day += timedelta(days=1)
    if not slots:
        slots.append(now + timedelta(days=1, hours=1))
    return slots[:3]


def get_credentials() -> Any:
    """Build Google OAuth credentials from env.

    Raises:
        GoogleCalendarConfigError: If credentials or google-auth are missing.
    """

    if not _has_google_config():
        raise GoogleCalendarConfigError(
            "GCAL_CLIENT_ID, GCAL_CLIENT_SECRET, and GCAL_REFRESH_TOKEN are required for live Google Calendar."
        )

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError as exc:  # pragma: no cover - local setup issue.
        raise GoogleCalendarConfigError(
            "Google Calendar packages are not installed. Run `pip install -r agents/requirements.txt`."
        ) from exc

    credentials = Credentials(
        token=None,
        refresh_token=_env("GCAL_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=_env("GCAL_CLIENT_ID"),
        client_secret=_env("GCAL_CLIENT_SECRET"),
        scopes=["https://www.googleapis.com/auth/calendar"],
    )
    credentials.refresh(Request())
    return credentials


def _service() -> Any:
    """Return a Google Calendar service object."""

    try:
        from googleapiclient.discovery import build
    except ImportError as exc:  # pragma: no cover - local setup issue.
        raise GoogleCalendarConfigError(
            "google-api-python-client is not installed. Run `pip install -r agents/requirements.txt`."
        ) from exc
    return build("calendar", "v3", credentials=get_credentials(), cache_discovery=False)


def _overlaps_busy(start: datetime, end: datetime, busy_ranges: Iterable[dict[str, str]]) -> bool:
    """Return whether a candidate overlaps any busy block."""

    for item in busy_ranges:
        busy_start = datetime.fromisoformat(item["start"].replace("Z", "+00:00"))
        busy_end = datetime.fromisoformat(item["end"].replace("Z", "+00:00"))
        if start < busy_end and end > busy_start:
            return True
    return False


def get_free_slots(
    duration_minutes: int = 30,
    days_ahead: int = 7,
    hours_range: tuple[int, int] = (9, 17),
    tz: str = DEFAULT_TZ,
) -> list[datetime]:
    """Return 3 free slots from Google Calendar or demo-safe fake slots."""

    if not _has_google_config():
        return _demo_slots(duration_minutes, days_ahead, hours_range, tz)

    zone = _tz(tz)
    now = datetime.now(zone)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days_ahead)).isoformat()
    try:
        service = _service()
        calendar_id = _env("GCAL_CALENDAR_ID") or DEFAULT_CALENDAR_ID
        freebusy = (
            service.freebusy()
            .query(
                body={
                    "timeMin": time_min,
                    "timeMax": time_max,
                    "timeZone": tz,
                    "items": [{"id": calendar_id}],
                }
            )
            .execute()
        )
        busy = freebusy.get("calendars", {}).get(calendar_id, {}).get("busy", [])
    except Exception:
        return _demo_slots(duration_minutes, days_ahead, hours_range, tz)

    start_hour, end_hour = hours_range
    slots: list[datetime] = []
    day = now.date()
    while len(slots) < 3 and (day - now.date()).days <= max(days_ahead, 1):
        if day.weekday() < 5:
            candidate = datetime.combine(day, time(hour=start_hour), zone)
            while candidate.hour < end_hour and len(slots) < 3:
                end = candidate + timedelta(minutes=duration_minutes)
                if candidate > now + timedelta(hours=1) and not _overlaps_busy(candidate, end, busy):
                    slots.append(candidate)
                candidate += timedelta(minutes=60)
        day += timedelta(days=1)
    return slots or _demo_slots(duration_minutes, days_ahead, hours_range, tz)


def create_event(
    title: str,
    description: str,
    start: datetime,
    duration_minutes: int = 30,
    attendee_email: str | None = None,
) -> str:
    """Create a Google Calendar event, or return a deterministic demo id."""

    if not _has_google_config():
        return f"demo-gcal-{int(start.timestamp())}"

    zone_name = start.tzinfo.key if hasattr(start.tzinfo, "key") else DEFAULT_TZ
    event: dict[str, Any] = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start.isoformat(), "timeZone": zone_name},
        "end": {"dateTime": (start + timedelta(minutes=duration_minutes)).isoformat(), "timeZone": zone_name},
    }
    if attendee_email:
        event["attendees"] = [{"email": attendee_email}]

    try:
        calendar_id = _env("GCAL_CALENDAR_ID") or DEFAULT_CALENDAR_ID
        created = _service().events().insert(calendarId=calendar_id, body=event).execute()
        event_id = created.get("id")
        if not event_id:
            raise GoogleCalendarError("Google Calendar response did not include event id.")
        return str(event_id)
    except Exception:
        return f"demo-gcal-{int(start.timestamp())}"
