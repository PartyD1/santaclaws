"""Scout tool for simple website quality scoring."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlparse

from agents.shared.logger import logger


MAX_PAGE_BYTES = 2 * 1024 * 1024
PHONE_RE = re.compile(r"(\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def _safe_log(action_type: str, status: str, message: str, lead_id: str | None, result: dict[str, Any]) -> None:
    """Best-effort action logging for local and no-credential runs."""

    try:
        logger.log("scout", action_type, status, message, lead_id=lead_id, result=result)
    except Exception as exc:  # pragma: no cover - local/no-credential path.
        print(f"Scout log skipped: {exc}")


def _normalize_url(url: str | None) -> str | None:
    """Normalize a possibly missing URL for fetching."""

    if not url or not url.strip():
        return None
    value = url.strip()
    parsed = urlparse(value)
    if not parsed.scheme:
        return f"https://{value}"
    return value


def _title_text(html: str) -> str:
    """Extract title text from HTML."""

    match = TITLE_RE.search(html)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def _last_modified_recent(header: str | None) -> bool | None:
    """Return whether Last-Modified is within two years, or None if absent/unparseable."""

    if not header:
        return None
    try:
        modified_at = parsedate_to_datetime(header)
        if modified_at.tzinfo is None:
            modified_at = modified_at.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None
    age_days = (datetime.now(timezone.utc) - modified_at).days
    return age_days <= 730


async def _fetch(url: str) -> tuple[str, bytes, dict[str, str], int]:
    """Fetch a URL with httpx AsyncClient."""

    try:
        import httpx
    except ImportError as exc:  # pragma: no cover - local setup issue.
        raise RuntimeError("The `httpx` package is not installed. Run `pip install -r agents/requirements.txt`.") from exc

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        response = await client.get(url)
    return str(response.url), response.content, dict(response.headers), response.status_code


def _score_html(final_url: str, body: bytes, headers: dict[str, str]) -> dict[str, Any]:
    """Score fetched HTML according to the hackathon rubric."""

    html = body.decode("utf-8", errors="ignore")
    html_lower = html.lower()
    reasons: list[str] = []
    score = 2

    if urlparse(final_url).scheme == "https":
        score += 1
    else:
        reasons.append("not HTTPS")

    if re.search(r"<meta[^>]+name=[\"']viewport[\"']", html, re.IGNORECASE):
        score += 2
    else:
        reasons.append("missing mobile viewport")

    if len(body) < MAX_PAGE_BYTES:
        score += 1
    else:
        reasons.append("page heavier than 2MB")

    if "application/ld+json" in html_lower or "itemscope" in html_lower or "itemtype=" in html_lower:
        score += 1
    else:
        reasons.append("missing structured data")

    if PHONE_RE.search(html):
        score += 1
    else:
        reasons.append("no phone number visible")

    recent = _last_modified_recent(headers.get("last-modified") or headers.get("Last-Modified"))
    if recent is True:
        score += 1
    elif recent is False:
        reasons.append("site appears stale")
    else:
        reasons.append("no recent Last-Modified signal")

    title = _title_text(html)
    if 30 <= len(title) <= 60:
        score += 1
    else:
        reasons.append("title length is weak")

    return {"score": min(score, 10), "reasons": reasons, "final_url": final_url}


def run(url: str | None, lead_id: str | None = None) -> dict[str, Any]:
    """Score a website from 0-10 with short failure reasons."""

    normalized = _normalize_url(url)
    if normalized is None:
        result = {"score": 0, "reasons": ["no website"]}
        _safe_log("score_website", "skipped", "found no website to score.", lead_id, result)
        return result

    try:
        final_url, body, headers, status_code = asyncio.run(_fetch(normalized))
    except Exception as exc:
        result = {"score": 0, "reasons": [f"site unreachable: {exc.__class__.__name__}"]}
        _safe_log("score_website", "skipped", f"could not reach {normalized}.", lead_id, result)
        return result

    if status_code != 200:
        result = {"score": 0, "reasons": [f"HTTP {status_code}"], "final_url": final_url}
        _safe_log("score_website", "skipped", f"scored {normalized} as 0/10 due to HTTP {status_code}.", lead_id, result)
        return result

    result = _score_html(final_url, body, headers)
    _safe_log(
        "score_website",
        "succeeded",
        f"scored {final_url} as {result['score']}/10.",
        lead_id,
        result,
    )
    return result
