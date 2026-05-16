"""Minimal Discord approval worker for Mainstreet NemoClaw."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency validation catches this.
    load_dotenv = None  # type: ignore[assignment]

from agents.shared.logger import logger
from agents.shared.supabase_client import get_client


Decision = Literal["approve", "skip", "edit"]
COMMAND_RE = re.compile(r"^\s*(APPROVE|SKIP|EDIT)\s+([0-9a-fA-F-]{32,36})(?:\s+([\s\S]+))?\s*$", re.IGNORECASE)
PING_RE = re.compile(r"^\s*!?(PING|HELP)\s*$", re.IGNORECASE)


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
                    "or `EDIT <outreach_id> <new body>`."
                )
                return
            command = parse_command(message.content)
            if command is None:
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
