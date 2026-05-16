"""Closer tool for drafting concise email replies."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from agents.shared import nemotron_client
from agents.shared.logger import logger
from agents.shared.supabase_client import get_client


VALID_BRANCHES = {"interested", "has_question", "has_objection", "not_interested", "spam", "uncertain"}


def _safe_log(action_type: str, status: str, message: str, lead_id: str | None, result: dict[str, Any]) -> None:
    """Best-effort action logging."""

    try:
        logger.log("closer", action_type, status, message, lead_id=lead_id, result=result)
    except Exception as exc:  # pragma: no cover - local/no-credential path.
        print(f"Closer log skipped: {exc}")


def _first_row(response: Any) -> dict[str, Any] | None:
    """Return the first Supabase row."""

    rows = getattr(response, "data", None)
    if isinstance(rows, list):
        return rows[0] if rows else None
    if isinstance(rows, dict):
        return rows
    return None


def _fetch_row(table: str, row_id: UUID | str) -> dict[str, Any] | None:
    """Fetch a row by id."""

    return _first_row(get_client().table(table).select("*").eq("id", str(row_id)).limit(1).execute())


def _prompt(
    inbound: dict[str, Any],
    lead: dict[str, Any] | None,
    branch: str,
    meeting_times: list[str] | None,
) -> str:
    """Build a concise reply prompt."""

    return (
        "Draft a concise email reply from Mainstreet to a local business owner.\n"
        "Return JSON only: {\"subject\": \"...\", \"body\": \"...\"}.\n"
        "Rules: 5 sentences or fewer, no invented business facts, no aggressive sales language.\n\n"
        f"Classification: {branch}\n"
        f"Business name: {(lead or {}).get('business_name') or 'unknown'}\n"
        f"Lead city: {(lead or {}).get('city') or 'unknown'}\n"
        f"Inbound reply: {inbound.get('raw_content') or inbound.get('transcript') or ''}\n"
        f"Meeting options: {', '.join(meeting_times or []) or 'none provided'}\n"
    )


def _normalize(payload: dict[str, Any]) -> dict[str, str]:
    """Validate and normalize Nemotron reply JSON."""

    subject = str(payload.get("subject") or "").strip()[:80]
    body = str(payload.get("body") or "").strip()
    if not subject:
        raise ValueError("subject is required.")
    if not body:
        raise ValueError("body is required.")
    return {"subject": subject, "body": body}


def _fallback_reply(branch: str, lead: dict[str, Any] | None, meeting_times: list[str] | None, reason: str) -> dict[str, Any]:
    """Return a safe local draft when Nemotron is unavailable."""

    business_name = (lead or {}).get("business_name") or "there"
    if branch == "interested":
        options = ", ".join(meeting_times or []) or "a couple of times this week"
        body = f"Thanks for getting back to me. Happy to talk through the mockup; would {options} work for a quick call?"
    elif branch == "has_question":
        body = "Thanks for the question. I can keep this simple: the mockup is a quick starting point, and I am happy to walk through what would change for your business."
    elif branch == "has_objection":
        body = "That makes sense. No pressure; the mockup is just meant to show what a clearer local site could look like before you spend time on a full conversation."
    elif branch == "not_interested":
        body = "Thanks for letting me know. I will close the loop here and will not follow up further."
    else:
        body = "Thanks for the reply. I will take a closer look and follow up only if it is useful."
    return {
        "subject": f"Re: {business_name}",
        "body": body,
        "fallback": True,
        "fallback_reason": reason,
    }


def run(inbound_id: UUID | str, branch: str, meeting_times: list[str] | None = None) -> dict[str, Any]:
    """Draft a concise email response for one inbound reply."""

    if branch not in VALID_BRANCHES:
        return {"error": f"unknown reply branch: {branch}", "_status": "skipped"}

    try:
        inbound = _fetch_row("inbound", inbound_id)
        if not inbound:
            return {"error": f"inbound row not found: {inbound_id}", "_status": "skipped"}
        lead_id = None if inbound.get("lead_id") is None else str(inbound.get("lead_id"))
        lead = _fetch_row("leads", lead_id) if lead_id else None

        try:
            payload = nemotron_client.chat_json(
                system="You are Closer, a NemoClaw claw drafting concise email replies. Return JSON only.",
                user=_prompt(inbound, lead, branch, meeting_times),
                retries=1,
            )
            result: dict[str, Any] = _normalize(payload)
        except (nemotron_client.NemotronClientError, ValueError) as exc:
            result = _fallback_reply(branch, lead, meeting_times, str(exc))

        _safe_log("draft_reply", "succeeded", f"drafted {branch} reply.", lead_id, result)
        return result
    except Exception as exc:
        result = {"error": str(exc), "_status": "failed"}
        _safe_log("draft_reply", "failed", f"could not draft reply: {exc}", None, result)
        return result
