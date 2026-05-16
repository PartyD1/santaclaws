"""Pitcher tool for generating short outreach email drafts with Nemotron."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from agents.shared import nemotron_client
from agents.shared.logger import logger


PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"
PROMPT_BY_ANGLE = {
    "specific_pain": "pitcher_generate_pain.txt",
    "competitor_comparison": "pitcher_generate_compare.txt",
    "social_proof": "pitcher_generate_social.txt",
    "curiosity": "pitcher_generate_curiosity.txt",
}


def _lead_id(lead: dict[str, Any]) -> str | None:
    """Return a string lead id when present."""

    value = lead.get("id")
    return None if value is None else str(value)


def _safe_log(
    action_type: str,
    status: str,
    message: str,
    lead_id: str | None,
    result: dict[str, Any],
) -> None:
    """Best-effort action logging."""

    try:
        logger.log("pitcher", action_type, status, message, lead_id=lead_id, result=result)
    except Exception as exc:  # pragma: no cover - local/no-credential path.
        print(f"Pitcher log skipped: {exc}")


def _sentences(text: str) -> list[str]:
    """Split text into rough sentence chunks for simple length validation."""

    return [part.strip() for part in re.split(r"[.!?]+", text) if part.strip()]


def _trim_sentences(text: str, limit: int = 5) -> str:
    """Trim long model output to the first few sentences for demo reliability."""

    matches = re.findall(r"[^.!?]+[.!?]?", text)
    trimmed = "".join(match.strip() + " " for match in matches[:limit]).strip()
    return trimmed or text.strip()


def _business_salutation(body: str, business_name: str) -> str:
    """Force the opening greeting to use the business name, not an owner name."""

    business_name = business_name.strip() or "there"
    greeting = f"Hi {business_name},"
    cleaned = body.strip()
    replaced = re.sub(
        r"^\s*(hi|hello|hey|dear)\s+[^,\n.!?-]{1,60}\s*[,!?.-]?\s*",
        f"{greeting}\n\n",
        cleaned,
        count=1,
        flags=re.IGNORECASE,
    )
    if replaced == cleaned:
        return f"{greeting}\n\n{cleaned}"
    return replaced


def _repair_mockup_urls(body: str, mockup_url: str) -> str:
    """Replace Vercel-looking links with the exact stored mockup URL.

    Nemotron sometimes inserts spaces into domains, and the sentence trimmer can
    cut a URL at `.vercel.` before `.app`. In both cases, use the database URL.
    """

    if not mockup_url or "vercel.app" not in mockup_url:
        return body
    return re.sub(
        r"https://[-A-Za-z0-9.\s]+?vercel(?:\s*\.\s*app)?",
        mockup_url,
        body,
        flags=re.IGNORECASE,
    )


def _strip_url_trailing_punctuation(body: str, mockup_url: str) -> str:
    """Remove punctuation that mail clients can accidentally include in URLs."""

    if not mockup_url:
        return body
    return re.sub(rf"{re.escape(mockup_url)}[.,;:]+", mockup_url, body)


def _repair_rating_spacing(body: str) -> str:
    """Repair model spacing in decimal ratings like `4. 9-star`."""

    return re.sub(r"\b(\d)\.\s+(\d)(?=[-\u2011\u2010\u2013 ]?star\b)", r"\1.\2", body, flags=re.IGNORECASE)


def _capitalize_paragraph_starts(body: str) -> str:
    """Capitalize the first letter of each paragraph for cleaner outreach."""

    paragraphs = body.split("\n\n")
    cleaned: list[str] = []
    for paragraph in paragraphs:
        match = re.search(r"[A-Za-z]", paragraph)
        if not match:
            cleaned.append(paragraph)
            continue
        index = match.start()
        cleaned.append(paragraph[:index] + paragraph[index].upper() + paragraph[index + 1 :])
    return "\n\n".join(cleaned)


def _polish_body(body: str, business_name: str, mockup_url: str) -> str:
    """Apply deterministic cleanup to model email copy before saving it."""

    polished = _repair_mockup_urls(body, mockup_url)
    polished = _strip_url_trailing_punctuation(polished, mockup_url)
    polished = _repair_rating_spacing(polished)
    polished = _business_salutation(polished, business_name)
    polished = _capitalize_paragraph_starts(polished)
    return polished


def _validate(payload: dict[str, Any]) -> dict[str, str]:
    """Validate Nemotron's email draft payload."""

    subject = str(payload.get("subject") or "").strip()
    body = str(payload.get("body") or "").strip()
    if not subject:
        raise ValueError("subject is required.")
    if not body:
        raise ValueError("body is required.")
    if len(subject) > 50:
        subject = subject[:47].rstrip() + "..."
    if len(_sentences(body)) > 5:
        body = _trim_sentences(body, 5)
    return {"subject": subject, "body": body}


def _format_prompt(lead: dict[str, Any], mockup_url: str, angle: str) -> str:
    """Load and format the prompt for one Pitcher angle."""

    if angle not in PROMPT_BY_ANGLE:
        valid = ", ".join(sorted(PROMPT_BY_ANGLE))
        raise ValueError(f"Unknown Pitcher angle: {angle}. Expected one of: {valid}.")

    template = (PROMPT_DIR / PROMPT_BY_ANGLE[angle]).read_text(encoding="utf-8")
    return template.format(
        business_name=lead.get("business_name", "Unknown business"),
        niche=lead.get("niche", "local service"),
        city=lead.get("city", ""),
        website=lead.get("website") or "not listed",
        rating=lead.get("google_rating") or "unknown",
        review_count=lead.get("review_count") or 0,
        pain_points=", ".join(lead.get("top_review_pain_points") or []) or "none provided",
        website_score=lead.get("website_score") or "unknown",
        website_reasons=", ".join(lead.get("website_score_reasons") or []) or "none provided",
        mockup_url=mockup_url,
    )


def run(lead: dict[str, Any], mockup_url: str, angle: str) -> dict[str, Any]:
    """Generate a personalized email draft for one Pitcher angle.

    Expected failures return an error dictionary so the future Pitcher claw can
    keep moving without crashing the whole heartbeat.
    """

    lead_id = _lead_id(lead)
    business_name = str(lead.get("business_name") or "lead")
    if not mockup_url:
        result = {"error": "mockup_url is required.", "_status": "skipped", "angle": angle}
        _safe_log("generate_email", "skipped", f"could not draft email for {business_name}: no mockup URL.", lead_id, result)
        return result

    try:
        prompt = _format_prompt(lead, mockup_url, angle)
    except ValueError as exc:
        result = {"error": str(exc), "_status": "skipped", "angle": angle}
        _safe_log("generate_email", "skipped", f"could not draft email for {business_name}: {exc}", lead_id, result)
        return result

    last_error: Exception | None = None
    for attempt in range(2):
        retry_note = ""
        if attempt:
            retry_note = f"\n\nPrevious output violated rules: {last_error}. Regenerate with the exact JSON shape."
        try:
            payload = nemotron_client.chat_json(
                system="You are Pitcher, a NemoClaw claw writing concise, non-spammy outreach. Return JSON only.",
                user=prompt + retry_note,
                retries=1,
            )
            draft = _validate(payload)
            draft["body"] = _polish_body(draft["body"], business_name, mockup_url)
            result: dict[str, Any] = {"angle": angle, **draft}
            _safe_log(
                "generate_email",
                "succeeded",
                f"drafted {angle} email for {business_name}.",
                lead_id,
                {"angle": angle, "subject": draft["subject"]},
            )
            return result
        except (nemotron_client.NemotronClientError, ValueError) as exc:
            last_error = exc

    result = {"error": str(last_error), "_status": "skipped", "angle": angle}
    _safe_log("generate_email", "skipped", f"could not draft {angle} email for {business_name}: {last_error}", lead_id, result)
    return result
