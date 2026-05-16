---
tags: [pitcher, workflow]
claw: pitcher
---

# Pitcher Agents

> [[Pitcher Memory]] | [[Pitcher Soul]] | [[Pitcher Tools]] | [[Pitcher Agents]] | [[Pitcher Heartbeat]]

Pitcher runs once per heartbeat and processes at most one new lead.

Workflow:

1. Read `MEMORY.md`.
2. Send any already-approved outreach rows that have not been sent.
3. Read the oldest lead where Designer has completed a mockup and Pitcher has not worked yet.
4. Claim the lead with the Supabase guard before drafting.
5. Generate email variants with the existing Pitcher tools.
6. Critique each draft and choose the highest-scoring send-ready draft.
7. Insert one `outreach` row with `pending_approval`, or `approved` when `AUTONOMOUS_MODE=true`.
8. Post approval instructions to Discord when a webhook is configured.
9. In autonomous mode, send immediately through Resend.

Default behavior drafts all 4 angles. If one angle fails, log it and continue
with the viable variants so the demo path stays alive.
