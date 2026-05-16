---
tags: [closer, tools]
claw: closer
---

# Closer Tools

> [[Closer Memory]] | [[Closer Soul]] | [[Closer Tools]] | [[Closer Agents]] | [[Closer Heartbeat]]

- `classify_reply.run(inbound_id) -> dict`
- `propose_meeting_times.run(...) -> dict`
- `draft_reply.run(inbound_id, branch, meeting_times=None) -> dict`
- `book_meeting.run(lead_id, chosen_slot, attendee_email, inbound_id=None) -> dict`
- `handle_vapi_call.run(payload) -> dict`

Supported classifications:

- `interested`
- `not_interested`
- `has_question`
- `has_objection`
- `spam`
- `uncertain`

Email inbound and Vapi voice transcripts are supported. Vapi is inbound-only;
do not add outbound calling.
