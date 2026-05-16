"""Closer tool for proposing meeting times."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from agents.integrations import gcal_client
from agents.shared.logger import logger


def _safe_log(action_type: str, status: str, message: str, result: dict[str, Any]) -> None:
    """Best-effort action logging."""

    try:
        logger.log("closer", action_type, status, message, result=result)
    except Exception as exc:  # pragma: no cover - local/no-credential path.
        print(f"Closer log skipped: {exc}")


def _format_slot(slot: datetime) -> str:
    """Format a meeting slot for an email reply."""

    return slot.strftime("%A %-I:%M%p %Z").replace("AM", "am").replace("PM", "pm")


def _safe_format_slot(slot: datetime) -> str:
    """Windows-safe slot formatting."""

    try:
        return _format_slot(slot)
    except ValueError:
        return slot.strftime("%A %#I:%M%p %Z").replace("AM", "am").replace("PM", "pm")


def run(
    duration_minutes: int = 30,
    days_ahead: int = 7,
    hours_range: tuple[int, int] = (9, 17),
    tz: str = gcal_client.DEFAULT_TZ,
) -> dict[str, Any]:
    """Return 3 proposed meeting slots for a Closer reply."""

    try:
        slots = gcal_client.get_free_slots(duration_minutes, days_ahead, hours_range, tz)
        formatted = [_safe_format_slot(slot) for slot in slots[:3]]
        result = {
            "slots": [slot.isoformat() for slot in slots[:3]],
            "formatted_slots": formatted,
            "summary": ", ".join(formatted),
            "timezone": tz,
            "duration_minutes": duration_minutes,
        }
        _safe_log("propose_meeting_times", "succeeded", f"proposed {len(formatted)} meeting times.", result)
        return result
    except Exception as exc:
        result = {"error": str(exc), "_status": "failed", "slots": [], "formatted_slots": []}
        _safe_log("propose_meeting_times", "failed", f"could not propose meeting times: {exc}", result)
        return result
