"""Insert one unhandled inbound row for testing the Closer claw."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency validation catches this.
    load_dotenv = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.shared.supabase_client import get_client


FIXTURES = {
    "interested": "Thanks for sending this over. I am interested. When can we schedule a quick call?",
    "question": "Thanks. What would this cost after the mockup, and how long would it take?",
    "objection": "We already have someone helping with our website, so I am not sure we need this right now.",
    "not_interested": "No thanks, please stop emailing us.",
    "spam": "You won a crypto prize. Click here to claim it now.",
    "uncertain": "Thanks for the note. I will look at it.",
}


def _load_env() -> None:
    """Load `.env` values if python-dotenv is available."""

    if load_dotenv is not None:
        load_dotenv()


def _rows(response: Any) -> list[dict[str, Any]]:
    """Normalize Supabase response rows."""

    data = getattr(response, "data", []) or []
    return data if isinstance(data, list) else [data]


def _first(response: Any) -> dict[str, Any] | None:
    """Return the first row from a Supabase response."""

    rows = _rows(response)
    return rows[0] if rows else None


def _parse_supabase_dt(value: Any) -> datetime | None:
    """Parse a Supabase timestamptz value."""

    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _received_at(make_next: bool) -> str:
    """Return a received_at timestamp that lets this test row run next."""

    now = datetime.now(timezone.utc)
    if not make_next:
        return now.isoformat()

    oldest = _first(
        get_client()
        .table("inbound")
        .select("received_at")
        .is_("handled_at", "null")
        .order("received_at")
        .limit(1)
        .execute()
    )
    oldest_at = _parse_supabase_dt((oldest or {}).get("received_at"))
    if oldest_at is None:
        return now.isoformat()
    return (oldest_at - timedelta(seconds=1)).isoformat()


def _classification_from_args(args: argparse.Namespace) -> str:
    """Return the requested fixture key."""

    for key in FIXTURES:
        if getattr(args, key):
            return key
    return "interested"


def insert_test_inbound(args: argparse.Namespace) -> dict[str, Any]:
    """Insert one fresh unhandled inbound row."""

    _load_env()
    classification = _classification_from_args(args)
    payload: dict[str, Any] = {
        "channel": "email",
        "from_address": args.from_address,
        "raw_content": args.body or FIXTURES[classification],
        "classification": None,
        "classification_confidence": None,
        "classification_key_phrase": None,
        "received_at": _received_at(make_next=not args.no_prioritize),
        "handled_at": None,
        "handled_by": None,
    }
    if args.lead_id:
        payload["lead_id"] = args.lead_id

    row = _first(get_client().table("inbound").insert(payload).select("*").execute())
    if not row:
        raise RuntimeError("Supabase did not return the inserted inbound row.")
    row["_expected_fixture"] = classification
    return row


def main() -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description="Insert a Closer test inbound row.")
    group = parser.add_mutually_exclusive_group()
    for key in FIXTURES:
        group.add_argument(f"--{key.replace('_', '-')}", action="store_true", help=f"Insert a {key} reply.")
    parser.add_argument("--lead-id", help="Optional existing lead UUID to attach to the inbound row.")
    parser.add_argument("--from-address", default="closer-demo@example.com", help="Sender address for the test row.")
    parser.add_argument("--body", help="Override the fixture body.")
    parser.add_argument(
        "--no-prioritize",
        action="store_true",
        help="Use the current timestamp instead of placing this test row at the front of the unhandled queue.",
    )
    args = parser.parse_args()

    try:
        row = insert_test_inbound(args)
    except Exception as exc:
        print(f"Closer demo inbound insert failed: {exc}")
        return 1

    print("Inserted Closer demo inbound row.")
    print(f"  id: {row.get('id')}")
    print(f"  expected_fixture: {row.get('_expected_fixture')}")
    print(f"  lead_id: {row.get('lead_id') or 'none'}")
    print(f"  received_at: {row.get('received_at')}")
    print("Run: .\\agents\\.venv\\Scripts\\python.exe -m agents.scripts.openclaw_run closer --once")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
