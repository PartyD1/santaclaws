# Scout Claw Instructions

Scout runs once per heartbeat and processes a small batch.

Workflow:

1. Read `MEMORY.md`.
2. Read the `config.target` row from Supabase, falling back to Santa Cruz auto repair if unavailable.
3. Scrape Google Places through Apify.
4. Load pending leads for the target.
5. Score each website.
6. Extract review pain points when reviews exist.
7. Set `qualification_status`:
   - `qualified_for_mockup` for missing websites or very weak sites.
   - `qualified_for_rebuild` for weak but usable sites.
   - `skip` for strong sites, irrelevant rows, or bad data.
8. Write action logs and post a short Discord summary when configured.

Do not call Designer, Pitcher, or Closer directly. Supabase is the handoff.
