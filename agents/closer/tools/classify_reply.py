"""Closer tool for classifying inbound email replies."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from agents.shared import nemotron_client
from agents.shared.logger import logger
from agents.shared.supabase_client import get_client


PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "closer_classify.txt"
VALID_CLASSIFICATIONS = {"interested", "not_interested", "has_question", "has_objection", "spam", "uncertain"}


def _safe_log(action_type: str, status: str, message: str, lead_id: str | None, result: dict[str, Any]) -> None:
    """Best-effort action logging."""

    try:
        logger.log("closer", action_type, status, message, lead_id=lead_id, result=result)
    except Exception as exc:  # pragma: no cover - local/no-credential path.
        print(f"Closer log skipped: {exc}")


def _first_row(response: Any) -> dict[str, Any] | None:
    """Return the first row from a Supabase response."""

    rows = getattr(response, "data", None)
    if isinstance(rows, list):
        return rows[0] if rows else None
    if isinstance(rows, dict):
        return rows
    return None


def _fetch_row(table: str, row_id: UUID | str) -> dict[str, Any] | None:
    """Fetch a row by id."""

    return _first_row(get_client().table(table).select("*").eq("id", str(row_id)).limit(1).execute())


def _fetch_latest_outreach(lead_id: str | None) -> dict[str, Any] | None:
    """Fetch the latest outreach row for context."""

    if not lead_id:
        return None
    response = (
        get_client()
        .table("outreach")
        .select("*")
        .eq("lead_id", lead_id)
        .order("drafted_at", desc=True)
        .limit(1)
        .execute()
    )
    return _first_row(response)


def _prompt(inbound: dict[str, Any], lead: dict[str, Any] | None, outreach: dict[str, Any] | None) -> str:
    """Build the classification prompt."""

    reply_text = inbound.get("raw_content") or ""
    prompt = PROMPT_PATH.read_text(encoding="utf-8").format(
        reply_text=reply_text,
        business_name=(lead or {}).get("business_name") or "unknown",
        from_address=inbound.get("from_address") or (lead or {}).get("email") or "unknown",
        outreach_subject=(outreach or {}).get("subject") or "unknown",
    )
    return prompt


def _keyword_fallback(text: str, reason: str) -> dict[str, Any]:
    """Classify with simple keywords when Nemotron is unavailable."""

    lowered = text.lower()
    if any(term in lowered for term in ("unsubscribe", "stop emailing", "not interested", "no thanks")):
        classification, confidence, phrase = "not_interested", 88, "declined or opted out"
    elif any(term in lowered for term in ("when", "schedule", "call", "chat", "meet", "interested", "sounds good")):
        classification, confidence, phrase = "interested", 82, "asked to talk or schedule"
    elif "?" in text or any(term in lowered for term in ("how much", "what does", "who", "where")):
        classification, confidence, phrase = "has_question", 76, "asked a question"
    elif any(term in lowered for term in ("too expensive", "already have", "busy", "later", "not now")):
        classification, confidence, phrase = "has_objection", 72, "raised an objection"
    elif any(term in lowered for term in ("viagra", "crypto", "winner", "prize")):
        classification, confidence, phrase = "spam", 90, "spam-like content"
    else:
        classification, confidence, phrase = "uncertain", 45, "not enough signal"
    return {
        "classification": classification,
        "confidence": confidence,
        "key_phrase": phrase,
        "fallback": True,
        "fallback_reason": reason,
    }


def fallback_classification(text: str, reason: str) -> dict[str, Any]:
    """Return deterministic classification when the live classifier cannot run."""

    return _keyword_fallback(text, reason)


def _normalize(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize Nemotron classification output."""

    classification = str(payload.get("classification") or "uncertain").strip()
    if classification not in VALID_CLASSIFICATIONS:
        classification = "uncertain"
    try:
        confidence = int(payload.get("confidence") or 0)
    except (TypeError, ValueError):
        confidence = 0
    return {
        "classification": classification,
        "confidence": max(0, min(100, confidence)),
        "key_phrase": str(payload.get("key_phrase") or "").strip()[:200],
    }


def run(inbound_id: UUID | str) -> dict[str, Any]:
    """Classify one inbound email reply and update the inbound row."""

    try:
        inbound = _fetch_row("inbound", inbound_id)
        if not inbound:
            return {"error": f"inbound row not found: {inbound_id}", "_status": "skipped"}
        if inbound.get("channel") != "email":
            result = {"error": "only email inbound rows are supported.", "_status": "skipped"}
            _safe_log("classify_reply", "skipped", "skipped unsupported inbound channel.", None, result)
            return result

        lead_id = None if inbound.get("lead_id") is None else str(inbound.get("lead_id"))
        lead = _fetch_row("leads", lead_id) if lead_id else None
        outreach = _fetch_latest_outreach(lead_id)
        reply_text = str(inbound.get("raw_content") or "")

        try:
            payload = nemotron_client.chat_json(
                system="You are Closer, a NemoClaw claw classifying inbound email replies. Return JSON only.",
                user=_prompt(inbound, lead, outreach),
                retries=1,
            )
            result = _normalize(payload)
        except Exception as exc:
            result = _keyword_fallback(reply_text, str(exc))

        get_client().table("inbound").update(
            {
                "classification": result["classification"],
                "classification_confidence": result["confidence"],
                "classification_key_phrase": result["key_phrase"],
            }
        ).eq("id", str(inbound_id)).is_("handled_at", "null").execute()
        _safe_log(
            "classify_reply",
            "succeeded",
            f"classified inbound email as {result['classification']} ({result['confidence']}%).",
            lead_id,
            result,
        )
        return result
    except Exception as exc:
        result = {"error": str(exc), "_status": "failed"}
        _safe_log("classify_reply", "failed", f"could not classify inbound reply: {exc}", None, result)
        return result
