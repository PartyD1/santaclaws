"""Handle inbound Vapi call webhooks for the Closer claw."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from agents.shared.logger import logger
from agents.shared.supabase_client import get_client


PHONE_RE = re.compile(r"\D+")
END_OF_CALL_TYPES = {"end-of-call-report", "call-ended", "ended"}
TRANSCRIPT_TYPES = {"transcript", "conversation-update"}
STATUS_TYPES = {"status-update", "call-started", "call-start"}


def _now_iso() -> str:
    """Return a UTC timestamp for Supabase writes."""

    return datetime.now(timezone.utc).isoformat()


def _safe_log(action_type: str, status: str, message: str, result: dict[str, Any], lead_id: str | None = None) -> None:
    """Best-effort action logging."""

    try:
        logger.log("closer", action_type, status, message, lead_id=lead_id, result=result)
    except Exception as exc:  # pragma: no cover - local/no-credential path.
        print(f"Vapi call log skipped: {exc}")


def _message(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the Vapi message object from a webhook payload."""

    message = payload.get("message")
    return message if isinstance(message, dict) else payload


def _event_type(payload: dict[str, Any]) -> str:
    """Return the normalized Vapi webhook event type."""

    message = _message(payload)
    return str(message.get("type") or payload.get("type") or "").strip().lower()


def _call(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the call object from a Vapi webhook payload."""

    message = _message(payload)
    call = message.get("call") or payload.get("call")
    return call if isinstance(call, dict) else {}


def _customer(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the customer/caller object from a Vapi webhook payload."""

    call = _call(payload)
    customer = call.get("customer") or _message(payload).get("customer") or payload.get("customer")
    return customer if isinstance(customer, dict) else {}


def _call_id(payload: dict[str, Any]) -> str | None:
    """Return the Vapi call id if present."""

    call = _call(payload)
    value = call.get("id") or _message(payload).get("callId") or payload.get("callId")
    return None if value is None else str(value)


def _caller_phone(payload: dict[str, Any]) -> str | None:
    """Return the caller phone number when present."""

    customer = _customer(payload)
    value = customer.get("number") or customer.get("phoneNumber") or _message(payload).get("phoneNumber")
    return None if value is None else str(value)


def _normalize_phone(value: str | None) -> str:
    """Normalize a phone number to digits for local matching."""

    return PHONE_RE.sub("", value or "")


def _find_lead_id(caller_phone: str | None) -> str | None:
    """Best-effort lead lookup by caller phone."""

    normalized = _normalize_phone(caller_phone)
    if not normalized:
        return None
    response = get_client().table("leads").select("id, phone").limit(500).execute()
    rows = getattr(response, "data", []) or []
    for row in rows:
        if isinstance(row, dict) and _normalize_phone(row.get("phone")).endswith(normalized[-10:]):
            return str(row["id"])
    return None


def _transcript_from_messages(messages: Any) -> str:
    """Build a transcript from Vapi message arrays."""

    if not isinstance(messages, list):
        return ""
    lines = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or item.get("speaker") or "speaker").strip()
        content = str(item.get("message") or item.get("content") or item.get("text") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def transcript_text(payload: dict[str, Any]) -> str:
    """Extract the most useful transcript text from a Vapi webhook payload."""

    message = _message(payload)
    candidates = [
        message.get("transcript"),
        message.get("artifact", {}).get("transcript") if isinstance(message.get("artifact"), dict) else None,
        payload.get("transcript"),
        payload.get("summary"),
    ]
    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value.strip()
    built = _transcript_from_messages(message.get("messages") or payload.get("messages"))
    if built:
        return built
    return json.dumps(payload, ensure_ascii=True, default=str)[:4000]


def insert_voice_inbound(payload: dict[str, Any]) -> dict[str, Any]:
    """Insert one voice inbound row from a completed Vapi call."""

    caller = _caller_phone(payload)
    lead_id = _find_lead_id(caller)
    transcript = transcript_text(payload)
    call_id = _call_id(payload)
    raw_content = f"Vapi voice call transcript{f' ({call_id})' if call_id else ''}:\n{transcript}"
    insert_payload: dict[str, Any] = {
        "channel": "voice",
        "from_address": caller,
        "raw_content": raw_content,
        "transcript": transcript,
        "received_at": _now_iso(),
    }
    if lead_id:
        insert_payload["lead_id"] = lead_id

    response = get_client().table("inbound").insert(insert_payload).execute()
    rows = getattr(response, "data", []) or []
    if not rows:
        raise RuntimeError("Vapi inbound insert did not return a row.")
    inbound = rows[0]
    result = {"inbound_id": str(inbound["id"]), "lead_id": lead_id, "call_id": call_id, "caller": caller}
    _safe_log("vapi_call", "succeeded", "saved Vapi voice transcript to inbound.", result, lead_id)
    return result


def run(payload: dict[str, Any]) -> dict[str, Any]:
    """Handle one Vapi webhook payload."""

    event_type = _event_type(payload)
    call_id = _call_id(payload)
    if event_type in END_OF_CALL_TYPES:
        return {"status": "inserted", "event_type": event_type, **insert_voice_inbound(payload)}
    if event_type in TRANSCRIPT_TYPES:
        result = {"status": "acknowledged", "event_type": event_type, "call_id": call_id}
        _safe_log("vapi_transcript", "skipped", "acknowledged live Vapi transcript event.", result)
        return result
    if event_type in STATUS_TYPES:
        result = {"status": "acknowledged", "event_type": event_type, "call_id": call_id}
        _safe_log("vapi_status", "skipped", f"acknowledged Vapi status event {event_type}.", result)
        return result

    result = {"status": "ignored", "event_type": event_type or "unknown", "call_id": call_id}
    _safe_log("vapi_webhook", "skipped", f"ignored Vapi webhook event {result['event_type']}.", result)
    return result
