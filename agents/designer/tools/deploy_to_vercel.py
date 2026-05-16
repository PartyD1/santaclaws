"""Designer tool for deploying mockup HTML with fallback."""

from __future__ import annotations

import re
from typing import Any

from agents.integrations import supabase_storage_client, vercel_client
from agents.shared.logger import logger


def _safe_log(action_type: str, status: str, message: str, lead_id: str | None, result: dict[str, Any]) -> None:
    """Best-effort action logging."""

    try:
        logger.log("designer", action_type, status, message, lead_id=lead_id, result=result)
    except Exception as exc:  # pragma: no cover - local/no-credential path.
        print(f"Designer log skipped: {exc}")


def _slug(value: str) -> str:
    """Create a URL-safe slug."""

    slug = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    return slug[:80] or "mainstreet-mockup"


def run(html: str, slug: str, lead_id: str | None = None) -> dict[str, Any]:
    """Deploy HTML to Vercel, falling back to Supabase Storage."""

    safe_slug = _slug(slug)
    try:
        url = vercel_client.deploy_html_as_site(html, safe_slug)
        result = {"url": url, "provider": "vercel"}
    except Exception as vercel_error:
        try:
            url = supabase_storage_client.upload_html(html, f"{safe_slug}/index.html")
            result = {
                "url": url,
                "provider": "supabase",
                "fallback_reason": str(vercel_error),
            }
        except Exception as storage_error:
            result = {
                "url": None,
                "provider": None,
                "vercel_error": str(vercel_error),
                "storage_error": str(storage_error),
            }
            _safe_log("deploy_mockup", "failed", f"failed to deploy mockup {safe_slug}.", lead_id, result)
            raise RuntimeError(f"mockup deploy failed: {result}") from storage_error

    _safe_log("deploy_mockup", "succeeded", f"deployed mockup {safe_slug} via {result['provider']}.", lead_id, result)
    return result
