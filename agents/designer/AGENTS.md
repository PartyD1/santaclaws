# Designer Claw Instructions

Designer runs once per heartbeat and processes at most one lead.

Workflow:

1. Read `MEMORY.md`.
2. Read the oldest lead with `qualified_for_mockup` or `qualified_for_rebuild`.
3. Claim it with the Supabase guard before processing.
4. Generate mockup HTML.
5. Critique the mockup once.
6. Deploy to Vercel, falling back to Supabase Storage.
7. Insert a `generated_sites` row.
8. Mark exactly one generated site as the chosen winner.
9. Write action logs and post a short Discord summary when configured.

Default MVP behavior is one variant: `DESIGNER_VARIANT_COUNT=1`. Set
`DESIGNER_VARIANT_COUNT=3` only when the live route is stable.
