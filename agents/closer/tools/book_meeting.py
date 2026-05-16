"""Closer tool for booking a meeting and recording it in Supabase."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from agents.integrations import gcal_client
from agents.shared.logger import logger
from agents.shared.supabase_client import get_client


def _safe_log(action_type: str, status: str, message: str, lead_id: str | None, result: dict[str, Any]) -> None:
    """Best-effort action logging."""

    try:
        logger.log("closer", action_type, status, message, lead_id=lead_id, result=result)
    except Exception as exc:  # pragma: no cover - local/no-credential path.
        print(f"Closer log skipped: {exc}")


def _parse_slot(chosen_slot: datetime | str) -> datetime:
    """Parse a chosen slot from datetime or ISO string."""

    if isinstance(chosen_slot, datetime):
        return chosen_slot
    return datetime.fromisoformat(str(chosen_slot).replace("Z", "+00:00"))


def _first_row(response: Any) -> dict[str, Any] | None:
    """Return the first Supabase row."""

    rows = getattr(response, "data", None)
    if isinstance(rows, list):
        return rows[0] if rows else None
    if isinstance(rows, dict):
        return rows
    return None


def run(
    lead_id: UUID | str,
    chosen_slot: datetime | str,
    attendee_email: str,
    inbound_id: UUID | str | None = None,
    duration_minutes: int = 30,
) -> dict[str, Any]:
    """Book a calendar meeting and insert a row into `meetings`."""

    lead_id_str = str(lead_id)
    try:
        start = _parse_slot(chosen_slot)
        if not attendee_email or "@" not in attendee_email:
            raise ValueError("attendee_email is required to book a meeting.")

        event_id = gcal_client.create_event(
            title="Mainstreet follow-up",
            description="Meeting booked by the Mainstreet Closer NemoClaw.",
            start=start,
            duration_minutes=duration_minutes,
            attendee_email=attendee_email,
        )
        payload: dict[str, Any] = {
            "lead_id": lead_id_str,
            "scheduled_for": start.isoformat(),
            "google_event_id": event_id,
            "status": "booked",
            "attendee_email": attendee_email,
        }
        if inbound_id is not None:
            payload["inbound_id"] = str(inbound_id)

        row = _first_row(get_client().table("meetings").insert(payload).execute())
        result = {
            "booked": True,
            "event_id": event_id,
            "meeting_id": None if not row else row.get("id"),
            "scheduled_for": start.isoformat(),
            "attendee_email": attendee_email,
            "provider": "demo" if event_id.startswith("demo-gcal-") else "google_calendar",
        }
        _safe_log("book_meeting", "succeeded", f"booked meeting for {attendee_email}.", lead_id_str, result)
        return result
    except Exception as exc:
        result = {"booked": False, "_status": "failed", "error": str(exc)}
        _safe_log("book_meeting", "failed", f"could not book meeting: {exc}", lead_id_str, result)
        return result
