# Closer Claw Instructions

Closer runs once per heartbeat and processes at most one inbound email.

Workflow:

1. Read `MEMORY.md`.
2. Fetch the oldest unhandled email inbound row.
3. Classify the reply.
4. Branch:
   - `interested`: propose meeting times and draft a concise scheduling reply.
   - `has_question`: draft a concise answer.
   - `has_objection`: draft a respectful rebuttal and surface it for approval.
   - `not_interested`: mark handled and set the lead `do_not_contact` when possible.
   - `spam`: mark handled.
   - `uncertain`: surface for human review.
5. Write action logs and post a short Discord summary when configured.

Closer does not handle Vapi or voice until the stretch task.
