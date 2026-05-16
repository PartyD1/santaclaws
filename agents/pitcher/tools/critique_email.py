"""Pitcher tool for self-critiquing outreach email drafts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.shared import nemotron_client
from agents.shared.logger import logger


PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "pitcher_critique.txt"


def _lead_id(lead: dict[str, Any]) -> str | None:
    """Return a string lead id when present."""

    value = lead.get("id")
    return None if value is None else str(value)


def _safe_log(action_type: str, status: str, message: str, lead_id: str | None, result: dict[str, Any]) -> None:
    """Best-effort action logging."""

    try:
        logger.log("pitcher", action_type, status, message, lead_id=lead_id, result=result)
    except Exception as exc:  # pragma: no cover - local/no-credential path.
        print(f"Pitcher log skipped: {exc}")


def _score(value: Any) -> int:
    """Clamp a numeric score to the 1-10 critique scale."""

    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        score = 1
    return max(1, min(10, score))


def _format_prompt(subject: str, body: str, lead: dict[str, Any], mockup_url: str | None) -> str:
    """Build the critique prompt."""

    return PROMPT_PATH.read_text(encoding="utf-8").format(
        business_name=lead.get("business_name", "Unknown business"),
        niche=lead.get("niche", "local service"),
        city=lead.get("city", ""),
        pain_points=", ".join(lead.get("top_review_pain_points") or []) or "none provided",
        mockup_url=mockup_url or "not provided",
        subject=subject,
        body=body,
    )


def _normalize(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize Nemotron critique JSON."""

    result = {
        "personalization_score": _score(payload.get("personalization_score")),
        "specificity_score": _score(payload.get("specificity_score")),
        "clarity_score": _score(payload.get("clarity_score")),
        "non_spam_score": _score(payload.get("non_spam_score")),
        "overall_score": _score(payload.get("overall_score")),
        "biggest_issue": str(payload.get("biggest_issue") or "No issue provided.").strip(),
        "send_ready": bool(payload.get("send_ready")),
    }
    if result["overall_score"] >= 8 and not result["send_ready"]:
        result["send_ready"] = True
    return result


def _fallback_critique(subject: str, body: str, reason: str) -> dict[str, Any]:
    """Provide a local critique when Nemotron is unavailable."""

    lowered = f"{subject} {body}".lower()
    generic_terms = ["buy our stuff", "limited time", "guaranteed", "act now", "dear business owner"]
    score = 8
    issue = "Email is clear enough for a lightweight fallback review."
    if any(term in lowered for term in generic_terms):
        score = 3
        issue = "Email sounds generic or spammy."
    elif len(subject) > 50:
        score = 5
        issue = "Subject is too long."
    elif len([part for part in body.replace("?", ".").replace("!", ".").split(".") if part.strip()]) > 5:
        score = 6
        issue = "Body is too long."

    return {
        "personalization_score": score,
        "specificity_score": score,
        "clarity_score": max(1, min(10, score + 1)),
        "non_spam_score": score,
        "overall_score": score,
        "biggest_issue": issue,
        "send_ready": score >= 8,
        "fallback": True,
        "fallback_reason": reason,
    }


def run(subject: str, body: str, lead: dict[str, Any], mockup_url: str | None = None) -> dict[str, Any]:
    """Critique an outreach email and return sub-scores plus an overall score."""

    lead_id = _lead_id(lead)
    business_name = str(lead.get("business_name") or "lead")
    try:
        payload = nemotron_client.chat_json(
            system="You are Pitcher self-critiquing outreach before a human sees it. Return JSON only.",
            user=_format_prompt(subject, body, lead, mockup_url),
            retries=1,
        )
        result = _normalize(payload)
    except nemotron_client.NemotronClientError as exc:
        result = _fallback_critique(subject, body, str(exc))

    _safe_log(
        "critique_email",
        "succeeded",
        f"critiqued email for {business_name} at {result['overall_score']}/10.",
        lead_id,
        result,
    )
    return result
