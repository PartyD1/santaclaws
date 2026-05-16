"""Seed obvious demo fallback data for the Mainstreet NemoClaw dashboard."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency validation catches this.
    load_dotenv = None  # type: ignore[assignment]

from agents.shared.supabase_client import get_client


DEMO_PREFIX = "DEMO - "


def _load_env() -> None:
    """Load `.env` values if python-dotenv is installed."""

    if load_dotenv is not None:
        load_dotenv()


def _now() -> datetime:
    """Return the current UTC time."""

    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    """Return an ISO timestamp for Supabase."""

    return dt.isoformat()


def _rows(response: Any) -> list[dict[str, Any]]:
    """Normalize Supabase response rows."""

    data = getattr(response, "data", []) or []
    return data if isinstance(data, list) else [data]


def _first(response: Any) -> dict[str, Any] | None:
    """Return the first row from a Supabase response."""

    rows = _rows(response)
    return rows[0] if rows else None


DEMO_LEADS: list[dict[str, Any]] = [
    {
        "business_name": f"{DEMO_PREFIX}Pacific Coast Auto Repair",
        "address": "214 Front St, Santa Cruz, CA",
        "phone": "(831) 555-0184",
        "email": "owner+pacific-demo@example.com",
        "website": "http://pacificcoastautorepair.example.com",
        "niche": "auto repair",
        "city": "Santa Cruz",
        "google_rating": 4.2,
        "review_count": 86,
        "review_texts": [
            "Great mechanics, but I could not find prices or request an appointment online.",
            "They fixed my brakes fast. The website looks old on my phone.",
        ],
        "top_review_pain_points": ["hard to book online", "mobile website feels dated"],
        "website_score": 3,
        "website_score_reasons": ["HTTP only", "weak mobile layout", "no online booking CTA"],
        "qualification_status": "qualified_for_rebuild",
        "qualification_reason": "demo fallback: weak website and clear booking friction",
        "worked_by_designer": True,
        "worked_by_pitcher": True,
    },
    {
        "business_name": f"{DEMO_PREFIX}Cruz County Brake & Tire",
        "address": "905 Soquel Ave, Santa Cruz, CA",
        "phone": "(831) 555-0138",
        "email": "manager+brake-demo@example.com",
        "website": None,
        "niche": "auto repair",
        "city": "Santa Cruz",
        "google_rating": 4.6,
        "review_count": 141,
        "review_texts": [
            "Honest tire shop. I wish they had a website with hours and services.",
            "Phone line gets busy, but the work is solid.",
        ],
        "top_review_pain_points": ["missing website", "phone line gets busy"],
        "website_score": 0,
        "website_score_reasons": ["no website"],
        "qualification_status": "qualified_for_mockup",
        "qualification_reason": "demo fallback: no website",
        "worked_by_designer": True,
        "worked_by_pitcher": True,
    },
    {
        "business_name": f"{DEMO_PREFIX}Harbor Light Motors",
        "address": "77 Mission St, Santa Cruz, CA",
        "phone": "(831) 555-0199",
        "email": "hello+harbor-demo@example.com",
        "website": "https://harborlightmotors.example.com",
        "niche": "auto repair",
        "city": "Santa Cruz",
        "google_rating": 3.9,
        "review_count": 58,
        "review_texts": [
            "Friendly team, but I waited a long time for a quote.",
            "The site does not say whether they do diagnostics.",
        ],
        "top_review_pain_points": ["slow quote follow-up", "unclear services"],
        "website_score": 5,
        "website_score_reasons": ["thin service copy", "unclear CTA"],
        "qualification_status": "qualified_for_rebuild",
        "qualification_reason": "demo fallback: weak service clarity",
        "worked_by_designer": True,
        "worked_by_pitcher": True,
    },
]


INBOUND_BY_BUSINESS = {
    f"{DEMO_PREFIX}Pacific Coast Auto Repair": (
        "interested",
        "This looks useful. Could you send a couple times next week to talk about the mockup?",
    ),
    f"{DEMO_PREFIX}Cruz County Brake & Tire": (
        "has_question",
        "Do you build the site too, or is this just a design preview?",
    ),
    f"{DEMO_PREFIX}Harbor Light Motors": (
        "not_interested",
        "Thanks, but please take us off your list.",
    ),
}


def _find_lead(client: Any, business_name: str) -> dict[str, Any] | None:
    """Find one demo lead by exact business name."""

    response = client.table("leads").select("*").eq("business_name", business_name).limit(1).execute()
    return _first(response)


def _insert_lead(client: Any, payload: dict[str, Any]) -> dict[str, Any]:
    """Insert a lead if it does not already exist."""

    existing = _find_lead(client, str(payload["business_name"]))
    if existing:
        return existing
    response = client.table("leads").insert(payload).execute()
    row = _first(response)
    if not row:
        raise RuntimeError(f"Could not insert demo lead {payload['business_name']}.")
    return row


def _has_related(client: Any, table: str, lead_id: str) -> bool:
    """Return whether a related demo row already exists."""

    response = client.table(table).select("id").eq("lead_id", lead_id).limit(1).execute()
    return bool(_rows(response))


def _public_url(lead: dict[str, Any]) -> str:
    """Return a stable demo mockup URL."""

    slug = str(lead["business_name"]).replace(DEMO_PREFIX, "").lower()
    slug = "-".join(part for part in "".join(ch if ch.isalnum() else "-" for ch in slug).split("-") if part)
    return f"https://demo.nemoclaw.local/{slug}"


def _seed_generated_site(client: Any, lead: dict[str, Any]) -> None:
    """Create a chosen mockup row for one demo lead."""

    lead_id = str(lead["id"])
    if _has_related(client, "generated_sites", lead_id):
        return
    name = str(lead["business_name"]).replace(DEMO_PREFIX, "")
    html = (
        "<!doctype html><html><head><title>"
        f"{name}</title></head><body><main><h1>{name}</h1>"
        "<p>Demo NemoClaw mockup focused on fast booking and trustworthy local service.</p>"
        "<a href=\"mailto:demo@example.com\">Request service</a></main></body></html>"
    )
    client.table("generated_sites").insert(
        {
            "lead_id": lead_id,
            "variant": "clean_modern",
            "vercel_url": _public_url(lead),
            "html_content": html,
            "self_critique_score": 8.4,
            "self_critique_iterations": 2,
            "critique_issues": ["demo row: verify real brand photos before sending"],
            "is_chosen_winner": True,
            "pick_reasoning": "Demo fallback winner with clear appointment CTA.",
        }
    ).execute()


def _seed_outreach(client: Any, lead: dict[str, Any]) -> None:
    """Create a demo outreach row for one lead."""

    lead_id = str(lead["id"])
    if _has_related(client, "outreach", lead_id):
        return
    name = str(lead["business_name"]).replace(DEMO_PREFIX, "")
    client.table("outreach").insert(
        {
            "lead_id": lead_id,
            "to_address": lead.get("email"),
            "angle": "specific_pain",
            "subject": f"Quick mockup for {name}",
            "body": (
                f"Hi {name} team - I noticed customers mention booking friction, "
                "so I made a quick website mockup with a clearer appointment path."
            ),
            "critique_score": 8.1,
            "runner_up_variants": [
                {"angle": "curiosity", "subject": "A small idea for your site", "critique": {"overall_score": 7.4}}
            ],
            "status": "sent",
            "drafted_at": _iso(_now() - timedelta(hours=5)),
            "approved_at": _iso(_now() - timedelta(hours=4, minutes=50)),
            "sent_at": _iso(_now() - timedelta(hours=4, minutes=45)),
            "resend_message_id": f"demo-{lead_id[:8]}",
        }
    ).execute()


def _seed_inbound(client: Any, lead: dict[str, Any]) -> dict[str, Any] | None:
    """Create one demo inbound reply for the lead."""

    lead_id = str(lead["id"])
    if _has_related(client, "inbound", lead_id):
        return None
    classification, raw_content = INBOUND_BY_BUSINESS[str(lead["business_name"])]
    response = client.table("inbound").insert(
        {
            "lead_id": lead_id,
            "channel": "email",
            "raw_content": raw_content,
            "from_address": lead.get("email"),
            "classification": None,
            "classification_confidence": None,
            "classification_key_phrase": None,
            "received_at": _iso(_now() - timedelta(minutes=25)),
        }
    ).execute()
    row = _first(response)
    print(f"Seeded {classification} inbound for {lead['business_name']}.")
    return row


def _seed_meeting(client: Any, lead: dict[str, Any], inbound: dict[str, Any] | None) -> None:
    """Create one booked meeting for the first demo lead."""

    if not str(lead["business_name"]).endswith("Pacific Coast Auto Repair"):
        return
    lead_id = str(lead["id"])
    if _has_related(client, "meetings", lead_id):
        return
    client.table("meetings").insert(
        {
            "lead_id": lead_id,
            "inbound_id": None if inbound is None else inbound.get("id"),
            "scheduled_for": _iso(_now() + timedelta(days=2, hours=2)),
            "google_event_id": f"demo-gcal-{lead_id[:8]}",
            "status": "booked",
            "attendee_email": lead.get("email"),
        }
    ).execute()


def _seed_actions(client: Any, lead: dict[str, Any]) -> None:
    """Create readable demo action rows for the activity feed."""

    lead_id = str(lead["id"])
    existing = client.table("actions").select("id").eq("lead_id", lead_id).eq("action_type", "demo_seed").limit(1).execute()
    if _rows(existing):
        return
    for claw_name, log_text in [
        ("scout", "Demo seed: Scout qualified this lead for NemoClaw fallback data."),
        ("designer", "Demo seed: Designer produced a chosen mockup."),
        ("pitcher", "Demo seed: Pitcher sent a short outreach email."),
        ("closer", "Demo seed: Closer has an inbound reply ready for review."),
    ]:
        client.table("actions").insert(
            {
                "claw_name": claw_name,
                "lead_id": lead_id,
                "action_type": "demo_seed",
                "status": "succeeded",
                "human_readable_log": log_text,
                "result_json": {"demo": True},
                "started_at": _iso(_now() - timedelta(minutes=10)),
                "finished_at": _iso(_now() - timedelta(minutes=9)),
            }
        ).execute()


def clear_demo_data(client: Any) -> int:
    """Delete demo rows identified by exact demo lead names."""

    leads = []
    for payload in DEMO_LEADS:
        row = _find_lead(client, str(payload["business_name"]))
        if row:
            leads.append(row)

    for lead in leads:
        lead_id = str(lead["id"])
        for table in ["meetings", "inbound", "outreach", "generated_sites", "actions"]:
            client.table(table).delete().eq("lead_id", lead_id).execute()
        client.table("leads").delete().eq("id", lead_id).execute()

    return len(leads)


def seed_demo_data() -> dict[str, int]:
    """Seed demo leads and related rows."""

    _load_env()
    client = get_client()
    counts = {"leads": 0, "generated_sites": 0, "outreach": 0, "inbound": 0, "meetings": 0}
    for payload in DEMO_LEADS:
        before = _find_lead(client, str(payload["business_name"]))
        lead = _insert_lead(client, payload)
        if before is None:
            counts["leads"] += 1

        had_site = _has_related(client, "generated_sites", str(lead["id"]))
        _seed_generated_site(client, lead)
        counts["generated_sites"] += 0 if had_site else 1

        had_outreach = _has_related(client, "outreach", str(lead["id"]))
        _seed_outreach(client, lead)
        counts["outreach"] += 0 if had_outreach else 1

        had_inbound = _has_related(client, "inbound", str(lead["id"]))
        inbound = _seed_inbound(client, lead)
        counts["inbound"] += 0 if had_inbound else 1

        had_meeting = _has_related(client, "meetings", str(lead["id"]))
        _seed_meeting(client, lead, inbound)
        if not had_meeting and str(lead["business_name"]).endswith("Pacific Coast Auto Repair"):
            counts["meetings"] += 1

        _seed_actions(client, lead)

    return counts


def main() -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description="Seed or clear Mainstreet NemoClaw demo fallback data.")
    parser.add_argument("--clear", action="store_true", help="Remove demo rows and exit.")
    args = parser.parse_args()

    _load_env()
    try:
        client = get_client()
        if args.clear:
            removed = clear_demo_data(client)
            print(f"Cleared demo data for {removed} lead(s).")
            return 0
        counts = seed_demo_data()
        print(f"Seeded demo data: {counts}")
        return 0
    except Exception as exc:
        print(f"Demo seed failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
