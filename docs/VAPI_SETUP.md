# Vapi Inbound Voice Setup

This is a stretch path. The core NemoClaw pipeline still works without Vapi.

## Required Env

```bash
VAPI_API_KEY=
VAPI_PHONE_NUMBER=
VAPI_WEBHOOK_URL=
VAPI_WEBHOOK_PORT=8787
```

`VAPI_PHONE_NUMBER` may be the Vapi phone-number id. If you use an E.164 number
like `+14155550123`, the setup helper will list phone numbers and resolve it.

## Local Webhook

Run the webhook worker:

```bash
python -m workers.vapi_webhook --port 8787
```

Expose it with your tunnel of choice:

```bash
ngrok http 8787
```

Set `VAPI_WEBHOOK_URL` to the public HTTPS URL from the tunnel.

## Configure Assistant

```bash
python -m agents.integrations.vapi_client
```

This creates an inbound-only Vapi assistant, sets its server URL, and attaches it
to `VAPI_PHONE_NUMBER`. It does not place outbound calls.

## Runtime Flow

1. Caller dials the Vapi number.
2. Vapi sends status/transcript/end-of-call events to `workers.vapi_webhook`.
3. End-of-call report inserts an `inbound` row with `channel='voice'`.
4. Closer heartbeat classifies the transcript and follows the existing inbound flow.
5. Dashboard lead detail shows the voice transcript in Inbound Replies.

## Fallback

If `VAPI_API_KEY`, `VAPI_PHONE_NUMBER`, or `VAPI_WEBHOOK_URL` is missing, Vapi is
treated as not configured. Keep using seeded/email inbound rows for the demo.
