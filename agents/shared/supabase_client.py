"""Direct Supabase helpers for Mainstreet NemoClaw claws.

The database is the queue for this hackathon build. Helpers here stay thin:
direct Supabase table calls, simple validation, and no ORM/repository layer.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import UUID

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency validation catches this.
    load_dotenv = None  # type: ignore[assignment]

from agents.shared.types import (
    Action,
    ActionStatus,
    Classification,
    ClawName,
    Inbound,
    Lead,
)


VALID_CLAWS = {"scout", "designer", "pitcher", "closer"}
DESIGNER_QUAL_STATUSES = ["qualified_for_mockup", "qualified_for_rebuild"]
DEFAULT_SCOUT_NICHES = [
    "restaurants",
    "cafes",
    "hair salons",
    "barbers",
    "fitness centers",
    "spas",
    "house cleaners",
    "contractors",
]
DEFAULT_TARGET = {
    "niche": DEFAULT_SCOUT_NICHES[0],
    "niches": DEFAULT_SCOUT_NICHES,
    "city": "Santa Cruz",
    "state": "CA",
}


class SupabaseClientError(RuntimeError):
    """Base exception for Supabase helper failures."""


class SupabaseConfigError(SupabaseClientError):
    """Raised when required Supabase environment configuration is missing."""


class SupabaseDataError(SupabaseClientError):
    """Raised when expected Supabase data is missing or malformed."""


def _load_env() -> None:
    """Load local `.env` values when python-dotenv is installed."""

    if load_dotenv is not None:
        load_dotenv()


def _env(name: str, required: bool = True) -> str | None:
    """Read an environment variable with a clear error for missing values."""

    _load_env()
    value = os.environ.get(name, "").strip()
    if required and not value:
        raise SupabaseConfigError(f"{name} is required for Supabase access.")
    return value or None


@lru_cache(maxsize=2)
def get_client(use_service_key: bool = True) -> Any:
    """Return a cached Supabase client.

    Args:
        use_service_key: Use `SUPABASE_SERVICE_KEY` for agent writes. Set to
            `False` only for dashboard-like anon reads.

    Raises:
        SupabaseConfigError: If credentials or the `supabase` package are missing.
    """

    try:
        from supabase import create_client
    except ImportError as exc:  # pragma: no cover - local setup issue.
        raise SupabaseConfigError(
            "The `supabase` package is not installed. Run `pip install -r agents/requirements.txt`."
        ) from exc

    url = _env("SUPABASE_URL")
    anon_key = _env("SUPABASE_ANON_KEY", required=False)
    service_key = _env("SUPABASE_SERVICE_KEY", required=False)
    key = service_key if use_service_key else anon_key

    if not key:
        wanted = "SUPABASE_SERVICE_KEY" if use_service_key else "SUPABASE_ANON_KEY"
        raise SupabaseConfigError(f"{wanted} is required for this Supabase helper.")

    return create_client(url, key)


def _data(response: Any) -> list[dict[str, Any]]:
    """Normalize Supabase response data to a list of rows."""

    rows = getattr(response, "data", None)
    if rows is None:
        raise SupabaseDataError("Supabase response did not include data.")
    if isinstance(rows, dict):
        return [rows]
    if isinstance(rows, list):
        return rows
    raise SupabaseDataError(f"Unexpected Supabase data type: {type(rows).__name__}.")


def _first(response: Any) -> dict[str, Any] | None:
    """Return the first Supabase row from a response."""

    rows = _data(response)
    return rows[0] if rows else None


def _now_iso() -> str:
    """Return a UTC timestamp that Supabase accepts for timestamptz columns."""

    return datetime.now(timezone.utc).isoformat()


def _uuid_string(value: UUID | str) -> str:
    """Normalize UUID-like inputs for Supabase filters."""

    return str(value)


def next_scout_target() -> dict[str, Any]:
    """Read the current Scout target from the `config` table.

    Returns the default Santa Cruz local-services target if the row has not
    been seeded yet, keeping the demo path recoverable.
    """

    response = get_client().table("config").select("value").eq("key", "target").limit(1).execute()
    row = _first(response)
    if not row:
        return dict(DEFAULT_TARGET)
    value = row.get("value")
    if not isinstance(value, dict):
        raise SupabaseDataError("config.target must be a JSON object.")
    return value


def insert_leads(rows: list[dict[str, Any]]) -> int:
    """Insert lead rows and return the number accepted by Supabase."""

    if not rows:
        return 0
    for index, row in enumerate(rows):
        missing = {"business_name", "niche", "city"} - set(row)
        if missing:
            raise SupabaseDataError(f"lead row {index} missing required fields: {sorted(missing)}")

    response = get_client().table("leads").insert(rows).execute()
    return len(_data(response))


def next_designer_lead() -> Lead | None:
    """Return the oldest email-ready lead for the Designer claw."""

    response = (
        get_client()
        .table("leads")
        .select("*")
        .in_("qualification_status", DESIGNER_QUAL_STATUSES)
        .eq("worked_by_designer", False)
        .eq("do_not_contact", False)
        .order("scraped_at")
        .limit(25)
        .execute()
    )
    for row in _data(response):
        if str(row.get("email") or "").strip():
            return Lead.from_row(row)
    return None


def claim_lead_for_designer(lead_id: UUID | str) -> bool:
    """Claim a lead for Designer with an update guard.

    Returns `True` only if this call changed the row from unclaimed to claimed.
    """

    response = (
        get_client()
        .table("leads")
        .update({"worked_by_designer": True, "updated_at": _now_iso()})
        .eq("id", _uuid_string(lead_id))
        .eq("worked_by_designer", False)
        .execute()
    )
    return bool(_data(response))


def next_pitcher_lead() -> dict[str, Any] | None:
    """Return the next Pitcher lead plus its chosen mockup when available.

    Pitcher can only create useful outreach for leads that have a recipient,
    so scan a small queue window and skip Designer-completed rows without an
    email address.
    """

    lead_response = (
        get_client()
        .table("leads")
        .select("*")
        .eq("worked_by_designer", True)
        .eq("worked_by_pitcher", False)
        .eq("do_not_contact", False)
        .order("scraped_at")
        .limit(25)
        .execute()
    )
    lead_rows = _data(lead_response)
    if not lead_rows:
        return None

    for lead_row in lead_rows:
        if not str(lead_row.get("email") or "").strip():
            continue

        site_response = (
            get_client()
            .table("generated_sites")
            .select("*")
            .eq("lead_id", lead_row["id"])
            .eq("is_chosen_winner", True)
            .order("generated_at", desc=True)
            .limit(1)
            .execute()
        )
        site_row = _first(site_response)
        if not site_row:
            fallback_response = (
                get_client()
                .table("generated_sites")
                .select("*")
                .eq("lead_id", lead_row["id"])
                .order("generated_at", desc=True)
                .limit(1)
                .execute()
            )
            site_row = _first(fallback_response)

        if site_row:
            return {"lead": Lead.from_row(lead_row), "mockup": site_row}

    return None


def claim_lead_for_pitcher(lead_id: UUID | str) -> bool:
    """Claim a lead for Pitcher with an update guard."""

    response = (
        get_client()
        .table("leads")
        .update({"worked_by_pitcher": True, "updated_at": _now_iso()})
        .eq("id", _uuid_string(lead_id))
        .eq("worked_by_pitcher", False)
        .execute()
    )
    return bool(_data(response))


def next_inbound() -> Inbound | None:
    """Return the oldest unhandled inbound reply/call."""

    response = (
        get_client()
        .table("inbound")
        .select("*")
        .is_("handled_at", "null")
        .order("received_at")
        .limit(1)
        .execute()
    )
    row = _first(response)
    return Inbound.from_row(row) if row else None


def mark_inbound_handled(
    inbound_id: UUID | str,
    classification: Classification | None,
    handled_by: str,
) -> bool:
    """Mark an inbound row handled by a claw or human."""

    if not handled_by:
        raise SupabaseDataError("handled_by is required when marking inbound handled.")

    payload: dict[str, Any] = {"handled_at": _now_iso(), "handled_by": handled_by}
    if classification is not None:
        payload["classification"] = classification

    response = (
        get_client()
        .table("inbound")
        .update(payload)
        .eq("id", _uuid_string(inbound_id))
        .is_("handled_at", "null")
        .execute()
    )
    return bool(_data(response))


def insert_action(
    claw_name: ClawName,
    action_type: str,
    status: ActionStatus,
    human_readable_log: str,
    lead_id: UUID | str | None = None,
    result_json: dict[str, Any] | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> Action:
    """Insert an action-log row and return it as an Action dataclass."""

    if claw_name not in VALID_CLAWS:
        raise SupabaseDataError(f"Invalid claw_name: {claw_name}")
    if not action_type:
        raise SupabaseDataError("action_type is required for insert_action.")
    if not human_readable_log:
        raise SupabaseDataError("human_readable_log is required for insert_action.")

    payload: dict[str, Any] = {
        "claw_name": claw_name,
        "action_type": action_type,
        "status": status,
        "human_readable_log": human_readable_log,
        "started_at": started_at or _now_iso(),
        "finished_at": finished_at,
        "result_json": result_json,
    }
    if lead_id is not None:
        payload["lead_id"] = _uuid_string(lead_id)

    response = get_client().table("actions").insert(payload).execute()
    row = _first(response)
    if not row:
        raise SupabaseDataError("insert_action did not return an inserted row.")
    return Action.from_row(row)


def _memory_path(claw_name: str) -> Path:
    """Return the MEMORY.md path for a NemoClaw claw."""

    if claw_name not in VALID_CLAWS:
        raise SupabaseDataError(f"Unknown claw memory requested: {claw_name}")
    return Path(__file__).resolve().parents[1] / claw_name / "MEMORY.md"


def read_memory(claw_name: ClawName) -> str:
    """Read durable claw memory from Supabase, falling back to MEMORY.md."""

    db_memory = ""
    try:
        rows = recent_memory(claw_name, limit=30)
        if rows:
            db_memory = "\n".join(f"- {row['created_at']} - {row['pattern']}" for row in reversed(rows))
    except Exception:
        db_memory = ""

    path = _memory_path(claw_name)
    file_memory = path.read_text(encoding="utf-8") if path.exists() else ""

    if db_memory and file_memory.strip():
        return f"{db_memory}\n\nLocal compatibility cache:\n{file_memory}"
    return db_memory or file_memory


def append_memory(claw_name: ClawName, pattern: str) -> None:
    """Append one observation to a claw's MEMORY.md file."""

    if not pattern.strip():
        return
    path = _memory_path(claw_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n- {timestamp} - {pattern.strip()}\n")


def insert_memory(
    claw_name: ClawName,
    pattern: str,
    source: str = "nemotron",
    heartbeat_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist one claw memory observation to Supabase."""

    if claw_name not in VALID_CLAWS:
        raise SupabaseDataError(f"Invalid claw_name for memory: {claw_name}")
    pattern = pattern.strip()
    if not pattern:
        raise SupabaseDataError("pattern is required for memory insert.")

    payload = {
        "claw_name": claw_name,
        "pattern": pattern,
        "source": source,
        "heartbeat_summary": heartbeat_summary,
    }
    response = get_client().table("agent_memory").insert(payload).execute()
    row = _first(response)
    if not row:
        raise SupabaseDataError("insert_memory did not return an inserted row.")
    return row


def pipeline_counts() -> dict[str, int]:
    """Return lead counts at each pipeline stage for bot and dashboard queries."""

    db = get_client()

    def _count(table: str, filters: list) -> int:
        try:
            q = db.table(table).select("id", count="exact")
            for method, *args in filters:
                q = getattr(q, method)(*args)
            return q.execute().count or 0
        except Exception:
            return 0

    return {
        "scouted": _count("leads", []),
        "pending_design": _count("leads", [
            ("in_", "qualification_status", ["qualified_for_mockup", "qualified_for_rebuild"]),
            ("eq", "worked_by_designer", False),
            ("eq", "do_not_contact", False),
        ]),
        "pending_pitch": _count("leads", [
            ("eq", "worked_by_designer", True),
            ("eq", "worked_by_pitcher", False),
            ("eq", "do_not_contact", False),
        ]),
        "pitched": _count("leads", [("eq", "worked_by_pitcher", True)]),
        "pending_approval": _count("outreach", [("eq", "status", "pending_approval")]),
        "unhandled_inbound": _count("inbound", [("is_", "handled_at", "null")]),
    }


def recent_actions_all(limit: int = 4) -> list[dict[str, Any]]:
    """Return the most recent actions across all claws, newest first."""

    response = (
        get_client()
        .table("actions")
        .select("claw_name, action_type, status, human_readable_log, started_at")
        .order("started_at", desc=True)
        .limit(limit * 4)
        .execute()
    )
    return _data(response)


def recent_memory(claw_name: ClawName, limit: int = 30) -> list[dict[str, Any]]:
    """Return recent durable memory rows for one claw."""

    if claw_name not in VALID_CLAWS:
        raise SupabaseDataError(f"Invalid claw_name for memory: {claw_name}")
    response = (
        get_client()
        .table("agent_memory")
        .select("created_at, pattern, source")
        .eq("claw_name", claw_name)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return _data(response)
