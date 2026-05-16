"""OpenClaw-compatible context loading for NemoClaw claw heartbeats."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


CONTEXT_FILES = ("SOUL.md", "AGENTS.md", "TOOLS.md", "HEARTBEAT.md", "MEMORY.md")


def _load_nemoclaw_config() -> dict:
    """Read nemoclaw.json from the agents root."""
    config_path = Path(__file__).resolve().parents[1] / "nemoclaw.json"
    return json.loads(config_path.read_text(encoding="utf-8"))


def list_agents() -> list[dict]:
    """Return the agents list from nemoclaw.json."""
    return _load_nemoclaw_config().get("agents", [])


# Computed from nemoclaw.json so it stays in sync with the config file.
VALID_CLAWS: set[str] = {agent["name"] for agent in list_agents()}


class OpenClawRuntimeError(RuntimeError):
    """Raised when an OpenClaw-compatible claw workspace is malformed."""


@dataclass(frozen=True)
class OpenClawContext:
    """Runtime context read from the OpenClaw-compatible claw files."""

    claw_name: str
    root: Path
    soul: str
    instructions: str
    tools: str
    heartbeat: str
    memory: str
    interval_seconds: int
    entrypoint: str

    def prompt_context(self) -> str:
        """Return a compact prompt bundle for model-facing tool calls."""

        return "\n\n".join(
            [
                f"# SOUL.md\n{self.soul.strip()}",
                f"# AGENTS.md\n{self.instructions.strip()}",
                f"# TOOLS.md\n{self.tools.strip()}",
                f"# MEMORY.md\n{self.memory.strip()}",
            ]
        ).strip()

    def summary(self) -> dict[str, object]:
        """Return safe metadata for action logs and dashboard visibility."""

        return {
            "claw_name": self.claw_name,
            "entrypoint": self.entrypoint,
            "interval_seconds": self.interval_seconds,
            "context_files": list(CONTEXT_FILES),
            "prompt_context_chars": len(self.prompt_context()),
        }


def _agents_root() -> Path:
    """Return the agents package root."""

    return Path(__file__).resolve().parents[1]


def _claw_root(claw_name: str) -> Path:
    """Return the directory for a known claw."""

    if claw_name not in VALID_CLAWS:
        raise OpenClawRuntimeError(f"Unknown claw: {claw_name}")
    return _agents_root() / claw_name


def _read_required(root: Path, filename: str) -> str:
    """Read a required OpenClaw-compatible context file."""

    path = root / filename
    if not path.exists():
        raise OpenClawRuntimeError(f"Missing {path}")
    return path.read_text(encoding="utf-8")


def _heartbeat_value(heartbeat: str, key: str) -> str | None:
    """Extract a simple `key: value` pair from HEARTBEAT.md."""

    prefix = f"{key}:"
    for line in heartbeat.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(prefix):
            return stripped[len(prefix) :].strip()
    return None


def _parse_interval(heartbeat: str) -> int:
    """Parse `interval: 60s` from HEARTBEAT.md."""

    raw_value = _heartbeat_value(heartbeat, "interval") or "60s"
    value = raw_value.lower().removesuffix("seconds").removesuffix("second").removesuffix("s").strip()
    try:
        seconds = int(value)
    except ValueError as exc:
        raise OpenClawRuntimeError(f"Invalid HEARTBEAT.md interval: {raw_value}") from exc
    return max(1, seconds)


def load_openclaw_context(claw_name: str) -> OpenClawContext:
    """Load SOUL, AGENTS, TOOLS, HEARTBEAT, and MEMORY for one claw."""

    root = _claw_root(claw_name)
    files = {filename: _read_required(root, filename) for filename in CONTEXT_FILES}
    entrypoint = _heartbeat_value(files["HEARTBEAT.md"], "entrypoint")
    if not entrypoint:
        raise OpenClawRuntimeError(f"{root / 'HEARTBEAT.md'} is missing `entrypoint:`")
    if ":" not in entrypoint:
        raise OpenClawRuntimeError(f"Invalid HEARTBEAT.md entrypoint: {entrypoint}")

    return OpenClawContext(
        claw_name=claw_name,
        root=root,
        soul=files["SOUL.md"],
        instructions=files["AGENTS.md"],
        tools=files["TOOLS.md"],
        heartbeat=files["HEARTBEAT.md"],
        memory=files["MEMORY.md"],
        interval_seconds=_parse_interval(files["HEARTBEAT.md"]),
        entrypoint=entrypoint,
    )
