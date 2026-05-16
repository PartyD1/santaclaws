"""Pitcher tool for sending approved outreach through the configured provider."""

from __future__ import annotations

import html
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from agents.integrations import resend_client, smtp_client
from agents.shared.logger import logger
from agents.shared.supabase_client import get_client


def _now_iso() -> str:
    """Return a UTC timestamp for Supabase writes."""

    return datetime.now(timezone.utc).isoformat()


def _safe_log(action_type: str, status: str, message: str, lead_id: str | None, result: dict[str, Any]) -> None:
    """Best-effort action logging."""

    try:
        logger.log("pitcher", action_type, status, message, lead_id=lead_id, result=result)
    except Exception as exc:  # pragma: no cover - local/no-credential path.
        print(f"Pitcher log skipped: {exc}")


def _first_row(response: Any) -> dict[str, Any] | None:
    """Return the first row from a Supabase response."""

    rows = getattr(response, "data", None)
    if isinstance(rows, list):
        return rows[0] if rows else None
    if isinstance(rows, dict):
        return rows
    return None


def _fetch_mockup_url(lead_id: str) -> str | None:
    """Return the latest public mockup URL for a lead when available."""

    response = (
        get_client()
        .table("generated_sites")
        .select("vercel_url, storage_url")
        .eq("lead_id", lead_id)
        .order("generated_at", desc=True)
        .limit(1)
        .execute()
    )
    row = _first_row(response)
    if not row:
        return None
    return row.get("vercel_url") or row.get("storage_url")


def _plain_text_to_html(text: str, lead: dict[str, Any], mockup_url: str | None = None) -> str:
    """Convert plain-text outreach into polished, safe email HTML."""

    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    if not paragraphs:
        paragraphs = [text.strip()]
    rendered = []
    for paragraph in paragraphs:
        escaped = html.escape(paragraph).replace("\n", "<br>")
        rendered.append(
            "<p style=\"margin:0 0 16px; color:#273142; font-size:16px; line-height:1.62;\">"
            f"{escaped}"
            "</p>"
        )

    business_name = html.escape(str(lead.get("business_name") or "your business"))
    city = html.escape(str(lead.get("city") or "your area"))
    cta = ""
    if mockup_url:
        escaped_url = html.escape(mockup_url, quote=True)
        cta = f"""
          <tr>
            <td style="padding:8px 28px 24px;">
              <a href="{escaped_url}" style="display:inline-block; background:#0f172a; color:#ffffff; font-size:15px; font-weight:700; text-decoration:none; padding:13px 18px; border-radius:8px;">
                View the mockup
              </a>
            </td>
          </tr>
        """

    body_html = "\n".join(rendered)
    return f"""<!doctype html>
<html>
  <body style="margin:0; padding:0; background:#f4f6f8; font-family:Arial, Helvetica, sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f6f8; padding:28px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px; background:#ffffff; border:1px solid #dde3ea; border-radius:12px; overflow:hidden;">
            <tr>
              <td style="background:#0f172a; padding:22px 28px;">
                <div style="color:#ffffff; font-size:19px; font-weight:800; letter-spacing:0;">Santa Claws</div>
                <div style="color:#cbd5e1; font-size:13px; line-height:1.5; margin-top:4px;">Website mockup for {business_name} in {city}</div>
              </td>
            </tr>
            <tr>
              <td style="padding:30px 28px 10px;">
                {body_html}
              </td>
            </tr>
            {cta}
            <tr>
              <td style="padding:0 28px 30px;">
                <div style="height:1px; background:#e5eaf0; margin:8px 0 18px;"></div>
                <p style="margin:0; color:#64748b; font-size:13px; line-height:1.55;">
                  Sent by Santa Claws, a NemoClaw-powered demo team building quick website mockups for local businesses.
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


def _provider() -> str:
    """Return the configured email provider."""

    configured = os.environ.get("EMAIL_PROVIDER", "").strip().lower()
    if configured:
        return configured
    if os.environ.get("SMTP_HOST", "").strip():
        return "smtp"
    return "resend"


def _fetch_outreach(outreach_id: UUID | str) -> dict[str, Any]:
    """Fetch one outreach row."""

    response = get_client().table("outreach").select("*").eq("id", str(outreach_id)).limit(1).execute()
    row = _first_row(response)
    if not row:
        raise RuntimeError(f"Outreach row not found: {outreach_id}")
    return row


def _fetch_lead(lead_id: str) -> dict[str, Any]:
    """Fetch the lead for an outreach row."""

    response = get_client().table("leads").select("*").eq("id", lead_id).limit(1).execute()
    row = _first_row(response)
    if not row:
        raise RuntimeError(f"Lead row not found for outreach: {lead_id}")
    return row


def _mark_outreach(outreach_id: UUID | str, payload: dict[str, Any]) -> None:
    """Update the outreach row."""

    get_client().table("outreach").update(payload).eq("id", str(outreach_id)).execute()


def _send_via_provider(to_address: str, subject: str, body: str, lead: dict[str, Any], mockup_url: str | None) -> dict[str, Any]:
    """Send through SMTP or Resend based on env configuration."""

    html_body = _plain_text_to_html(body, lead, mockup_url)
    provider = _provider()
    if provider == "smtp":
        return smtp_client.send_email(
            to=to_address,
            subject=subject,
            html=html_body,
            text=body,
        )
    if provider == "resend":
        return resend_client.send_email(
            to=to_address,
            subject=subject,
            html=html_body,
            text=body,
        )
    raise RuntimeError("EMAIL_PROVIDER must be `smtp` or `resend`.")


def run(outreach_id: UUID | str) -> dict[str, Any]:
    """Send an approved outreach email.

    Uses `outreach.to_address` first, then falls back to `leads.email`.
    Expected setup failures return a structured result and mark outreach failed
    when a row can be reached.
    """

    lead_id: str | None = None
    try:
        outreach = _fetch_outreach(outreach_id)
        lead_id = str(outreach["lead_id"])
        lead = _fetch_lead(lead_id)
        if outreach.get("sent_at"):
            result = {"sent": False, "_status": "skipped", "error": "outreach already sent"}
            _safe_log("send_email", "skipped", f"outreach {outreach_id} was already sent.", lead_id, result)
            return result
        if outreach.get("status") != "approved":
            result = {"sent": False, "_status": "skipped", "error": "outreach is not approved"}
            _safe_log("send_email", "skipped", f"outreach {outreach_id} is not approved yet.", lead_id, result)
            return result

        to_address = (outreach.get("to_address") or lead.get("email") or "").strip()
        if not to_address:
            raise RuntimeError("No recipient address found in outreach.to_address or leads.email.")

        response = _send_via_provider(
            to_address=to_address,
            subject=str(outreach["subject"]),
            body=str(outreach["body"]),
            lead=lead,
            mockup_url=_fetch_mockup_url(lead_id),
        )
        message_id = str(response["id"])
        _mark_outreach(
            outreach_id,
            {
                "status": "sent",
                "sent_at": _now_iso(),
                "to_address": to_address,
                "resend_message_id": message_id,
            },
        )
        result = {
            "sent": True,
            "message_id": message_id,
            "to_address": to_address,
            "provider": response.get("provider", _provider()),
        }
        _safe_log(
            "send_email",
            "succeeded",
            f"sent approved email to {to_address} via {result['provider']}.",
            lead_id,
            result,
        )
        return result
    except Exception as exc:
        result = {"sent": False, "_status": "failed", "error": str(exc)}
        try:
            _mark_outreach(outreach_id, {"status": "failed"})
        except Exception as mark_exc:
            result["mark_failed_error"] = str(mark_exc)
        _safe_log("send_email", "failed", f"could not send outreach {outreach_id}: {exc}", lead_id, result)
        return result
