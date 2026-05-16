"""Designer tool for choosing the strongest mockup variant."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.shared import nemotron_client
from agents.shared.logger import logger


PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "designer_pick_winner.txt"
VALID_VARIANTS = {"clean_modern", "retro_local", "premium"}


def _safe_log(action_type: str, status: str, message: str, lead_id: str | None, result: dict[str, Any]) -> None:
    """Best-effort action logging."""

    try:
        logger.log("designer", action_type, status, message, lead_id=lead_id, result=result)
    except Exception as exc:  # pragma: no cover - local/no-credential path.
        print(f"Designer log skipped: {exc}")


def _variants_summary(variants: list[dict[str, Any]]) -> str:
    """Create a compact summary for winner selection."""

    lines = []
    for item in variants:
        html = str(item.get("html") or "")
        lines.append(
            "- {variant}: score={score}, url={url}, issues={issues}, html_excerpt={excerpt}".format(
                variant=item.get("variant"),
                score=item.get("score"),
                url=item.get("url"),
                issues=item.get("issues", []),
                excerpt=html[:500].replace("\n", " "),
            )
        )
    return "\n".join(lines)


def _fallback_winner(variants: list[dict[str, Any]]) -> dict[str, Any]:
    """Pick the highest-scoring variant without Nemotron."""

    best = max(variants, key=lambda item: float(item.get("score") or 0))
    return {
        "winner": best.get("variant"),
        "reasoning": "Picked the highest critique score as a fallback.",
    }


def run(lead: dict[str, Any], variants: list[dict[str, Any]]) -> dict[str, Any]:
    """Ask Nemotron to pick the best mockup variant."""

    if not variants:
        raise ValueError("variants cannot be empty.")

    lead_id = None if lead.get("id") is None else str(lead.get("id"))
    prompt = PROMPT_PATH.read_text(encoding="utf-8").format(
        business_name=lead.get("business_name", "Unknown business"),
        niche=lead.get("niche", "auto repair"),
        city=lead.get("city", ""),
        rating=lead.get("google_rating") or "unknown",
        review_count=lead.get("review_count") or 0,
        pain_points=", ".join(lead.get("top_review_pain_points") or []) or "none provided",
        variants_summary=_variants_summary(variants),
    )

    try:
        payload = nemotron_client.chat_json(
            system="You are Designer choosing the best Mainstreet mockup. Return JSON only.",
            user=prompt,
            retries=1,
        )
        winner = str(payload.get("winner") or "")
        if winner not in VALID_VARIANTS:
            raise ValueError(f"invalid winner: {winner}")
        result = {"winner": winner, "reasoning": str(payload.get("reasoning") or "")}
    except Exception as exc:
        result = _fallback_winner(variants)
        result["fallback_error"] = str(exc)

    _safe_log(
        "pick_winner",
        "succeeded",
        f"picked {result['winner']} mockup for {lead.get('business_name', 'lead')}.",
        lead_id,
        result,
    )
    return result
