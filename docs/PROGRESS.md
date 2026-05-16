# Mainstreet NemoClaw Progress

## Current Status

- Read `AGENTS.md`.
- Read `docs/Mainstreet_NemoClaw_Codex_Execution_Spec.md`.
- Created the Task 4 monorepo skeleton.
- Added corrected schema columns to the spec and `agents/scripts/setup_supabase.sql`.
- Dashboard dependencies were resolved and installed locally for validation.

## Spec Consistency Check

Overall, the spec is aligned around a NemoClaw + Nemotron build: NemoClaw is the runtime/sandbox story, Nemotron is the reasoning model, Supabase is shared memory/queue, and Section 10 is the implementation order.

Issues to resolve or keep in mind:

- Task 21 has been clarified as MVP one-variant/one-critique by default; Tasks 36-37 are hardening to full 3-variant, multi-iteration behavior.
- `leads.review_texts`, `leads.email`, and `outreach.to_address` have been added to the spec schema and setup SQL.
- Task 15 says `scrape_leads.run(...) -> int`, but then expects Scout to process each new lead. The tool should return inserted lead rows/IDs plus count, or Scout must query newly inserted leads afterward.
- Task 1 says dependencies are none, but the actual rate check needs NemoClaw/Nemotron routing, NVIDIA credentials, and Apify credentials to produce real numbers.

## OpenClaw Wording Review

Remaining `OpenClaw` references found:

- Runtime lock: "OpenClaw-compatible environment" - acceptable compatibility reference.
- NemoClaw notes: "OpenClaw-compatible inside NemoClaw" - acceptable compatibility reference.
- Heartbeat model: "OpenClaw-compatible HEARTBEAT.md" - acceptable compatibility reference.
- Race-condition wording was changed to "NemoClaw/OpenShell heartbeat scheduling".
- `.env.example` now uses `NEMOCLAW_WORKSPACE`.

No problematic product/story wording like "OpenClaw claws" was found.

## Section 10 Execution Checklist

- [ ] Task 0: NemoClaw install/onboard and sandbox smoke test.
- [ ] Task 1: Nemotron and Apify rate-limit check script.
- [ ] Task 2: Domain and Resend DNS setup.
- [ ] Task 3: Supabase project and schema.
- [x] Task 4: Monorepo skeleton.
- [ ] Task 5: Vercel project.
- [ ] Task 6: Apify test scrape.
- [ ] Task 7: Discord setup.
- [ ] Task 8: Nemotron client.
- [ ] Task 9: Supabase client and helpers.
- [ ] Task 10: Action logger.
- [ ] Task 11: Discord outbound bridge.
- [ ] Task 12: Scout `scrape_leads`.
- [ ] Task 13: Scout `score_website`.
- [ ] Task 14: Scout `extract_pain_points`.
- [ ] Task 15: Scout claw integration.
- [ ] Task 16: Designer `generate_mockup`.
- [ ] Task 17: Designer `screenshot_html`.
- [ ] Task 18: Designer `critique_mockup`.
- [ ] Task 19: Designer deploy with Supabase Storage fallback.
- [ ] Task 20: Designer `pick_winner`.
- [ ] Task 21: Designer claw integration.
- [ ] Task 22: Dashboard skeleton.
- [ ] Task 23: Dashboard realtime activity feed.
- [ ] Task 24: Pitcher `generate_email`.
- [ ] Task 25: Pitcher `critique_email`.
- [ ] Task 26: Pitcher `send_email`.
- [ ] Task 27: Pitcher claw integration.
- [ ] Task 28: Discord inbound approval worker.
- [ ] Task 29: Closer `classify_reply`.
- [ ] Task 30: Google Calendar integration.
- [ ] Task 31: Closer meeting/reply tools.
- [ ] Task 32: Closer claw integration.
- [ ] Task 33: Resend inbound webhook.
- [ ] Task 34: Lead detail page.
- [ ] Task 35: Live metrics bar.
- [ ] Task 36: Designer self-critique loop upgrade.
- [ ] Task 37: Designer 3-variant winner upgrade.
- [ ] Task 38: Pitcher 4-angle critique upgrade.
- [ ] Task 39: MEMORY.md self-update.
- [ ] Task 40: Demo data seeder.
- [ ] Task 41: Start/stop all claws scripts.
- [ ] Task 42-46: Polish, monitor, rehearse, and fix.
- [ ] Task 47: Vapi inbound stretch.

## First 5 Tasks To Implement

1. Task 0: NemoClaw install/onboard and sandbox smoke test.
2. Task 1: Rate-limit check script.
3. Task 2: Domain and Resend DNS.
4. Task 3: Supabase project and schema.
5. Task 4: Monorepo skeleton.

## Manual Setup / API Key Blockers

- NemoClaw/Brev access and working sandbox runtime.
- NVIDIA API key or NemoClaw/OpenShell routed Nemotron credentials.
- Supabase project URL, anon key, service key, Realtime setup, and Storage bucket.
- Apify token.
- Domain purchase plus Resend domain verification, DNS records, and Resend API key.
- Vercel project, token, and optional team ID.
- Discord webhook URL; bot token and channel ID for inbound approval flow.
- Google Calendar OAuth client ID, client secret, and refresh token.
- Vapi API key and phone number only if stretch is attempted.

## Validation

- `python --version` -> Python 3.11.3.
- `python -m compileall agents integrations workers` passed.
- `python -c "import tomllib; ..."` parsed `agents/pyproject.toml`.
- `python -m pip install --dry-run -r agents/requirements.txt` passed after network approval.
- `npm.cmd install --package-lock-only --ignore-scripts` passed after network approval.
- `npm.cmd install --ignore-scripts` passed.
- `npm.cmd run typecheck` passed.
- `npm.cmd run build` passed.

Note: npm reported 2 audit findings in the dependency tree (1 moderate, 1 high). No package upgrades were applied because Task 4 is locked to the basic Next.js skeleton.

## TASK 8 Blockers

- Need working NemoClaw/OpenShell inference route or direct NVIDIA fallback URL.
- Need `NEMOTRON_BASE_URL`, `NEMOTRON_MODEL`, and either routed credentials or `NVIDIA_API_KEY`.
- Need confirmation whether the NemoClaw gateway accepts a placeholder API key such as `openshell`.
- Need to know whether `nvidia/nemotron-3-super-120b-a12b` supports `response_format={"type": "json_object"}` and vision calls in the selected route.
