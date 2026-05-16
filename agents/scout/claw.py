"""Scout claw heartbeat for the Mainstreet NemoClaw demo."""

from __future__ import annotations

import argparse
import os
import time
from datetime import datetime, timezone
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency validation catches this.
    load_dotenv = None  # type: ignore[assignment]

from agents.scout.tools import extract_pain_points, score_website, scrape_leads
from agents.shared import discord_bridge, memory_updater
from agents.shared.logger import logger
from agents.shared.openclaw_runtime import load_openclaw_context
from agents.shared.supabase_client import DEFAULT_SCOUT_NICHES, DEFAULT_TARGET, get_client, next_scout_target, read_memory


DEFAULT_SCRAPE_LIMIT = 20
DEFAULT_PROCESS_LIMIT = 5
LEGACY_SCOUT_NICHES = {
    "auto detailing",
    "dentist",
    "electrician",
    "hvac contractor",
    "landscaper",
    "pet groomer",
    "plumber",
    "roofing contractor",
}


def _load_env() -> None:
    """Load `.env` if python-dotenv is available."""

    if load_dotenv is not None:
        load_dotenv()


def _now_iso() -> str:
    """Return a UTC timestamp for Supabase updates."""

    return datetime.now(timezone.utc).isoformat()


def _int_env(name: str, default: int) -> int:
    """Read a positive integer env var."""

    value = os.environ.get(name, "").strip()
    if not value:
        return default
    try:
        return max(1, int(value))
    except ValueError:
        return default


def _list_env(name: str) -> list[str]:
    """Read a comma-separated env var as clean string values."""

    raw = os.environ.get(name, "")
    return [part.strip() for part in raw.split(",") if part.strip()]


def _safe_log(
    action_type: str,
    status: str,
    message: str,
    result: dict[str, Any] | None = None,
    lead_id: str | None = None,
) -> None:
    """Best-effort action logging that does not break the heartbeat."""

    try:
        logger.log("scout", action_type, status, message, lead_id=lead_id, result=result)
    except Exception as exc:  # pragma: no cover - local/no-credential path.
        print(f"Scout log skipped: {exc}")


def _safe_discord(content: str) -> None:
    """Post a Discord summary when the webhook is configured."""

    if not os.environ.get("DISCORD_WEBHOOK_URL", "").strip():
        return
    try:
        discord_bridge.post(content)
    except Exception as exc:  # pragma: no cover - local/no-webhook path.
        print(f"Scout Discord summary skipped: {exc}")


def _finish(summary: dict[str, Any]) -> dict[str, Any]:
    """Run best-effort end-of-heartbeat memory update."""

    memory_updater.maybe_update_memory("scout", summary)
    return summary


def _niches_from_target(target: dict[str, Any]) -> list[str]:
    """Normalize Scout target config to one or more niches.

    `SCOUT_NICHES` is the fastest demo override. Supabase can also provide a
    `niches` JSON array. Legacy single-niche `auto repair` configs are treated
    as the old seed value and upgraded to the broader Santa Claws default.
    """

    env_niches = _list_env("SCOUT_NICHES")
    if env_niches:
        return env_niches

    def _fresh_niches(values: list[str]) -> list[str]:
        """Replace the old narrow service list with broader demo categories."""

        normalized = {value.lower() for value in values}
        if normalized and normalized.issubset(LEGACY_SCOUT_NICHES):
            return list(DEFAULT_SCOUT_NICHES)
        return [value for value in values if value.lower() != "auto detailing"]

    raw_niches = target.get("niches")
    if isinstance(raw_niches, list):
        niches = [str(niche).strip() for niche in raw_niches if str(niche).strip()]
        if niches:
            return _fresh_niches(niches)
    if isinstance(raw_niches, str):
        niches = [part.strip() for part in raw_niches.split(",") if part.strip()]
        if niches:
            return _fresh_niches(niches)

    niche = str(target.get("niche") or "").strip()
    if niche and niche.lower() != "auto repair":
        return [niche]
    return list(DEFAULT_SCOUT_NICHES)


def _lead_count(city: str, niche: str) -> int:
    """Return current lead count for a niche so Scout fills sparse categories."""

    query = get_client().table("leads").select("id").eq("city", city).eq("niche", niche).limit(1000)
    response = query.execute()
    rows = getattr(response, "data", None)
    if not isinstance(rows, list):
        raise RuntimeError("Supabase lead-count query did not return a list.")
    return len(rows)


def _choose_niche(city: str, state: str | None, niches: list[str]) -> str:
    """Pick the niche with the fewest existing leads, with a time fallback."""

    if not niches:
        return str(DEFAULT_TARGET["niche"])
    if len(niches) == 1:
        return niches[0]
    try:
        return min(niches, key=lambda niche: (_lead_count(city, niche), niches.index(niche)))
    except Exception as exc:
        print(f"Scout niche balancing unavailable; rotating by time. Reason: {exc}")
        index = int(datetime.now(timezone.utc).timestamp() // 60) % len(niches)
        return niches[index]


def _target() -> dict[str, Any]:
    """Read Scout target config, falling back to broad local-service targets."""

    try:
        target = next_scout_target()
        if not target.get("city"):
            raise ValueError("config.target must include city")
    except Exception as exc:
        print(f"Scout target config unavailable; using default target. Reason: {exc}")
        target = dict(DEFAULT_TARGET)
    city = str(target.get("city", DEFAULT_TARGET["city"]))
    state = target.get("state")
    niches = _niches_from_target(target)
    chosen = dict(target)
    chosen["niches"] = niches
    chosen["niche"] = _choose_niche(city, str(state) if state else None, niches)
    return chosen


def _pending_leads(city: str, niche: str, limit: int) -> list[dict[str, Any]]:
    """Fetch a small batch of pending leads for Scout qualification."""

    response = (
        get_client()
        .table("leads")
        .select("*")
        .eq("city", city)
        .eq("niche", niche)
        .eq("qualification_status", "pending")
        .eq("do_not_contact", False)
        .order("scraped_at")
        .limit(limit)
        .execute()
    )
    rows = getattr(response, "data", None)
    if not isinstance(rows, list):
        raise RuntimeError("Supabase pending lead query did not return a list.")
    return rows


def _qualification(lead: dict[str, Any], website_score: int, reasons: list[str]) -> tuple[str, str]:
    """Apply the simple Scout qualification rubric."""

    if not lead.get("business_name") or not (lead.get("address") or lead.get("phone") or lead.get("website")):
        return "skip", "bad or incomplete lead data"
    if not lead.get("website") or "no website" in reasons:
        return "qualified_for_mockup", "missing website"
    if website_score <= 3:
        return "qualified_for_mockup", f"low website score {website_score}/10"
    if website_score <= 6:
        return "qualified_for_rebuild", f"weak website score {website_score}/10"
    return "skip", f"website already strong enough at {website_score}/10"


def _update_lead(lead_id: str, payload: dict[str, Any]) -> None:
    """Update a lead row in Supabase."""

    payload["updated_at"] = _now_iso()
    get_client().table("leads").update(payload).eq("id", lead_id).execute()


def _process_lead(lead: dict[str, Any]) -> dict[str, Any]:
    """Score, enrich, and qualify one lead."""

    lead_id = str(lead["id"])
    score_result = score_website.run(lead.get("website"), lead_id=lead_id)
    score = int(score_result.get("score") or 0)
    reasons = [str(reason) for reason in score_result.get("reasons", [])]

    try:
        pain_points = extract_pain_points.run(lead)
    except Exception as exc:
        pain_points = []
        _safe_log(
            "extract_pain_points",
            "skipped",
            f"could not extract pain points for {lead.get('business_name', 'lead')}: {exc}",
            {"lead_id": lead_id, "error": str(exc)},
            lead_id=lead_id,
        )

    qualification_status, qualification_reason = _qualification(lead, score, reasons)
    _update_lead(
        lead_id,
        {
            "website_score": score,
            "website_score_reasons": reasons,
            "top_review_pain_points": pain_points,
            "qualification_status": qualification_status,
            "qualification_reason": qualification_reason,
        },
    )
    _safe_log(
        "qualify_lead",
        "succeeded" if qualification_status != "skip" else "skipped",
        f"qualified {lead.get('business_name', 'lead')} as {qualification_status}. {qualification_reason}.",
        {
            "lead_id": lead_id,
            "website_score": score,
            "qualification_status": qualification_status,
            "qualification_reason": qualification_reason,
        },
        lead_id=lead_id,
    )
    return {
        "lead_id": lead_id,
        "business_name": lead.get("business_name"),
        "website_score": score,
        "qualification_status": qualification_status,
    }


def heartbeat() -> dict[str, Any]:
    """Run one Scout heartbeat."""

    _load_env()
    openclaw_context = load_openclaw_context("scout")
    memory = read_memory("scout")
    target = _target()
    city = str(target.get("city", DEFAULT_TARGET["city"]))
    state = target.get("state")
    niche = str(target.get("niche", DEFAULT_TARGET["niche"]))
    location = f"{city}, {state}" if state else city
    scrape_limit = _int_env("SCOUT_SCRAPE_LIMIT", DEFAULT_SCRAPE_LIMIT)
    process_limit = _int_env("SCOUT_PROCESS_LIMIT", DEFAULT_PROCESS_LIMIT)

    summary: dict[str, Any] = {
        "target": {"city": city, "state": state, "niche": niche, "niches": target.get("niches", [niche])},
        "memory_loaded": bool(memory.strip()),
        "openclaw_context": openclaw_context.summary(),
        "scraped_inserted": 0,
        "processed": 0,
        "qualified_for_mockup": 0,
        "qualified_for_rebuild": 0,
        "skipped": 0,
        "errors": [],
    }

    _safe_log("heartbeat", "started", f"heartbeat started for {niche} in {location}.", summary)
    _safe_log(
        "openclaw_context",
        "succeeded",
        "loaded Scout OpenClaw-compatible context files.",
        openclaw_context.summary(),
    )

    try:
        inserted = scrape_leads.run(city=city, niche=niche, limit=scrape_limit, state=state, country="United States")
        summary["scraped_inserted"] = inserted
        if inserted == 0:
            _safe_log(
                "scrape_dedup_check",
                "skipped",
                f"found no new {niche} leads in {location}; possible dedup saturation.",
                {"city": city, "niche": niche},
            )
    except Exception as exc:
        summary["errors"].append(f"scrape failed: {exc}")
        _safe_log("scrape_batch", "failed", f"scrape failed for {niche} in {location}: {exc}", {"error": str(exc)})

    try:
        leads = _pending_leads(city=city, niche=niche, limit=process_limit)
    except Exception as exc:
        summary["errors"].append(f"pending lead fetch failed: {exc}")
        _safe_log("fetch_pending_leads", "failed", f"could not fetch pending Scout leads: {exc}", {"error": str(exc)})
        leads = []

    for lead in leads[:process_limit]:
        try:
            result = _process_lead(lead)
            summary["processed"] += 1
            status = result["qualification_status"]
            if status == "qualified_for_mockup":
                summary["qualified_for_mockup"] += 1
            elif status == "qualified_for_rebuild":
                summary["qualified_for_rebuild"] += 1
            else:
                summary["skipped"] += 1
        except Exception as exc:
            summary["errors"].append(f"lead {lead.get('id')} failed: {exc}")
            _safe_log(
                "qualify_lead",
                "failed",
                f"failed to qualify {lead.get('business_name', 'lead')}: {exc}",
                {"lead_id": lead.get("id"), "error": str(exc)},
                lead_id=str(lead.get("id")) if lead.get("id") else None,
            )

    final_status = "succeeded" if not summary["errors"] else "failed"
    final_text = (
        f"heartbeat finished for {niche} in {location}. "
        f"Inserted {summary['scraped_inserted']}, processed {summary['processed']}, "
        f"mockup {summary['qualified_for_mockup']}, rebuild {summary['qualified_for_rebuild']}, skipped {summary['skipped']}."
    )
    _safe_log("heartbeat", final_status, final_text, summary)
    _safe_discord(f"Scout: {final_text}")
    print(final_text)
    return _finish(summary)


def _run_loop() -> None:
    """Run Scout forever for local manual use."""

    interval = _int_env("SCOUT_HEARTBEAT_SECONDS", 60)
    while True:
        heartbeat()
        time.sleep(interval)


def main() -> int:
    """CLI entrypoint for Scout."""

    parser = argparse.ArgumentParser(description="Run the Scout NemoClaw heartbeat.")
    parser.add_argument("--once", action="store_true", help="Run one heartbeat and exit.")
    args = parser.parse_args()

    if args.once:
        heartbeat()
        return 0
    _run_loop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
