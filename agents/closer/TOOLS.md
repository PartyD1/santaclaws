# Closer Tools

- `classify_reply.run(inbound_id) -> dict`
- `propose_meeting_times.run(...) -> dict`
- `draft_reply.run(inbound_id, branch, meeting_times=None) -> dict`
- `book_meeting.run(lead_id, chosen_slot, attendee_email, inbound_id=None) -> dict`

Supported classifications:

- `interested`
- `not_interested`
- `has_question`
- `has_objection`
- `spam`
- `uncertain`

Email inbound replies are supported.
