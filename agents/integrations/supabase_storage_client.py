"""Supabase Storage fallback for Designer mockups."""

from __future__ import annotations

from agents.shared.supabase_client import get_client


BUCKET = "mockups"


class SupabaseStorageError(RuntimeError):
    """Raised when Supabase Storage upload fails."""


def upload_html(html: str, path: str) -> str:
    """Upload HTML to public Supabase Storage and return its public URL."""

    if "<html" not in html.lower():
        raise SupabaseStorageError("upload_html requires a complete HTML document.")
    normalized_path = path.strip().lstrip("/") or "mockup.html"
    if not normalized_path.endswith(".html"):
        normalized_path += ".html"

    client = get_client()
    try:
        client.storage.from_(BUCKET).upload(
            normalized_path,
            html.encode("utf-8"),
            {"content-type": "text/html", "upsert": "true"},
        )
    except Exception as exc:
        raise SupabaseStorageError(f"Supabase Storage upload failed: {exc}") from exc

    public = client.storage.from_(BUCKET).get_public_url(normalized_path)
    if isinstance(public, str):
        return public
    if isinstance(public, dict) and public.get("publicUrl"):
        return str(public["publicUrl"])
    raise SupabaseStorageError("Supabase Storage did not return a public URL.")
