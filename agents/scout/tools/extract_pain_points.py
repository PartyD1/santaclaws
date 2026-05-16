"""Scout tool for extracting recurring customer complaints from reviews."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from agents.shared import nemotron_client
from agents.shared.logger import logger
from agents.shared.supabase_client import get_client


PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "scout_extract_pain.txt"


def _safe_log(action_type: str, status: str, message: str, lead_id: str | None, result: dict[str, Any]) -> None:
    """Best-effort action logging for local/no-credential paths."""

    try:
        logger.log("scout", action_type, status, message, lead_id=lead_id, result=result)
    except Exception as exc:  # pragma: no cover - local/no-credential path.
        print(f"Scout log skipped: {exc}")


def _fetch_lead(lead_id: UUID | str) -> dict[str, Any]:
    """Fetch one lead row from Supabase."""

    response = get_client().table("leads").select("*").eq("id", str(lead_id)).limit(1).execute()
    rows = getattr(response, "data", [])
    if not rows:
        raise ValueError(f"lead not found: {lead_id}")
    return rows[0]


def _lead_id(lead: dict[str, Any]) -> str | None:
    """Return a string lead id when present."""

    value = lead.get("id")
    return None if value is None else str(value)


def _reviews(lead: dict[str, Any]) -> list[str]:
    """Return normalized review texts from a lead row."""

    raw = lead.get("review_texts") or []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    return []


def _build_prompt(lead: dict[str, Any], reviews: list[str]) -> str:
    """Format the Scout pain extraction prompt."""

    template = PROMPT_PATH.read_text(encoding="utf-8")
    review_block = "\n".join(f"- {review}" for review in reviews[:10])
    return template.format(
        business_name=lead.get("business_name", "unknown business"),
        niche=lead.get("niche", "unknown niche"),
        city=lead.get("city", "unknown city"),
        google_rating=lead.get("google_rating"),
        review_count=lead.get("review_count", len(reviews)),
        reviews=review_block,
    )


def _parse_pain_points(payload: dict[str, Any]) -> list[str]:
    """Validate and trim Nemotron pain point output."""

    raw = payload.get("pain_points", [])
    if not isinstance(raw, list):
        return []
    points: list[str] = []
    for item in raw:
        text = str(item).strip()
        if text and text not in points:
            points.append(text)
        if len(points) == 3:
            break
    return points


def _update_lead(lead_id: str | None, pain_points: list[str]) -> None:
    """Persist pain points when a lead id is available."""

    if not lead_id:
        return
    try:
        get_client().table("leads").update({"top_review_pain_points": pain_points}).eq("id", lead_id).execute()
    except Exception as exc:  # pragma: no cover - local/no-credential path.
        print(f"Scout pain point update skipped: {exc}")


def run(lead: dict[str, Any] | UUID | str) -> list[str]:
    """Extract up to three recurring customer complaints from lead reviews."""

    lead_row = _fetch_lead(lead) if isinstance(lead, (UUID, str)) else lead
    lead_id = _lead_id(lead_row)
    review_texts = _reviews(lead_row)
    review_count = int(lead_row.get("review_count") or len(review_texts))

    if review_count < 5 or not review_texts:
        result = {"pain_points": [], "reason": "insufficient reviews"}
        _safe_log("extract_pain_points", "skipped", "found insufficient reviews for pain extraction.", lead_id, result)
        _update_lead(lead_id, [])
        return []

    prompt = _build_prompt(lead_row, review_texts)
    payload = nemotron_client.chat_json(
        system="Extract customer complaints for Scout. Return only valid JSON.",
        user=prompt,
        retries=1,
    )
    pain_points = _parse_pain_points(payload)
    _update_lead(lead_id, pain_points)
    _safe_log(
        "extract_pain_points",
        "succeeded",
        f"extracted {len(pain_points)} recurring customer complaints.",
        lead_id,
        {"pain_points": pain_points},
    )
    return pain_points
