"""Tiny HTTP webhook worker for inbound Vapi voice calls."""

from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency validation catches this.
    load_dotenv = None  # type: ignore[assignment]

from agents.closer.tools import handle_vapi_call


def _load_env() -> None:
    """Load `.env` if python-dotenv is available."""

    if load_dotenv is not None:
        load_dotenv()


def _configured() -> tuple[bool, str | None]:
    """Return whether Vapi webhook handling is configured."""

    if not os.environ.get("VAPI_API_KEY", "").strip():
        return False, "VAPI_API_KEY is not set"
    if not os.environ.get("VAPI_PHONE_NUMBER", "").strip():
        return False, "VAPI_PHONE_NUMBER is not set"
    return True, None


def handle_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Handle one decoded Vapi webhook payload."""

    ok, reason = _configured()
    if not ok:
        print(f"Vapi webhook skipped: {reason}")
        return {"ok": True, "inserted": False, "reason": reason}
    try:
        result = handle_vapi_call.run(payload)
        return {"ok": True, **result}
    except Exception as exc:
        print(f"Vapi webhook failed: {exc}")
        return {"ok": True, "inserted": False, "reason": str(exc)}


class VapiWebhookHandler(BaseHTTPRequestHandler):
    """HTTP handler for Vapi POST webhooks."""

    def do_GET(self) -> None:  # noqa: N802 - stdlib method name.
        """Health check."""

        self._send_json({"ok": True, "service": "mainstreet-vapi-webhook"})

    def do_POST(self) -> None:  # noqa: N802 - stdlib method name.
        """Handle one Vapi webhook POST."""

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("payload must be a JSON object")
        except Exception as exc:
            self._send_json({"ok": True, "inserted": False, "reason": f"invalid json: {exc}"})
            return
        self._send_json(handle_payload(payload))

    def log_message(self, format: str, *args: Any) -> None:
        """Keep webhook logs compact."""

        print(f"Vapi webhook: {format % args}")

    def _send_json(self, payload: dict[str, Any]) -> None:
        """Send a JSON response."""

        body = json.dumps(payload, ensure_ascii=True, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server(port: int) -> None:
    """Run the Vapi webhook server."""

    _load_env()
    server = ThreadingHTTPServer(("0.0.0.0", port), VapiWebhookHandler)
    print(f"Vapi webhook worker listening on port {port}.")
    server.serve_forever()


def main() -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description="Run the Mainstreet NemoClaw Vapi webhook worker.")
    parser.add_argument("--port", type=int, default=int(os.environ.get("VAPI_WEBHOOK_PORT", "8787")))
    args = parser.parse_args()
    run_server(args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
