"""Pitcher claw heartbeat for Mainstreet NemoClaw."""

from __future__ import annotations

import argparse
import os
import time
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency validation catches this.
    load_dotenv = None  # type: ignore[assignment]

from agents.pitcher.tools import critique_email, generate_email, send_email
from agents.shared import discord_bridge
from agents.shared.logger import logger
from agents.shared.supabase_client import (
    claim_lead_for_pitcher,
    get_client,
    next_pitcher_lead,
    read_memory,
)
from agents.shared.types import Lead


ANGLE_ORDER = ["specific_pain", "competitor_comparison", "social_proof", "curiosity"]


def _load_env() -> None:
    """Load `.env` if python-dotenv is available."""

    if load_dotenv is not None:
        load_dotenv()


def _now_iso() -> str:
    """Return a UTC timestamp for Supabase writes."""

    return datetime.now(timezone.utc).isoformat()


def _autonomous_mode() -> bool:
    """Return whether Pitcher should auto-approve and send."""

    return os.environ.get("AUTONOMOUS_MODE", "false").strip().lower() == "true"


def _angle_count() -> int:
    """Return the number of email angles to draft."""

    value = os.environ.get("PITCHER_ANGLE_COUNT", str(len(ANGLE_ORDER))).strip()
    try:
        count = int(value)
    except ValueError:
        count = len(ANGLE_ORDER)
    return max(1, min(len(ANGLE_ORDER), count))


def _safe_log(
    action_type: str,
    status: str,
    message: str,
    result: dict[str, Any] | None = None,
    lead_id: str | None = None,
) -> None:
    """Best-effort action logging."""

    try:
        logger.log("pitcher", action_type, status, message, lead_id=lead_id, result=result)
    except Exception as exc:  # pragma: no cover - local/no-credential path.
        print(f"Pitcher log skipped: {exc}")


def _safe_discord(content: str, embed: dict[str, Any] | None = None) -> None:
    """Post a Discord message when webhook configuration exists."""

    if not os.environ.get("DISCORD_WEBHOOK_URL", "").strip():
        print(f"Pitcher Discord approval instructions:\n{content}")
        return
    try:
        discord_bridge.post(content, embed=embed)
    except Exception as exc:  # pragma: no cover - local/no-webhook path.
        print(f"Pitcher Discord post skipped: {exc}\n{content}")


def _lead_to_dict(lead: Lead) -> dict[str, Any]:
    """Convert a Lead dataclass into tool-friendly dict values."""

    row = asdict(lead)
    row["id"] = str(lead.id)
    row["scraped_at"] = lead.scraped_at.isoformat() if lead.scraped_at else None
    row["updated_at"] = lead.updated_at.isoformat() if lead.updated_at else None
    return row


def _mockup_url(mockup: dict[str, Any] | None) -> str | None:
    """Return the public URL for a generated mockup row."""

    if not mockup:
        return None
    return mockup.get("vercel_url") or mockup.get("storage_url")


def _select_best(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pick the highest-scoring email candidate."""

    if not candidates:
        return None
    send_ready = [item for item in candidates if item["critique"].get("send_ready")]
    pool = send_ready or candidates
    return max(pool, key=lambda item: float(item["critique"].get("overall_score") or 0))


def _insert_outreach(
    lead: dict[str, Any],
    winner: dict[str, Any],
    candidates: list[dict[str, Any]],
    status: str,
) -> dict[str, Any]:
    """Insert the winning draft into `outreach`."""

    runner_up_variants = [
        {
            "angle": item["angle"],
            "subject": item["subject"],
            "body": item["body"],
            "critique": item["critique"],
        }
        for item in candidates
        if item["angle"] != winner["angle"]
    ]
    payload = {
        "lead_id": str(lead["id"]),
        "to_address": lead.get("email"),
        "angle": winner["angle"],
        "subject": winner["subject"],
        "body": winner["body"],
        "critique_score": winner["critique"].get("overall_score"),
        "runner_up_variants": runner_up_variants,
        "status": status,
        "drafted_at": _now_iso(),
    }
    response = get_client().table("outreach").insert(payload).execute()
    rows = getattr(response, "data", [])
    if not rows:
        raise RuntimeError("outreach insert did not return a row.")
    return rows[0]


def _post_approval_request(outreach: dict[str, Any], lead: dict[str, Any], mockup_url: str, autonomous: bool) -> None:
    """Post or print the approval instructions for one outreach draft."""

    outreach_id = str(outreach["id"])
    subject = str(outreach.get("subject") or "")
    body = str(outreach.get("body") or "")
    if autonomous:
        content = f"Pitcher auto-approved outreach {outreach_id} for {lead.get('business_name')}."
    else:
        content = (
            f"Pitcher drafted outreach for {lead.get('business_name')}.\n"
            f"Mockup: {mockup_url}\n"
            f"Subject: {subject}\n"
            f"Body: {body}\n\n"
            f"Reply with: APPROVE {outreach_id}, SKIP {outreach_id}, or EDIT {outreach_id} <new body>"
        )
    _safe_discord(content)


def _draft_candidates(lead: dict[str, Any], mockup_url: str) -> list[dict[str, Any]]:
    """Generate and critique the configured Pitcher angles."""

    candidates: list[dict[str, Any]] = []
    for angle in ANGLE_ORDER[: _angle_count()]:
        draft = generate_email.run(lead, mockup_url, angle)
        if draft.get("_status") or draft.get("error"):
            continue
        critique = critique_email.run(str(draft["subject"]), str(draft["body"]), lead, mockup_url)
        candidates.append(
            {
                "angle": angle,
                "subject": str(draft["subject"]),
                "body": str(draft["body"]),
                "critique": critique,
            }
        )
    return candidates


def _send_approved_outreach(limit: int = 3) -> list[dict[str, Any]]:
    """Send a small batch of approved unsent outreach rows."""

    response = (
        get_client()
        .table("outreach")
        .select("id")
        .eq("status", "approved")
        .is_("sent_at", "null")
        .order("drafted_at")
        .limit(limit)
        .execute()
    )
    rows = getattr(response, "data", []) or []
    results = []
    for row in rows:
        results.append(send_email.run(str(row["id"])))
    return results


def heartbeat() -> dict[str, Any]:
    """Run one Pitcher heartbeat."""

    _load_env()
    memory = read_memory("pitcher")
    summary: dict[str, Any] = {
        "memory_loaded": bool(memory.strip()),
        "approved_sends": [],
        "lead_id": None,
        "business_name": None,
        "angles_attempted": ANGLE_ORDER[: _angle_count()],
        "winner": None,
        "outreach_id": None,
        "errors": [],
    }

    _safe_log("heartbeat", "started", "heartbeat started.", summary)

    try:
        summary["approved_sends"] = _send_approved_outreach()
    except Exception as exc:
        summary["errors"].append(f"approved send sweep failed: {exc}")
        _safe_log("send_approved", "failed", f"approved outreach sweep failed: {exc}", {"error": str(exc)})

    try:
        work = next_pitcher_lead()
    except Exception as exc:
        summary["errors"].append(f"lead fetch failed: {exc}")
        _safe_log("fetch_lead", "failed", f"could not fetch Pitcher lead: {exc}", {"error": str(exc)})
        print(f"Pitcher heartbeat skipped: {exc}")
        return summary

    if not work:
        _safe_log("fetch_lead", "skipped", "found no completed mockup lead for Pitcher.", summary)
        print("Pitcher heartbeat found no completed mockup lead.")
        return summary

    lead_obj = work["lead"]
    lead = _lead_to_dict(lead_obj)
    lead_id = str(lead["id"])
    summary["lead_id"] = lead_id
    summary["business_name"] = lead.get("business_name")
    mockup_url = _mockup_url(work.get("mockup"))
    if not mockup_url:
        summary["errors"].append("missing mockup URL")
        _safe_log("fetch_mockup", "skipped", f"{lead.get('business_name')} has no public mockup URL.", summary, lead_id)
        return summary

    try:
        if not claim_lead_for_pitcher(lead_id):
            _safe_log("claim_lead", "skipped", f"lead {lead_id} was already claimed by Pitcher.", {"lead_id": lead_id}, lead_id)
            print(f"Pitcher heartbeat skipped already-claimed lead {lead_id}.")
            return summary
        _safe_log("claim_lead", "succeeded", f"claimed {lead.get('business_name')} for Pitcher.", {"lead_id": lead_id}, lead_id)
    except Exception as exc:
        summary["errors"].append(f"claim failed: {exc}")
        _safe_log("claim_lead", "failed", f"could not claim Pitcher lead: {exc}", {"error": str(exc)}, lead_id)
        return summary

    candidates = _draft_candidates(lead, mockup_url)
    if not candidates:
        summary["errors"].append("no valid email candidates")
        _safe_log("heartbeat", "failed", f"Pitcher produced no valid email drafts for {lead.get('business_name')}.", summary, lead_id)
        return summary

    winner = _select_best(candidates)
    if not winner:
        summary["errors"].append("winner selection failed")
        _safe_log("heartbeat", "failed", f"Pitcher could not select an email for {lead.get('business_name')}.", summary, lead_id)
        return summary

    autonomous = _autonomous_mode()
    status = "approved" if autonomous else "pending_approval"
    outreach = _insert_outreach(lead, winner, candidates, status)
    summary["outreach_id"] = str(outreach["id"])
    summary["winner"] = {
        "angle": winner["angle"],
        "subject": winner["subject"],
        "score": winner["critique"].get("overall_score"),
        "status": status,
    }
    _safe_log(
        "insert_outreach",
        "succeeded",
        f"queued {winner['angle']} email for {lead.get('business_name')} at {winner['critique'].get('overall_score')}/10.",
        summary["winner"],
        lead_id,
    )
    _post_approval_request(outreach, lead, mockup_url, autonomous)

    if autonomous:
        send_result = send_email.run(str(outreach["id"]))
        summary["auto_send"] = send_result

    final_status = "succeeded" if not summary["errors"] else "failed"
    _safe_log("heartbeat", final_status, f"heartbeat finished for {lead.get('business_name')}.", summary, lead_id)
    print(f"Pitcher heartbeat finished for {lead.get('business_name')}.")
    return summary


def _run_loop() -> None:
    """Run Pitcher forever for local manual use."""

    interval = int(os.environ.get("PITCHER_HEARTBEAT_SECONDS", "60"))
    while True:
        heartbeat()
        time.sleep(max(1, interval))


def main() -> int:
    """CLI entrypoint for Pitcher."""

    parser = argparse.ArgumentParser(description="Run the Pitcher NemoClaw heartbeat.")
    parser.add_argument("--once", action="store_true", help="Run one heartbeat and exit.")
    args = parser.parse_args()

    if args.once:
        heartbeat()
        return 0
    _run_loop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
