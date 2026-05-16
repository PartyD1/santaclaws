"""Minimal Discord approval worker for Mainstreet NemoClaw."""

from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency validation catches this.
    load_dotenv = None  # type: ignore[assignment]

from agents.shared import nemotron_client
from agents.shared.logger import logger
from agents.shared.supabase_client import (
    get_client,
    pipeline_counts,
    recent_actions_all,
    recent_memory,
)

_LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"


Decision = Literal["approve", "skip", "edit"]
COMMAND_RE = re.compile(r"^\s*(APPROVE|SKIP|EDIT)\s+([0-9a-fA-F-]{32,36})(?:\s+([\s\S]+))?\s*$", re.IGNORECASE)
PING_RE = re.compile(r"^\s*!?(PING|HELP)\s*$", re.IGNORECASE)
_CLAWS = ("scout", "designer", "pitcher", "closer")


@dataclass(frozen=True)
class ApprovalCommand:
    """A parsed Discord approval command."""

    decision: Decision
    outreach_id: str
    new_body: str | None = None


def _load_env() -> None:
    """Load `.env` if python-dotenv is available."""

    if load_dotenv is not None:
        load_dotenv()


def _now_iso() -> str:
    """Return a UTC timestamp for Supabase writes."""

    return datetime.now(timezone.utc).isoformat()


def _safe_log(action_type: str, status: str, message: str, result: dict[str, Any]) -> None:
    """Best-effort action logging."""

    try:
        logger.log("pitcher", action_type, status, message, result=result)
    except Exception as exc:  # pragma: no cover - local/no-credential path.
        print(f"Discord approval log skipped: {exc}")


def parse_command(content: str) -> ApprovalCommand | None:
    """Parse APPROVE, SKIP, or EDIT commands from Discord text."""

    match = COMMAND_RE.match(content.strip())
    if not match:
        return None

    verb = match.group(1).lower()
    outreach_id = match.group(2)
    tail = (match.group(3) or "").strip()
    if verb == "approve":
        return ApprovalCommand("approve", outreach_id)
    if verb == "skip":
        return ApprovalCommand("skip", outreach_id)
    if not tail:
        raise ValueError("EDIT requires a new body after the outreach id.")
    return ApprovalCommand("edit", outreach_id, tail)


def _insert_approval(command: ApprovalCommand, decided_by: str) -> None:
    """Write an approvals row for a Discord decision."""

    payload: dict[str, Any] = {
        "target_type": "outreach",
        "target_id": command.outreach_id,
        "decision": command.decision,
        "decided_at": _now_iso(),
        "decided_by": decided_by,
    }
    if command.decision == "edit":
        payload["edit_payload"] = {"body": command.new_body}
    get_client().table("approvals").insert(payload).execute()


def apply_command(command: ApprovalCommand, decided_by: str = "discord") -> dict[str, Any]:
    """Apply one parsed approval command to Supabase."""

    if command.decision == "approve":
        update_payload = {"status": "approved", "approved_at": _now_iso()}
    elif command.decision == "skip":
        update_payload = {"status": "skipped"}
    else:
        update_payload = {"status": "approved", "approved_at": _now_iso(), "body": command.new_body}

    response = get_client().table("outreach").update(update_payload).eq("id", command.outreach_id).execute()
    rows = getattr(response, "data", []) or []
    if not rows:
        raise RuntimeError(f"Outreach row not found for approval command: {command.outreach_id}")

    _insert_approval(command, decided_by)

    result = {"outreach_id": command.outreach_id, "decision": command.decision, "updated": True}
    _safe_log(
        "discord_approval",
        "succeeded",
        f"Discord {command.decision} applied for outreach {command.outreach_id}.",
        result,
    )
    return result


def _agents_running() -> str:
    """Check whether the unified agent process is alive."""

    pid_file = _LOGS_DIR / "all_claws.pid"
    if not pid_file.exists():
        return "unknown (no PID file)"
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
        return f"running (PID {pid})"
    except (ValueError, ProcessLookupError, PermissionError):
        return "not running"


def _gather_context() -> str:
    """Build a text snapshot of the full pipeline for the Nemotron prompt."""

    lines: list[str] = []
    lines.append(f"## Agents process: {_agents_running()}")

    try:
        counts = pipeline_counts()
        lines.append(
            "## Pipeline counts\n"
            f"- Total leads scouted: {counts['scouted']}\n"
            f"- Pending design: {counts['pending_design']}\n"
            f"- Pending pitch: {counts['pending_pitch']}\n"
            f"- Pitched: {counts['pitched']}\n"
            f"- Pending approval: {counts['pending_approval']}\n"
            f"- Unhandled inbound replies: {counts['unhandled_inbound']}"
        )
    except Exception as exc:
        lines.append(f"## Pipeline counts: unavailable ({exc})")

    try:
        actions = recent_actions_all(limit=3)
        by_claw: dict[str, list[str]] = {}
        for row in actions:
            claw = row.get("claw_name", "unknown")
            entry = f"[{row.get('status')}] {row.get('human_readable_log', '')} ({row.get('started_at', '')[:16]})"
            by_claw.setdefault(claw, []).append(entry)
        activity_lines = ["## Recent activity"]
        for claw in _CLAWS:
            entries = by_claw.get(claw, ["no recent actions"])
            activity_lines.append(f"**{claw}**: " + " | ".join(entries[:2]))
        lines.append("\n".join(activity_lines))
    except Exception as exc:
        lines.append(f"## Recent activity: unavailable ({exc})")

    for claw in _CLAWS:
        try:
            rows = recent_memory(claw, limit=5)  # type: ignore[arg-type]
            if rows:
                snippets = [r.get("pattern", "")[:100] for r in rows[:3]]
                lines.append(f"## {claw} memory\n" + "\n".join(f"- {s}" for s in snippets))
        except Exception:
            pass

    return "\n\n".join(lines)[:2000]


def _ask_nemotron(question: str, context: str) -> str:
    """Call Nemotron with pipeline context and return a plain text answer."""

    system = (
        "You are a helpful assistant for the Mainstreet autonomous sales team. "
        "Answer questions about the pipeline status concisely. "
        "Return JSON with a single key 'response' containing a plain text answer under 400 characters."
    )
    user = f"Pipeline context:\n{context}\n\nQuestion: {question}"
    result = nemotron_client.chat_json(system, user)
    return str(result.get("response", "I couldn't generate a response. Try again."))


async def handle_query(message: Any) -> None:
    """Answer a natural language pipeline question in Discord."""

    try:
        context = await asyncio.to_thread(_gather_context)
        answer = await asyncio.to_thread(_ask_nemotron, message.content.strip(), context)
        await message.reply(answer[:1900])
    except Exception as exc:
        await message.reply(f"Could not answer query: {exc}")


def fallback_instructions() -> str:
    """Return manual approval instructions when the Discord bot cannot run."""

    return (
        "Discord approval worker is not running. Set DISCORD_BOT_TOKEN and "
        "DISCORD_APPROVAL_CHANNEL_ID, then run `python -m workers.discord_bridge`. "
        "Manual commands: APPROVE <outreach_id>, SKIP <outreach_id>, "
        "EDIT <outreach_id> <new body>."
    )


def run_bot() -> int:
    """Start the Discord approval worker if bot configuration is available."""

    _load_env()
    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    channel_id = os.environ.get("DISCORD_APPROVAL_CHANNEL_ID", "").strip()
    if not token or not channel_id:
        print(fallback_instructions())
        return 0

    try:
        import discord
    except ImportError:
        print("The `discord.py` package is not installed. Run `pip install -r agents/requirements.txt`.")
        print(fallback_instructions())
        return 0

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    try:
        approval_channel_id = int(channel_id)
    except ValueError:
        print("DISCORD_APPROVAL_CHANNEL_ID must be a numeric Discord channel id.")
        print(fallback_instructions())
        return 0

    @client.event
    async def on_ready() -> None:  # type: ignore[no-untyped-def]
        print(f"Discord approval worker connected as {client.user}.")
        print(f"Listening for approval commands in channel id {approval_channel_id}.")

    @client.event
    async def on_message(message: Any) -> None:  # type: ignore[no-untyped-def]
        if message.author.bot or message.channel.id != approval_channel_id:
            return
        try:
            if PING_RE.match(message.content.strip()):
                await message.reply(
                    "NemoClaw approval worker is online. "
                    "Use `APPROVE <outreach_id>`, `SKIP <outreach_id>`, "
                    "or `EDIT <outreach_id> <new body>`. "
                    "You can also ask me anything about the pipeline in plain English."
                )
                return
            command = parse_command(message.content)
            if command is None:
                await handle_query(message)
                return
            result = apply_command(command, decided_by=str(message.author))
            await message.reply(f"Recorded {result['decision']} for outreach {result['outreach_id']}.")
        except Exception as exc:
            _safe_log("discord_approval", "failed", f"Discord approval command failed: {exc}", {"error": str(exc)})
            await message.reply(f"Could not apply approval command: {exc}")

    client.run(token)
    return 0


def main() -> int:
    """CLI entrypoint."""

    return run_bot()


if __name__ == "__main__":
    raise SystemExit(main())
