"""MEMORY.md updater for NemoClaw heartbeats."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.shared import nemotron_client
from agents.shared.supabase_client import insert_memory
from agents.shared.types import ClawName


VALID_CLAWS = {"scout", "designer", "pitcher", "closer"}
MAX_MEMORY_ENTRIES = 30


def _memory_path(claw_name: str) -> Path:
    """Return the local MEMORY.md path for one claw."""

    if claw_name not in VALID_CLAWS:
        raise ValueError(f"Unknown NemoClaw claw for memory update: {claw_name}")
    return Path(__file__).resolve().parents[1] / claw_name / "MEMORY.md"


def _title(claw_name: str) -> str:
    """Return the standard memory title."""

    return f"# {claw_name.title()} Memory"


def _summary_text(heartbeat_summary: Any) -> str:
    """Serialize heartbeat output into a compact prompt fragment."""

    if isinstance(heartbeat_summary, str):
        text = heartbeat_summary
    else:
        text = json.dumps(heartbeat_summary, ensure_ascii=True, default=str, sort_keys=True)
    return text[:4000]


def _existing_entries(path: Path) -> list[str]:
    """Return existing bullet memory entries."""

    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            entries.append(stripped)
    return entries


def _write_entries(path: Path, claw_name: str, entries: list[str]) -> None:
    """Write the title and pruned memory entries."""

    path.parent.mkdir(parents=True, exist_ok=True)
    kept = entries[-MAX_MEMORY_ENTRIES:]
    if kept:
        body = "\n".join(kept)
    else:
        body = "No observations yet."
    path.write_text(f"{_title(claw_name)}\n\n{body}\n", encoding="utf-8")


def _one_line(value: Any) -> str:
    """Normalize a model-produced pattern into one readable line."""

    text = " ".join(str(value or "").split())
    return text[:500]


def _fallback_pattern(claw_name: str, heartbeat_summary: Any) -> str | None:
    """Create a deterministic memory entry when Nemotron is unavailable."""

    if not isinstance(heartbeat_summary, dict):
        return None

    errors = heartbeat_summary.get("errors")
    if errors:
        first_error = str(errors[0]) if isinstance(errors, list) and errors else str(errors)
        return f"Last {claw_name} heartbeat had a recoverable error: {first_error[:220]}"

    target = heartbeat_summary.get("target") if isinstance(heartbeat_summary.get("target"), dict) else {}
    city = target.get("city") or heartbeat_summary.get("city") or "current city"
    niche = target.get("niche") or heartbeat_summary.get("niche") or "current niche"

    if claw_name == "scout":
        processed = heartbeat_summary.get("processed", 0)
        mockup = heartbeat_summary.get("qualified_for_mockup", 0)
        rebuild = heartbeat_summary.get("qualified_for_rebuild", 0)
        skipped = heartbeat_summary.get("skipped", 0)
        if processed:
            return (
                f"Scout recently processed {processed} {niche} leads in {city}: "
                f"{mockup} mockup, {rebuild} rebuild, {skipped} skipped."
            )
    elif claw_name == "designer":
        lead = heartbeat_summary.get("business_name") or heartbeat_summary.get("lead_name")
        winner = heartbeat_summary.get("winner") or heartbeat_summary.get("winning_variant")
        if lead or winner:
            return f"Designer last worked on {lead or 'a lead'}; winning variant was {winner or 'recorded in generated_sites'}."
    elif claw_name == "pitcher":
        angle = heartbeat_summary.get("winning_angle") or heartbeat_summary.get("angle")
        if angle:
            return f"Pitcher last winning outreach angle was {angle}; prefer it when similar lead context appears."
    elif claw_name == "closer":
        classification = heartbeat_summary.get("classification")
        if classification:
            return f"Closer last classified inbound as {classification}; reuse matching response posture for similar replies."

    return None


def _persist_memory(
    claw_name: ClawName,
    pattern: str,
    source: str,
    heartbeat_summary: Any,
    path: Path,
) -> dict[str, Any]:
    """Persist memory to Supabase and mirror it into MEMORY.md."""

    row: dict[str, Any] | None = None
    summary_payload = heartbeat_summary if isinstance(heartbeat_summary, dict) else {"summary": _summary_text(heartbeat_summary)}
    try:
        row = insert_memory(claw_name, pattern, source=source, heartbeat_summary=summary_payload)
    except Exception as exc:
        print(f"{claw_name.title()} durable memory write failed: {exc}")

    timestamp = str(row.get("created_at")) if row else datetime.now(timezone.utc).isoformat(timespec="seconds")
    entries = _existing_entries(path)
    entries.append(f"- {timestamp} - {pattern}")
    try:
        _write_entries(path, claw_name, entries)
    except Exception as exc:  # pragma: no cover - filesystem failure.
        print(f"{claw_name.title()} memory cache write failed: {exc}")
        if row:
            return {"status": "updated", "pattern": pattern, "source": source, "durable": True, "cache": "failed"}
        return {"status": "failed", "reason": str(exc)}

    try:
        from agents.shared import obsidian_writer
        obsidian_writer.append_entry(claw_name, timestamp, pattern)
    except Exception:
        pass

    return {
        "status": "updated",
        "pattern": pattern,
        "source": source,
        "durable": bool(row),
        "entries": min(len(entries), MAX_MEMORY_ENTRIES),
    }


def maybe_update_memory(claw_name: ClawName, heartbeat_summary: Any) -> dict[str, Any]:
    """Ask Nemotron for one durable pattern and append it to a claw's memory.

    The updater is intentionally best-effort. Missing SDKs, missing Nemotron
    credentials, model failures, and file-write problems are reported as a
    skipped/failed result instead of breaking the heartbeat.
    """

    path = _memory_path(claw_name)
    summary = _summary_text(heartbeat_summary)
    system = (
        "You update MEMORY.md for a Mainstreet NemoClaw claw. "
        "Return one reusable pattern only if this heartbeat taught something "
        "useful for future runs. Return JSON: {\"pattern\": string|null}."
    )
    user = (
        f"Claw: {claw_name}\n"
        f"Current memory entries:\n{json.dumps(_existing_entries(path)[-10:], ensure_ascii=True)}\n\n"
        f"Heartbeat summary:\n{summary}\n\n"
        "Keep the pattern concrete, short, and operational. "
        "If there is no useful durable lesson, use null."
    )

    source = "nemotron"
    try:
        result = nemotron_client.chat_json(system, user, retries=1)
    except nemotron_client.NemotronClientError as exc:
        pattern = _fallback_pattern(claw_name, heartbeat_summary)
        if not pattern:
            print(f"{claw_name.title()} memory update skipped: {exc}")
            return {"status": "skipped", "reason": str(exc)}
        print(f"{claw_name.title()} memory used fallback pattern because Nemotron failed: {exc}")
        return _persist_memory(claw_name, pattern, "fallback", heartbeat_summary, path)
    except Exception as exc:  # pragma: no cover - keeps heartbeat alive.
        pattern = _fallback_pattern(claw_name, heartbeat_summary)
        if not pattern:
            print(f"{claw_name.title()} memory update failed: {exc}")
            return {"status": "failed", "reason": str(exc)}
        print(f"{claw_name.title()} memory used fallback pattern because update failed: {exc}")
        return _persist_memory(claw_name, pattern, "fallback", heartbeat_summary, path)

    pattern = _one_line(result.get("pattern"))
    if not pattern or pattern.lower() in {"none", "null", "n/a"}:
        return {"status": "skipped", "reason": "no durable pattern"}

    return _persist_memory(claw_name, pattern, source, heartbeat_summary, path)


__all__ = ["maybe_update_memory"]
