"""MEMORY.md updater for NemoClaw heartbeats."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.shared import nemotron_client
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

    try:
        result = nemotron_client.chat_json(system, user, retries=1)
    except nemotron_client.NemotronClientError as exc:
        print(f"{claw_name.title()} memory update skipped: {exc}")
        return {"status": "skipped", "reason": str(exc)}
    except Exception as exc:  # pragma: no cover - keeps heartbeat alive.
        print(f"{claw_name.title()} memory update failed: {exc}")
        return {"status": "failed", "reason": str(exc)}

    pattern = _one_line(result.get("pattern"))
    if not pattern or pattern.lower() in {"none", "null", "n/a"}:
        return {"status": "skipped", "reason": "no durable pattern"}

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    entries = _existing_entries(path)
    entries.append(f"- {timestamp} - {pattern}")
    try:
        _write_entries(path, claw_name, entries)
    except Exception as exc:  # pragma: no cover - filesystem failure.
        print(f"{claw_name.title()} memory write failed: {exc}")
        return {"status": "failed", "reason": str(exc)}

    return {"status": "updated", "pattern": pattern, "entries": min(len(entries), MAX_MEMORY_ENTRIES)}


__all__ = ["maybe_update_memory"]
