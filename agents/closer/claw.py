"""Closer claw heartbeat for Mainstreet NemoClaw."""

from __future__ import annotations

import argparse
import os
import time
from dataclasses import asdict
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency validation catches this.
    load_dotenv = None  # type: ignore[assignment]

from agents.closer.tools import classify_reply, draft_reply, propose_meeting_times
from agents.shared import discord_bridge
from agents.shared.logger import logger
from agents.shared.supabase_client import get_client, mark_inbound_handled, next_inbound, read_memory
from agents.shared.types import Inbound


def _load_env() -> None:
    """Load `.env` if python-dotenv is available."""

    if load_dotenv is not None:
        load_dotenv()


def _safe_log(
    action_type: str,
    status: str,
    message: str,
    result: dict[str, Any] | None = None,
    lead_id: str | None = None,
) -> None:
    """Best-effort action logging."""

    try:
        logger.log("closer", action_type, status, message, lead_id=lead_id, result=result)
    except Exception as exc:  # pragma: no cover - local/no-credential path.
        print(f"Closer log skipped: {exc}")


def _safe_discord(content: str) -> None:
    """Post a Closer summary when Discord is configured."""

    if not os.environ.get("DISCORD_WEBHOOK_URL", "").strip():
        print(f"Closer Discord summary:\n{content}")
        return
    try:
        discord_bridge.post(content)
    except Exception as exc:  # pragma: no cover - local/no-webhook path.
        print(f"Closer Discord summary skipped: {exc}\n{content}")


def _inbound_to_dict(inbound: Inbound) -> dict[str, Any]:
    """Convert an Inbound dataclass to dict values."""

    row = asdict(inbound)
    row["id"] = str(inbound.id)
    row["lead_id"] = None if inbound.lead_id is None else str(inbound.lead_id)
    row["received_at"] = inbound.received_at.isoformat() if inbound.received_at else None
    row["handled_at"] = inbound.handled_at.isoformat() if inbound.handled_at else None
    return row


def _lead_id(inbound: dict[str, Any]) -> str | None:
    """Return a string lead id when present."""

    value = inbound.get("lead_id")
    return None if value is None else str(value)


def _mark_handled(inbound_id: str, classification: str, summary: dict[str, Any]) -> None:
    """Mark an inbound row handled and record any failure in the summary."""

    try:
        mark_inbound_handled(inbound_id, classification, "closer")
    except Exception as exc:
        summary["errors"].append(f"mark handled failed: {exc}")
        _safe_log("mark_inbound_handled", "failed", f"could not mark inbound handled: {exc}", {"error": str(exc)})


def _set_do_not_contact(lead_id: str | None, summary: dict[str, Any]) -> None:
    """Set `do_not_contact` for clear opt-outs."""

    if not lead_id:
        return
    try:
        get_client().table("leads").update({"do_not_contact": True}).eq("id", lead_id).execute()
    except Exception as exc:
        summary["errors"].append(f"do_not_contact update failed: {exc}")
        _safe_log("do_not_contact", "failed", f"could not set do_not_contact: {exc}", {"error": str(exc)}, lead_id)


def _surface_summary(inbound: dict[str, Any], classification: str, payload: dict[str, Any]) -> None:
    """Post a concise branch summary for humans."""

    lead_id = _lead_id(inbound)
    content = (
        f"Closer classified inbound {inbound.get('id')} as {classification}."
        f"\nLead: {lead_id or 'unknown'}"
        f"\nNext step: {payload.get('next_step', 'review')}"
    )
    draft = payload.get("draft")
    if isinstance(draft, dict) and draft.get("body"):
        content += f"\nDraft: {draft.get('body')}"
    _safe_discord(content)


def _handle_interested(inbound: dict[str, Any], classification: str, summary: dict[str, Any]) -> dict[str, Any]:
    """Propose times and draft a scheduling reply."""

    slots = propose_meeting_times.run()
    draft = draft_reply.run(str(inbound["id"]), "interested", slots.get("formatted_slots", []))
    result = {"next_step": "send scheduling reply for approval", "slots": slots, "draft": draft}
    _mark_handled(str(inbound["id"]), classification, summary)
    return result


def _handle_question_or_objection(inbound: dict[str, Any], classification: str, summary: dict[str, Any]) -> dict[str, Any]:
    """Draft a reply for questions and objections."""

    draft = draft_reply.run(str(inbound["id"]), classification)
    result = {
        "next_step": "review drafted answer" if classification == "has_question" else "review drafted rebuttal",
        "draft": draft,
    }
    _mark_handled(str(inbound["id"]), classification, summary)
    return result


def _handle_terminal(inbound: dict[str, Any], classification: str, summary: dict[str, Any]) -> dict[str, Any]:
    """Handle opt-outs and spam."""

    if classification == "not_interested":
        _set_do_not_contact(_lead_id(inbound), summary)
    _mark_handled(str(inbound["id"]), classification, summary)
    return {"next_step": "closed without reply"}


def _handle_uncertain(inbound: dict[str, Any], classification: str, summary: dict[str, Any]) -> dict[str, Any]:
    """Surface uncertain replies for human review."""

    _mark_handled(str(inbound["id"]), classification, summary)
    return {"next_step": "human review needed"}


def heartbeat() -> dict[str, Any]:
    """Run one Closer heartbeat."""

    _load_env()
    memory = read_memory("closer")
    summary: dict[str, Any] = {
        "memory_loaded": bool(memory.strip()),
        "inbound_id": None,
        "lead_id": None,
        "classification": None,
        "branch_result": None,
        "errors": [],
    }
    _safe_log("heartbeat", "started", "heartbeat started.", summary)

    try:
        inbound_obj = next_inbound()
    except Exception as exc:
        summary["errors"].append(f"inbound fetch failed: {exc}")
        _safe_log("fetch_inbound", "failed", f"could not fetch inbound reply: {exc}", {"error": str(exc)})
        print(f"Closer heartbeat skipped: {exc}")
        return summary

    if inbound_obj is None:
        _safe_log("fetch_inbound", "skipped", "found no unhandled inbound email.", summary)
        print("Closer heartbeat found no unhandled inbound email.")
        return summary

    inbound = _inbound_to_dict(inbound_obj)
    inbound_id = str(inbound["id"])
    lead_id = _lead_id(inbound)
    summary["inbound_id"] = inbound_id
    summary["lead_id"] = lead_id

    if inbound.get("channel") != "email":
        _mark_handled(inbound_id, "spam", summary)
        summary["classification"] = "spam"
        summary["branch_result"] = {"next_step": "non-email inbound ignored until Vapi stretch"}
        _safe_log("heartbeat", "skipped", "ignored non-email inbound until Vapi stretch.", summary, lead_id)
        return summary

    classification_result = classify_reply.run(inbound_id)
    if classification_result.get("_status") == "failed" or classification_result.get("error"):
        summary["errors"].append(str(classification_result.get("error")))
        summary["classification"] = "uncertain"
        branch_result = _handle_uncertain(inbound, "uncertain", summary)
    else:
        classification = str(classification_result.get("classification") or "uncertain")
        summary["classification"] = classification
        if classification == "interested":
            branch_result = _handle_interested(inbound, classification, summary)
        elif classification in {"has_question", "has_objection"}:
            branch_result = _handle_question_or_objection(inbound, classification, summary)
        elif classification in {"not_interested", "spam"}:
            branch_result = _handle_terminal(inbound, classification, summary)
        else:
            branch_result = _handle_uncertain(inbound, "uncertain", summary)

    summary["branch_result"] = branch_result
    _surface_summary(inbound, str(summary["classification"]), branch_result)
    final_status = "succeeded" if not summary["errors"] else "failed"
    _safe_log(
        "heartbeat",
        final_status,
        f"handled inbound reply as {summary['classification']}.",
        summary,
        lead_id,
    )
    print(f"Closer heartbeat handled inbound {inbound_id} as {summary['classification']}.")
    return summary


def _run_loop() -> None:
    """Run Closer forever for local manual use."""

    interval = int(os.environ.get("CLOSER_HEARTBEAT_SECONDS", "30"))
    while True:
        heartbeat()
        time.sleep(max(1, interval))


def main() -> int:
    """CLI entrypoint for Closer."""

    parser = argparse.ArgumentParser(description="Run the Closer NemoClaw heartbeat.")
    parser.add_argument("--once", action="store_true", help="Run one heartbeat and exit.")
    args = parser.parse_args()

    if args.once:
        heartbeat()
        return 0
    _run_loop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
