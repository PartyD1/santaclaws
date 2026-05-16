"""Scout tool for scraping and inserting new leads."""

from __future__ import annotations

from typing import Any

from agents.integrations.apify_client import scrape_google_places
from agents.shared.logger import logger
from agents.shared.supabase_client import get_client, insert_leads


def _safe_log(action_type: str, status: str, message: str, result: dict[str, Any] | None = None) -> None:
    """Best-effort action logging that never hides the tool result."""

    try:
        logger.log("scout", action_type, status, message, result=result)
    except Exception as exc:  # pragma: no cover - local/no-credential path.
        print(f"Scout log skipped: {exc}")


def _first_email(item: dict[str, Any]) -> str | None:
    """Extract the first email Apify found, if any."""

    emails = item.get("emails")
    if isinstance(emails, list) and emails:
        first = emails[0]
        if isinstance(first, dict):
            return first.get("email") or first.get("value")
        return str(first)
    if isinstance(emails, str):
        return emails
    return item.get("email")


def _review_texts(item: dict[str, Any]) -> list[str]:
    """Normalize review text from common Apify output shapes."""

    raw_reviews = item.get("reviews") or item.get("reviewsItems") or item.get("placeReviews") or []
    texts: list[str] = []
    if isinstance(raw_reviews, list):
        for review in raw_reviews[:10]:
            if isinstance(review, dict):
                text = review.get("text") or review.get("reviewText") or review.get("content")
            else:
                text = str(review)
            if text:
                texts.append(str(text).strip())
    elif isinstance(raw_reviews, str):
        texts.append(raw_reviews.strip())
    return [text for text in texts if text]


def _lead_key(row: dict[str, Any]) -> tuple[str, str]:
    """Return the dedupe key for a lead row."""

    return (str(row.get("business_name") or "").strip().lower(), str(row.get("address") or "").strip().lower())


def _already_exists(business_name: str, address: str | None) -> bool:
    """Check Supabase for an existing lead by business name and address."""

    if not address:
        return False
    response = (
        get_client()
        .table("leads")
        .select("id")
        .eq("business_name", business_name)
        .eq("address", address)
        .limit(1)
        .execute()
    )
    return bool(getattr(response, "data", []))


def _to_lead_row(item: dict[str, Any], city: str, niche: str) -> dict[str, Any] | None:
    """Map one Apify place item into the Mainstreet `leads` schema."""

    business_name = item.get("title") or item.get("name") or item.get("businessName")
    if not business_name:
        return None

    review_texts = _review_texts(item)
    return {
        "business_name": str(business_name).strip(),
        "address": item.get("address"),
        "phone": item.get("phoneUnformatted") or item.get("phone") or item.get("phoneNumber"),
        "email": _first_email(item),
        "website": item.get("website"),
        "niche": niche,
        "city": city,
        "google_rating": item.get("totalScore") or item.get("rating"),
        "review_count": item.get("reviewsCount") or item.get("reviewCount") or len(review_texts),
        "review_texts": review_texts,
        "qualification_status": "pending",
    }


def run(city: str, niche: str, limit: int = 20) -> int:
    """Scrape Google Places through Apify, dedupe, and insert new leads."""

    if not city.strip():
        raise ValueError("city is required for scrape_leads.")
    if not niche.strip():
        raise ValueError("niche is required for scrape_leads.")

    raw_items = scrape_google_places(search_query=niche, location=city, max_results=limit)
    candidate_rows = [
        row for item in raw_items if (row := _to_lead_row(item, city=city, niche=niche)) is not None
    ]

    seen: set[tuple[str, str]] = set()
    new_rows: list[dict[str, Any]] = []
    skipped_existing = 0
    for row in candidate_rows:
        key = _lead_key(row)
        if key in seen:
            skipped_existing += 1
            continue
        seen.add(key)
        if _already_exists(row["business_name"], row.get("address")):
            skipped_existing += 1
            continue
        new_rows.append(row)

    inserted = insert_leads(new_rows)
    _safe_log(
        "scrape_batch",
        "succeeded",
        f"scraped {len(raw_items)} {niche} leads in {city}. Inserted {inserted}, skipped {skipped_existing}.",
        {"raw_count": len(raw_items), "inserted": inserted, "skipped_existing": skipped_existing},
    )

    for row in new_rows:
        _safe_log(
            "insert_lead",
            "succeeded",
            f"inserted {row['business_name']}.",
            {"business_name": row["business_name"], "address": row.get("address")},
        )

    return inserted
