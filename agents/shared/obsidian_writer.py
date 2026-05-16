"""Obsidian vault writer — mirrors agent memory into browsable Markdown notes."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

VAULT_DIR = Path(__file__).resolve().parents[2] / "obsidian"

VALID_CLAWS = {"scout", "designer", "pitcher", "closer"}

_CLAW_DESCRIPTIONS = {
    "scout": "Finds local businesses worth helping. Scores websites, extracts pain points.",
    "designer": "Generates Tailwind mockups for qualified leads, picks the winning variant.",
    "pitcher": "Drafts personalized outreach emails, queues them for Discord approval.",
    "closer": "Classifies inbound replies and books meetings.",
}

_PIPELINE = "[[Scout Memory]] → [[Designer Memory]] → [[Pitcher Memory]] → [[Closer Memory]]"

_DOC_FILES: dict[str, tuple[str, list[str]]] = {
    "soul":      ("SOUL.md",      ["soul"]),
    "tools":     ("TOOLS.md",     ["tools"]),
    "agents":    ("AGENTS.md",    ["workflow"]),
    "heartbeat": ("HEARTBEAT.md", ["heartbeat"]),
}

def _doc_nav(claw_name: str) -> str:
    title = claw_name.title()
    parts = [f"[[{title} Memory]]", f"[[{title} Soul]]", f"[[{title} Tools]]", f"[[{title} Agents]]", f"[[{title} Heartbeat]]"]
    return " | ".join(parts)


def _note_path(claw_name: str) -> Path:
    return VAULT_DIR / f"{claw_name.title()} Memory.md"


def _memory_path(claw_name: str) -> Path:
    return Path(__file__).resolve().parents[1] / claw_name / "MEMORY.md"


def _format_ts(timestamp: str) -> str:
    """Convert ISO timestamp to 'YYYY-MM-DD HH:MM UTC'."""
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return timestamp[:16].replace("T", " ") + " UTC"


def _entry_icon(pattern: str) -> str:
    return "❌" if "error" in pattern.lower() else "✅"


def _note_header(claw_name: str) -> str:
    desc = _CLAW_DESCRIPTIONS.get(claw_name, "")
    return (
        f"---\ntags: [memory, {claw_name}]\nclaw: {claw_name}\n---\n\n"
        f"# {claw_name.title()} Memory\n\n"
        f"> {desc}\n"
        f"> Pipeline: {_PIPELINE}\n\n"
        "## Observations\n\n"
    )


def append_entry(claw_name: str, timestamp: str, pattern: str) -> None:
    """Append one memory entry to the agent's Obsidian note."""
    if claw_name not in VALID_CLAWS:
        return
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    path = _note_path(claw_name)
    if not path.exists():
        path.write_text(_note_header(claw_name), encoding="utf-8")
    ts_str = _format_ts(timestamp)
    icon = _entry_icon(pattern)
    entry = f"### {ts_str}\n{icon} {pattern.strip()}\n\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(entry)


def _parse_memory_entries(raw: str) -> list[tuple[str, str]]:
    """Parse MEMORY.md bullet lines into (timestamp, pattern) pairs."""
    entries = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        rest = stripped[2:]
        match = re.match(r"^(\S+)\s+-\s+(.+)$", rest)
        if match:
            entries.append((match.group(1), match.group(2)))
    return entries


def _write_agent_note(claw_name: str) -> None:
    path = _note_path(claw_name)
    body = _note_header(claw_name)
    mem_path = _memory_path(claw_name)
    if mem_path.exists():
        entries = _parse_memory_entries(mem_path.read_text(encoding="utf-8"))
        for ts, pattern in entries:
            ts_str = _format_ts(ts)
            icon = _entry_icon(pattern)
            body += f"### {ts_str}\n{icon} {pattern.strip()}\n\n"
    if body.endswith("## Observations\n\n"):
        body += "_No observations yet._\n"
    path.write_text(body, encoding="utf-8")


def _write_agent_docs(claw_name: str) -> None:
    """Write SOUL, TOOLS, AGENTS, HEARTBEAT notes for one claw."""
    agents_dir = Path(__file__).resolve().parents[1] / claw_name
    title = claw_name.title()
    nav = _doc_nav(claw_name)
    for key, (filename, tags) in _DOC_FILES.items():
        src = agents_dir / filename
        if not src.exists():
            continue
        raw = src.read_text(encoding="utf-8").strip()
        # Strip a leading # heading from the source so we don't duplicate it
        lines = raw.splitlines()
        if lines and lines[0].startswith("# "):
            raw = "\n".join(lines[1:]).lstrip("\n")
        tag_str = ", ".join([claw_name] + tags)
        doc_title = f"{title} {key.title()}"
        body = (
            f"---\ntags: [{tag_str}]\nclaw: {claw_name}\n---\n\n"
            f"# {doc_title}\n\n"
            f"> {nav}\n\n"
            f"{raw}\n"
        )
        (VAULT_DIR / f"{doc_title}.md").write_text(body, encoding="utf-8")


def _write_home() -> None:
    path = VAULT_DIR / "Home.md"
    rows = ""
    for claw, desc in [
        ("Scout",    "Finds and scores local auto repair shop leads"),
        ("Designer", "Generates website mockups for qualified leads"),
        ("Pitcher",  "Drafts and queues personalized outreach emails"),
        ("Closer",   "Classifies inbound replies and books meetings"),
    ]:
        cl = claw.lower()
        docs = f"[[{claw} Soul]] · [[{claw} Tools]] · [[{claw} Agents]] · [[{claw} Heartbeat]]"
        rows += f"| [[{claw} Memory]] | {desc} | {docs} |\n"
    path.write_text(
        "---\ntags: [home, index]\n---\n\n"
        "# Mainstreet Agent Memory\n\n"
        "Real-time memory vault for the four NemoClaw agents powering the Mainstreet autonomous sales team.\n\n"
        "## Pipeline\n\n"
        f"{_PIPELINE}\n\n"
        "## Agents\n\n"
        "| Memory | Role | Docs |\n"
        "| --- | --- | --- |\n"
        f"{rows}\n"
        "## Usage\n\n"
        "- Open this folder in Obsidian → graph view shows agent relationships\n"
        "- Memory notes auto-update as claws run — each heartbeat appends a new entry\n"
        "- Search `#error` to find recent failures across all agents\n",
        encoding="utf-8",
    )


def _write_obsidian_config() -> None:
    config_dir = VAULT_DIR / ".obsidian"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "app.json").write_text(
        '{"legacyEditor": false, "livePreview": true}\n', encoding="utf-8"
    )


def init_vault() -> None:
    """Create vault notes from existing MEMORY.md files. Safe to re-run."""
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    _write_obsidian_config()
    _write_home()
    for claw_name in VALID_CLAWS:
        _write_agent_note(claw_name)
        _write_agent_docs(claw_name)
    print(f"Obsidian vault initialized at {VAULT_DIR}")


__all__ = ["append_entry", "init_vault"]
