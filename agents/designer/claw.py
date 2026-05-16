"""Designer claw heartbeat for the Mainstreet NemoClaw demo."""

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

from agents.designer.tools import critique_mockup, deploy_to_vercel, generate_mockup, pick_winner
from agents.shared import discord_bridge, memory_updater
from agents.shared.logger import logger
from agents.shared.supabase_client import (
    claim_lead_for_designer,
    get_client,
    next_designer_lead,
    read_memory,
)
from agents.shared.types import Lead


VARIANT_ORDER = ["clean_modern", "retro_local", "premium"]


def _load_env() -> None:
    """Load `.env` if python-dotenv is available."""

    if load_dotenv is not None:
        load_dotenv()


def _now_iso() -> str:
    """Return a UTC timestamp for Supabase writes."""

    return datetime.now(timezone.utc).isoformat()


def _variant_count() -> int:
    """Return variant count, defaulting to the full 3-variant quality path."""

    value = os.environ.get("DESIGNER_VARIANT_COUNT", "3").strip()
    return 1 if value == "1" else 3


def _max_iterations() -> int:
    """Return the Designer self-critique iteration cap."""

    value = os.environ.get("DESIGNER_MAX_ITERATIONS", "5").strip()
    try:
        count = int(value)
    except ValueError:
        count = 5
    return max(1, min(5, count))


def _score(critique: dict[str, Any] | None) -> int:
    """Return a normalized critique score."""

    if not critique:
        return 0
    try:
        return int(float(critique.get("score") or 0))
    except (TypeError, ValueError):
        return 0


def _safe_log(
    action_type: str,
    status: str,
    message: str,
    result: dict[str, Any] | None = None,
    lead_id: str | None = None,
) -> None:
    """Best-effort action logging."""

    try:
        logger.log("designer", action_type, status, message, lead_id=lead_id, result=result)
    except Exception as exc:  # pragma: no cover - local/no-credential path.
        print(f"Designer log skipped: {exc}")


def _safe_discord(content: str) -> None:
    """Post a Discord summary when configured."""

    if not os.environ.get("DISCORD_WEBHOOK_URL", "").strip():
        return
    try:
        discord_bridge.post(content)
    except Exception as exc:  # pragma: no cover - local/no-webhook path.
        print(f"Designer Discord summary skipped: {exc}")


def _finish(summary: dict[str, Any]) -> dict[str, Any]:
    """Run best-effort end-of-heartbeat memory update."""

    memory_updater.maybe_update_memory("designer", summary)
    return summary


def _lead_to_dict(lead: Lead) -> dict[str, Any]:
    """Convert a Lead dataclass into tool-friendly dict values."""

    row = asdict(lead)
    row["id"] = str(lead.id)
    row["scraped_at"] = lead.scraped_at.isoformat() if lead.scraped_at else None
    row["updated_at"] = lead.updated_at.isoformat() if lead.updated_at else None
    return row


def _slug(lead: dict[str, Any], variant: str) -> str:
    """Build a stable mockup slug."""

    name = str(lead.get("business_name") or "lead").lower()
    slug = "".join(char if char.isalnum() else "-" for char in name)
    slug = "-".join(part for part in slug.split("-") if part)
    return f"{slug or 'lead'}-{variant}"


def _insert_generated_site(
    lead_id: str,
    variant: str,
    html: str,
    critique: dict[str, Any],
    deploy: dict[str, Any],
    is_winner: bool,
    iterations: int,
    pick_reasoning: str | None = None,
) -> dict[str, Any]:
    """Insert one generated_sites row and return the inserted row."""

    provider = deploy.get("provider")
    payload = {
        "lead_id": lead_id,
        "variant": variant,
        "vercel_url": deploy.get("url") if provider == "vercel" else None,
        "storage_url": deploy.get("url") if provider == "supabase" else None,
        "html_content": html,
        "self_critique_score": critique.get("score"),
        "self_critique_iterations": iterations,
        "critique_issues": critique.get("issues", []),
        "is_chosen_winner": is_winner,
        "pick_reasoning": pick_reasoning,
    }
    response = get_client().table("generated_sites").insert(payload).execute()
    rows = getattr(response, "data", [])
    if not rows:
        raise RuntimeError("generated_sites insert did not return a row.")
    return rows[0]


def _mark_winner(lead_id: str, site_id: str, reasoning: str) -> None:
    """Ensure exactly one generated site is marked as chosen winner."""

    client = get_client()
    client.table("generated_sites").update({"is_chosen_winner": False}).eq("lead_id", lead_id).execute()
    client.table("generated_sites").update(
        {"is_chosen_winner": True, "pick_reasoning": reasoning}
    ).eq("id", site_id).execute()


def _process_variant(lead: dict[str, Any], variant: str) -> dict[str, Any]:
    """Generate, self-critique, deploy, and persist one variant."""

    lead_id = str(lead["id"])
    html: str | None = None
    critique: dict[str, Any] | None = None
    iterations = 0

    for iteration in range(1, _max_iterations() + 1):
        try:
            html = generate_mockup.run(lead, variant, previous_critique=critique)
            critique = critique_mockup.run(html, lead)
            iterations = iteration
            score = _score(critique)
            _safe_log(
                "self_critique_iteration",
                "succeeded",
                f"{variant} iteration {iteration} scored {score}/10.",
                {"variant": variant, "iteration": iteration, "score": score, "issues": critique.get("issues", [])},
                lead_id,
            )
            if score >= 8:
                break
        except Exception as exc:
            if html and critique:
                _safe_log(
                    "self_critique_iteration",
                    "skipped",
                    f"{variant} iteration {iteration} failed; keeping prior attempt.",
                    {"variant": variant, "iteration": iteration, "error": str(exc)},
                    lead_id,
                )
                break
            raise

    if html is None or critique is None:
        raise RuntimeError(f"{variant} did not produce a mockup.")

    deploy = deploy_to_vercel.run(html, _slug(lead, variant), lead_id=lead_id)
    site = _insert_generated_site(
        lead_id=lead_id,
        variant=variant,
        html=html,
        critique=critique,
        deploy=deploy,
        is_winner=False,
        iterations=iterations,
    )
    url = deploy.get("url")
    return {
        "site_id": str(site["id"]),
        "variant": variant,
        "url": url,
        "score": critique.get("score"),
        "iterations": iterations,
        "issues": critique.get("issues", []),
        "html": html,
        "provider": deploy.get("provider"),
    }


def heartbeat() -> dict[str, Any]:
    """Run one Designer heartbeat."""

    _load_env()
    memory = read_memory("designer")
    summary: dict[str, Any] = {
        "memory_loaded": bool(memory.strip()),
        "lead_id": None,
        "business_name": None,
        "variants_attempted": [],
        "winner": None,
        "errors": [],
    }

    _safe_log("heartbeat", "started", "heartbeat started.", summary)

    try:
        lead_obj = next_designer_lead()
    except Exception as exc:
        summary["errors"].append(f"lead fetch failed: {exc}")
        _safe_log("fetch_lead", "failed", f"could not fetch Designer lead: {exc}", {"error": str(exc)})
        print(f"Designer heartbeat skipped: {exc}")
        return _finish(summary)

    if lead_obj is None:
        _safe_log("fetch_lead", "skipped", "found no qualified lead for Designer.", summary)
        print("Designer heartbeat found no qualified lead.")
        return _finish(summary)

    lead = _lead_to_dict(lead_obj)
    lead_id = str(lead["id"])
    summary["lead_id"] = lead_id
    summary["business_name"] = lead.get("business_name")

    try:
        if not claim_lead_for_designer(lead_id):
            _safe_log("claim_lead", "skipped", f"lead {lead_id} was already claimed.", {"lead_id": lead_id}, lead_id)
            print(f"Designer heartbeat skipped already-claimed lead {lead_id}.")
            return _finish(summary)
        _safe_log("claim_lead", "succeeded", f"claimed {lead.get('business_name')} for Designer.", {"lead_id": lead_id}, lead_id)
    except Exception as exc:
        summary["errors"].append(f"claim failed: {exc}")
        _safe_log("claim_lead", "failed", f"could not claim Designer lead: {exc}", {"lead_id": lead_id, "error": str(exc)}, lead_id)
        print(f"Designer heartbeat claim failed: {exc}")
        return _finish(summary)

    variants = VARIANT_ORDER[: _variant_count()]
    variant_results: list[dict[str, Any]] = []
    for variant in variants:
        summary["variants_attempted"].append(variant)
        try:
            result = _process_variant(lead, variant)
            variant_results.append(result)
            _safe_log(
                "generate_variant",
                "succeeded",
                (
                    f"built {variant} mockup for {lead.get('business_name')} "
                    f"at {result.get('score')}/10 after {result.get('iterations')} iteration(s)."
                ),
                {
                    "variant": variant,
                    "url": result.get("url"),
                    "score": result.get("score"),
                    "iterations": result.get("iterations"),
                },
                lead_id,
            )
        except Exception as exc:
            summary["errors"].append(f"{variant} failed: {exc}")
            _safe_log(
                "generate_variant",
                "failed",
                f"failed {variant} mockup for {lead.get('business_name')}: {exc}",
                {"variant": variant, "error": str(exc)},
                lead_id,
            )

    if not variant_results:
        final_text = f"Designer failed to produce a mockup for {lead.get('business_name')}."
        _safe_log("heartbeat", "failed", final_text, summary, lead_id)
        _safe_discord(f"Designer: {final_text}")
        print(final_text)
        return _finish(summary)

    winner = pick_winner.run(lead, variant_results)
    winner_variant = winner.get("winner")
    winning_result = next((item for item in variant_results if item["variant"] == winner_variant), variant_results[0])
    _mark_winner(lead_id, winning_result["site_id"], str(winner.get("reasoning") or ""))
    summary["winner"] = {
        "variant": winning_result["variant"],
        "url": winning_result.get("url"),
        "score": winning_result.get("score"),
        "reasoning": winner.get("reasoning"),
    }
    get_client().table("leads").update({"worked_by_designer": True, "updated_at": _now_iso()}).eq("id", lead_id).execute()

    final_status = "succeeded" if not summary["errors"] else "failed"
    final_text = (
        f"heartbeat finished for {lead.get('business_name')}. "
        f"Winner {summary['winner']['variant']} scored {summary['winner']['score']}/10."
    )
    _safe_log("heartbeat", final_status, final_text, summary, lead_id)
    _safe_discord(f"Designer: {final_text}")
    print(final_text)
    return _finish(summary)


def _run_loop() -> None:
    """Run Designer forever for local manual use."""

    interval = int(os.environ.get("DESIGNER_HEARTBEAT_SECONDS", "60"))
    while True:
        heartbeat()
        time.sleep(max(1, interval))


def main() -> int:
    """CLI entrypoint for Designer."""

    parser = argparse.ArgumentParser(description="Run the Designer NemoClaw heartbeat.")
    parser.add_argument("--once", action="store_true", help="Run one heartbeat and exit.")
    args = parser.parse_args()

    if args.once:
        heartbeat()
        return 0
    _run_loop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
