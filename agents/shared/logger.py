"""Human-readable action logging for Mainstreet NemoClaw claws."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import TracebackType
from typing import Any
from uuid import UUID

from agents.shared.supabase_client import insert_action
from agents.shared.types import Action, ActionStatus, ClawName


CLAW_EMOJI: dict[str, str] = {
    "scout": "🔍",
    "designer": "🎨",
    "pitcher": "✉️",
    "closer": "📞",
}


class LoggerError(RuntimeError):
    """Raised when the action logger is used with invalid inputs."""


def _now_iso() -> str:
    """Return a UTC timestamp suitable for Supabase timestamptz columns."""

    return datetime.now(timezone.utc).isoformat()


def _format_log(claw: str, log_text: str) -> str:
    """Prefix a dashboard log line with the claw emoji and name."""

    text = log_text.strip()
    if not text:
        raise LoggerError("log_text cannot be empty.")

    emoji = CLAW_EMOJI.get(claw, "•")
    claw_name = claw.capitalize()

    if text.startswith(emoji):
        return text
    if text.lower().startswith(claw.lower()):
        return f"{emoji} {text}"
    return f"{emoji} {claw_name} {text}"


def log(
    claw: ClawName,
    action_type: str,
    status: ActionStatus,
    log_text: str,
    lead_id: UUID | str | None = None,
    result: dict[str, Any] | None = None,
) -> Action:
    """Insert one human-readable action row.

    Args:
        claw: NemoClaw claw name: `scout`, `designer`, `pitcher`, or `closer`.
        action_type: Short machine-readable action type.
        status: Action status for the dashboard feed.
        log_text: Human-readable sentence. Emoji and claw name are added if absent.
        lead_id: Optional related lead UUID.
        result: Optional structured result payload.

    Returns:
        The inserted Action dataclass.
    """

    timestamp = _now_iso()
    return insert_action(
        claw_name=claw,
        action_type=action_type,
        status=status,
        human_readable_log=_format_log(claw, log_text),
        lead_id=lead_id,
        result_json=result,
        started_at=timestamp,
        finished_at=timestamp,
    )


@dataclass
class ActionContext:
    """Context manager used by tools to write one action row at exit."""

    claw: ClawName
    action_type: str
    lead_id: UUID | str | None = None
    started_at: str = field(default_factory=_now_iso)
    log_text: str | None = None
    result: dict[str, Any] | None = None
    status: ActionStatus = "succeeded"
    inserted: Action | None = None

    def __enter__(self) -> "ActionContext":
        """Start an action context."""

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        """Write the final action row and re-raise any original exception."""

        finished_at = _now_iso()
        status: ActionStatus = self.status
        result = self.result
        log_text = self.log_text

        if exc is not None:
            status = "failed"
            if result is None:
                result = {"error": str(exc), "error_type": exc.__class__.__name__}
            if log_text is None:
                log_text = f"{self.action_type} failed: {exc}"

        if log_text is None:
            log_text = f"{self.action_type} {status}"

        self.inserted = insert_action(
            claw_name=self.claw,
            action_type=self.action_type,
            status=status,
            human_readable_log=_format_log(self.claw, log_text),
            lead_id=self.lead_id,
            result_json=result,
            started_at=self.started_at,
            finished_at=finished_at,
        )
        return False

    def set_log(self, log_text: str) -> None:
        """Set the human-readable dashboard log line."""

        self.log_text = log_text

    def set_result(self, result: dict[str, Any]) -> None:
        """Set the structured JSON result payload."""

        self.result = result

    def set_status(self, status: ActionStatus) -> None:
        """Override the final status for skipped or failed non-exception paths."""

        self.status = status


def action(claw: ClawName, action_type: str, lead_id: UUID | str | None = None) -> ActionContext:
    """Create an action logging context manager."""

    return ActionContext(claw=claw, action_type=action_type, lead_id=lead_id)


class _Logger:
    """Small object API for `from agents.shared.logger import logger`."""

    def log(
        self,
        claw: ClawName,
        action_type: str,
        status: ActionStatus,
        log_text: str,
        lead_id: UUID | str | None = None,
        result: dict[str, Any] | None = None,
    ) -> Action:
        """Insert one human-readable action row."""

        return log(claw, action_type, status, log_text, lead_id=lead_id, result=result)

    def action(self, claw: ClawName, action_type: str, lead_id: UUID | str | None = None) -> ActionContext:
        """Create an action logging context manager."""

        return action(claw, action_type, lead_id=lead_id)


logger = _Logger()
