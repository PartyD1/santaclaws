"""Designer tool for critiquing generated mockups."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.designer.tools import screenshot_html
from agents.shared import nemotron_client
from agents.shared.logger import logger


PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "designer_critique.txt"


def _safe_log(action_type: str, status: str, message: str, lead_id: str | None, result: dict[str, Any]) -> None:
    """Best-effort action logging."""

    try:
        logger.log("designer", action_type, status, message, lead_id=lead_id, result=result)
    except Exception as exc:  # pragma: no cover - local/no-credential path.
        print(f"Designer log skipped: {exc}")


def _prompt(lead: dict[str, Any]) -> str:
    """Format the critique prompt."""

    return PROMPT_PATH.read_text(encoding="utf-8").format(
        business_name=lead.get("business_name", "Unknown business"),
        niche=lead.get("niche", "auto repair"),
        city=lead.get("city", ""),
    )


def _html_fallback(html: str, reason: str) -> dict[str, Any]:
    """Critique based on raw HTML when screenshot or vision is unavailable."""

    lowered = html.lower()
    issues: list[str] = []
    score = 10
    checks = [
        ("<!doctype", "missing doctype"),
        ("tailwind", "missing Tailwind CDN"),
        ("tel:", "missing phone CTA"),
        ("services", "missing services section"),
        ("contact", "missing contact section"),
    ]
    for needle, issue in checks:
        if needle not in lowered:
            score -= 2
            issues.append(issue)
    if "lorem ipsum" in lowered:
        score -= 2
        issues.append("contains lorem ipsum")
    score = max(1, min(10, score))
    return {
        "score": score,
        "issues": issues[:5],
        "suggestions": ["Fix the listed structural issues before sending."] if issues else [],
        "fallback": True,
        "fallback_reason": reason,
    }


def _normalize(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize Nemotron critique JSON."""

    score = int(payload.get("score") or 1)
    return {
        "score": max(1, min(10, score)),
        "issues": [str(item) for item in payload.get("issues", [])][:5],
        "suggestions": [str(item) for item in payload.get("suggestions", [])][:5],
    }


def run(html: str, lead: dict[str, Any]) -> dict[str, Any]:
    """Critique a mockup using vision when available, with HTML fallback."""

    lead_id = None if lead.get("id") is None else str(lead.get("id"))
    try:
        image_b64 = screenshot_html.run_b64(html)
        payload = nemotron_client.chat_vision(
            system="You are Designer self-critiquing a Mainstreet mockup. Return JSON only.",
            user=_prompt(lead),
            image_b64=image_b64,
        )
        result = _normalize(payload)
    except Exception as exc:
        result = _html_fallback(html, str(exc))

    _safe_log(
        "critique_mockup",
        "succeeded",
        f"critiqued mockup for {lead.get('business_name', 'lead')} at {result['score']}/10.",
        lead_id,
        result,
    )
    return result
