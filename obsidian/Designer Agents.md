---
tags: [designer, workflow]
claw: designer
---

# Designer Agents

> [[Designer Memory]] | [[Designer Soul]] | [[Designer Tools]] | [[Designer Agents]] | [[Designer Heartbeat]]

Designer runs once per heartbeat and processes at most one lead.

Workflow:

1. Read `MEMORY.md`.
2. Read the oldest lead with `qualified_for_mockup` or `qualified_for_rebuild`.
3. Claim it with the Supabase guard before processing.
4. Generate `clean_modern`, `retro_local`, and `premium` mockup variants.
5. Self-critique each variant and regenerate until it scores at least 8/10, capped at 5 iterations.
6. Deploy each successful variant to Vercel, falling back to Supabase Storage.
7. Insert `generated_sites` rows with final score, issues, and iteration count.
8. Pick one winner and mark exactly one generated site as `is_chosen_winner=true`.
9. Write action logs and post a short Discord summary when configured.

Default behavior is the full three-variant quality path. Set
`DESIGNER_VARIANT_COUNT=1` only as a manual fallback when live credentials or
rate limits are tight.
