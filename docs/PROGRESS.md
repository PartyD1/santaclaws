# Mainstreet NemoClaw Progress

## Current Status

- Read `AGENTS.md`.
- Read `docs/Mainstreet_NemoClaw_Codex_Execution_Spec.md`.
- Audited the repo against the full NemoClaw multi-agent execution spec for remaining incomplete work.
- Prepared Task 0 NemoClaw onboarding docs and smoke-test script; live completion remains blocked because `nemoclaw` is not installed on this machine.
- Created the Task 4 monorepo skeleton.
- Added corrected schema columns to the spec and `agents/scripts/setup_supabase.sql`.
- Dashboard dependencies were resolved and installed locally for validation.
- Implemented Task 8 Nemotron client in `agents/shared/nemotron_client.py`.
- Implemented Task 9 Supabase dataclasses and helper functions.
- Implemented Task 10 action logger in `agents/shared/logger.py`.
- Implemented Task 11 outbound Discord webhook bridge in `agents/shared/discord_bridge.py`.
- Implemented Tasks 12-14 Scout tools: Apify scraping, website scoring, and review pain extraction.
- Implemented Task 15 Scout claw heartbeat and `--once` CLI mode.
- Implemented Tasks 16-20 Designer tools: mockup generation, screenshotting, critique, deploy fallback, and winner selection.
- Implemented Task 21 Designer claw heartbeat and `--once` CLI mode.
- Implemented Tasks 22-23 dashboard skeleton, leads table, metrics bar, and realtime activity feed with polling fallback.
- Implemented Tasks 24-26 Pitcher tools: email generation, email critique, and Resend send helper.
- Implemented Tasks 27-28 Pitcher claw heartbeat and minimal Discord approval worker.
- Implemented Tasks 29-31 Closer tools: reply classification, Google Calendar fallback slots, meeting booking, and reply drafting.
- Implemented Tasks 32-33 Closer claw heartbeat and Resend inbound email webhook.
- Implemented Tasks 34-35 lead detail page and expanded live metrics polling.
- Implemented Tasks 36-38 Designer self-critique, three-variant winner selection, and Pitcher four-angle quality path.
- Implemented Tasks 39-41 MEMORY.md updater, demo data seeder, and claw start/stop scripts.
- Implemented Tasks 42-46 demo runbook, rehearsal checklist, fallback plan, dashboard polish, and mockup prompt quality pass.
- Implemented Task 47 Vapi inbound voice stretch with inbound-only assistant setup, webhook worker, voice transcript insertion, and dashboard transcript visibility.
- Replaced remaining demo-risk placeholders and documented the placeholder audit in `docs/PLACEHOLDER_AUDIT.md`.
- Updated the default NemoClaw/Nemotron model configuration to `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`.
- Fixed Supabase timestamp parsing for Python 3.9 local venvs that reject five-digit fractional seconds.
- Added Supabase-backed `agent_memory` persistence with `MEMORY.md` as a compatibility cache and deterministic fallback memory when Nemotron is unreachable.
- Added a `agents/scripts/preflight_check.py` runtime checker for Python/package/env/Supabase table readiness.
- Added `SETUP.md` as a teammate command reference for Brev, Ubuntu, NemoClaw, claw tests, dashboard, and full demo runs.
- Added per-claw dashboard pages for live status, action logs, durable memory, and claw-specific work queues/outputs.
- Added an OpenClaw-compatible runtime context loader plus `agents.scripts.openclaw_run`, and moved `start_all_claws.sh` onto that heartbeat runner.
- Wired Scout to load and log its OpenClaw-compatible SOUL/AGENTS/TOOLS/HEARTBEAT/MEMORY context at heartbeat start.
- Added Discord approval worker `PING`/`HELP` health replies and startup channel-id logging for demo debugging.
- Added a deterministic Designer fallback mockup path when Nemotron generation is unavailable, reset failed Designer claims, and restored one-variant MVP default.
- Upgraded Designer mockup quality prompts and fallback HTML with richer local-business structure, service cards, trust cues, pain-point fixes, and stronger contact sections.
- Hardened Vercel mockup deploys to request public deployments and reject login-protected URLs so Designer falls back to public Supabase Storage when needed.

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
- [x] Task 8: Nemotron client.
- [x] Task 9: Supabase client and helpers.
- [x] Task 10: Action logger.
- [x] Task 11: Discord outbound bridge.
- [x] Task 12: Scout `scrape_leads`.
- [x] Task 13: Scout `score_website`.
- [x] Task 14: Scout `extract_pain_points`.
- [x] Task 15: Scout claw integration.
- [x] Task 16: Designer `generate_mockup`.
- [x] Task 17: Designer `screenshot_html`.
- [x] Task 18: Designer `critique_mockup`.
- [x] Task 19: Designer deploy with Supabase Storage fallback.
- [x] Task 20: Designer `pick_winner`.
- [x] Task 21: Designer claw integration.
- [x] Task 22: Dashboard skeleton.
- [x] Task 23: Dashboard realtime activity feed.
- [x] Task 24: Pitcher `generate_email`.
- [x] Task 25: Pitcher `critique_email`.
- [x] Task 26: Pitcher `send_email`.
- [x] Task 27: Pitcher claw integration.
- [x] Task 28: Discord inbound approval worker.
- [x] Task 29: Closer `classify_reply`.
- [x] Task 30: Google Calendar integration.
- [x] Task 31: Closer meeting/reply tools.
- [x] Task 32: Closer claw integration.
- [x] Task 33: Resend inbound webhook.
- [x] Task 34: Lead detail page.
- [x] Task 35: Live metrics bar.
- [x] Task 36: Designer self-critique loop upgrade.
- [x] Task 37: Designer 3-variant winner upgrade.
- [x] Task 38: Pitcher 4-angle critique upgrade.
- [x] Task 39: MEMORY.md self-update.
- [x] Task 40: Demo data seeder.
- [x] Task 41: Start/stop all claws scripts.
- [x] Task 42-46: Polish, monitor, rehearse, and fix.
- [x] Task 47: Vapi inbound stretch.

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
- `python -m compileall agents/shared/nemotron_client.py` passed.
- `rg "nemotron-3-super|Super 120B|super-120b"` returned no remaining old model references after switching to Nano Omni 30B reasoning.
- Supabase timestamp parser validated against `2026-05-16T09:13:49.04514+00:00`, normalizing it to Python-compatible microseconds.
- `python -m compileall agents/shared/memory_updater.py agents/shared/supabase_client.py` passed after adding durable memory helpers.
- Fallback Scout memory pattern generation validated with a 5-lead heartbeat summary.
- `python -m compileall agents/scripts/preflight_check.py` passed.
- `python -m agents.scripts.preflight_check --skip-live` produced clear FAIL/WARN diagnostics in the local non-venv shell.
- `npm run typecheck` passed after adding per-claw dashboard pages.
- `npm run build` passed after adding per-claw dashboard pages.
- `python -m compileall agents/shared/openclaw_runtime.py agents/scripts/openclaw_run.py agents/scout/claw.py` passed after adding the OpenClaw-compatible runner.
- `python -m agents.scripts.openclaw_run scout --once` loaded Scout's OpenClaw-compatible context and exited cleanly in the local missing-credential path.
- `bash -n agents/scripts/start_all_claws.sh` passed after moving start-all onto the OpenClaw-compatible runner.
- `python -m agents.shared.nemotron_client` ran and failed clearly because the local Python environment does not have the `openai` package installed.
- `python -m compileall agents/shared/types.py agents/shared/supabase_client.py` passed.
- `agents.shared.types` and `agents.shared.supabase_client` import successfully without live credentials.
- Helper signatures for Task 9 were validated with `inspect.signature`.
- `Lead.from_row(...)` sample conversion passed.
- `python -m compileall agents/shared/logger.py` passed.
- Logger signatures were validated with `inspect.signature`.
- Logger direct call and context manager behavior were validated with a fake `insert_action`.
- `python -m compileall agents/shared/discord_bridge.py` passed.
- `python -m agents.shared.discord_bridge` skipped the live webhook smoke test because `DISCORD_WEBHOOK_URL` is not set.
- Discord payload truncation and embed formatting were validated locally.
- `python -m compileall agents/integrations/apify_client.py agents/scout/tools/scrape_leads.py agents/scout/tools/score_website.py agents/scout/tools/extract_pain_points.py` passed.
- Scout tool imports passed.
- `score_website.run(None)` returned score 0 with `no website`.
- `extract_pain_points.run(...)` with no reviews returned an empty list gracefully.
- Scout tool signatures were validated with `inspect.signature`.
- `python -m compileall agents/scout/claw.py` passed.
- `python -m agents.scout.claw --once` ran and exited cleanly with default target fallback because local Supabase/Python dependencies are not installed.
- `python -m compileall agents/designer/tools agents/integrations/vercel_client.py agents/integrations/supabase_storage_client.py` passed.
- Designer tool imports passed.
- Designer prompt formatting and HTML validation checks passed.
- Designer fallback mockup generation returns valid Tailwind HTML containing the business name when Nemotron is unavailable.
- Designer fallback quality smoke confirmed generated HTML includes hero, service cards, pain-point fixes, contact CTA, and valid document structure.
- `python -m compileall agents/integrations/vercel_client.py agents/designer/tools/deploy_to_vercel.py` passed after public URL verification for mockup deploys.
- `critique_mockup.run(...)` falls back to HTML inspection when Playwright is unavailable.
- `pick_winner.run(...)` falls back to highest critique score when Nemotron/OpenAI is unavailable.
- `deploy_to_vercel.run(...)` fails clearly when both Vercel and Supabase Storage dependencies/credentials are unavailable.
- `python -m compileall agents/designer/claw.py` passed.
- `python -m agents.designer.claw --once` ran and exited cleanly because local Supabase/Python dependencies are not installed.
- `npm.cmd run typecheck` passed for the dashboard.
- `npm.cmd run build` passed for the dashboard. Next.js emitted non-fatal webpack cache snapshot warnings.
- `python -m compileall agents/pitcher/tools agents/integrations/resend_client.py` passed.
- Pitcher tool imports and signatures were validated.
- Pitcher prompt formatting passed for all 4 angles.
- `generate_email.run(...)` missing-Nemotron path returns a skipped result clearly.
- `critique_email.run(...)` fallback scored a known bad email below 5.
- `send_email.run(...)` approval guard and fallback from `outreach.to_address` to `leads.email` were validated with fake clients.
- `python -m compileall agents/pitcher/claw.py workers/discord_bridge.py` passed.
- Pitcher heartbeat and Discord approval worker imports passed.
- Discord approval parser validated `APPROVE`, `SKIP`, and one-line `EDIT`.
- Discord approval worker now recognizes `PING` and `HELP` health checks in the configured approval channel.
- `python -m agents.pitcher.claw --once` ran and exited cleanly because local Supabase/Python dependencies are not installed.
- `python -m workers.discord_bridge` printed fallback approval instructions because bot credentials are not configured.
- Discord approval worker `EDIT` update/approval insert path was validated with a fake client.
- `python -m compileall agents/closer/tools agents/integrations/gcal_client.py` passed.
- Closer tool imports and signatures were validated.
- Google Calendar fallback returned 3 demo-safe meeting slots without credentials.
- `propose_meeting_times.run(...)` returned formatted slots with missing Google credentials.
- `classify_reply.run(...)` fallback classified sample replies correctly and updated fake Supabase rows.
- `book_meeting.run(...)` inserted a fake meeting row and returned a demo Google event id with fake clients.
- `draft_reply.run(...)` produced a concise fallback interested reply with fake clients.
- `python -m pip install --dry-run -r agents/requirements.txt` passed after adding Google Calendar dependencies.
- `python -m compileall agents/closer/claw.py` passed.
- `python -m agents.closer.claw --once` ran and exited cleanly because local Supabase/Python dependencies are not installed.
- Closer heartbeat interested branch was validated with fake clients.
- `npm.cmd run typecheck` passed for the dashboard inbound webhook route.
- `npm.cmd run build` passed for the dashboard after the inbound webhook route. Next.js emitted non-fatal webpack cache snapshot warnings.
- `npm.cmd run typecheck` passed for the lead detail page and expanded metrics.
- `npm.cmd run build` passed for the dashboard after Tasks 34-35. Next.js emitted non-fatal webpack cache snapshot warnings.
- `python -m compileall agents/designer/claw.py agents/pitcher/claw.py` passed after Tasks 36-38.
- Designer self-critique smoke validated regeneration until score 8 and `self_critique_iterations` persistence.
- Pitcher four-angle smoke validated all 4 angles are generated/critiqued and the highest score wins.
- `python -m agents.designer.claw --once` ran and exited cleanly because local Supabase/Python dependencies are not installed.
- `python -m agents.pitcher.claw --once` ran and exited cleanly because local Supabase/Python dependencies are not installed.
- `python -m compileall agents/shared/memory_updater.py agents/scripts/seed_demo_data.py agents/scout/claw.py agents/designer/claw.py agents/pitcher/claw.py agents/closer/claw.py` passed.
- Task 39-41 import/signature smoke passed.
- Memory updater smoke returned a clean skipped result because the local Python environment does not have the `openai` package installed.
- `python -m agents.scripts.seed_demo_data --clear` failed clearly because the local Python environment does not have the `supabase` package installed.
- `python -m agents.scout.claw --once`, `python -m agents.designer.claw --once`, `python -m agents.pitcher.claw --once`, and `python -m agents.closer.claw --once` ran and exited cleanly with missing local Supabase/OpenAI dependencies.
- Bash syntax checks for `start_all_claws.sh` and `stop_all_claws.sh` could not run because `bash`/`sh` is unavailable in this Windows session.
- `npm.cmd run typecheck` passed after Tasks 42-46 dashboard polish.
- `npm.cmd run build` passed after Tasks 42-46 dashboard polish. Next.js emitted non-fatal webpack cache snapshot warnings.
- `python -m compileall agents/integrations/vapi_client.py agents/closer/tools/handle_vapi_call.py agents/closer/tools/classify_reply.py agents/closer/claw.py workers/vapi_webhook.py` passed.
- Vapi fake end-of-call webhook smoke inserted a `voice` inbound row with transcript and matched lead phone.
- `python -m agents.integrations.vapi_client` skipped clearly because Vapi env is not configured.
- `python -m agents.integrations.vapi_client` with only `VAPI_WEBHOOK_URL` set skipped clearly because `VAPI_API_KEY` is missing.
- Vapi webhook missing-env smoke returned a clear non-inserting response.
- `python -m agents.closer.claw --once` ran and exited cleanly because local Supabase/OpenAI dependencies are not installed.
- `npm.cmd run typecheck` passed after Vapi dashboard transcript visibility.
- `npm.cmd run build` passed after Vapi dashboard transcript visibility. Next.js emitted non-fatal webpack cache snapshot warnings.
- Placeholder audit search found only acceptable historical/spec references and intentional NemoClaw `openshell` compatibility wording.
- `python -m compileall agents integrations workers` passed after placeholder replacement.
- Top-level `integrations.*` compatibility imports passed.
- `python -m agents.scripts.rate_limit_check --nemotron-rounds 1 --skip-apify` failed clearly because local OpenAI/Nemotron dependencies are not installed.
- `python -m agents.scripts.nuke_db` refused to run without `--demo-only --yes`.
- `python -m workers.inbound_email_worker` printed the active dashboard route status.
- `npm.cmd run typecheck` passed after dashboard API placeholder replacement.
- `npm.cmd run build` passed after dashboard API placeholder replacement. Next.js emitted non-fatal webpack cache snapshot warnings.

Note: npm reported 2 audit findings in the dependency tree (1 moderate, 1 high). No package upgrades were applied because Task 4 is locked to the basic Next.js skeleton.

## TASK 8 Runtime Blockers

- Install Python dependencies with `pip install -r agents/requirements.txt` before live smoke testing.
- Need working NemoClaw/OpenShell inference route or direct NVIDIA fallback URL.
- Need `NEMOTRON_BASE_URL`, `NEMOTRON_MODEL`, and either routed credentials or `NVIDIA_API_KEY`.
- Need confirmation whether the NemoClaw gateway accepts placeholder API key `openshell`.
- Need to verify whether `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` supports `response_format={"type": "json_object"}` and vision calls in the selected route.

## TASK 9 Runtime Blockers

- Install Python dependencies with `pip install -r agents/requirements.txt` before live Supabase calls.
- Need Supabase project URL, anon key, and service role key in `.env`.
- Need Task 3 schema applied successfully, including `leads.email`, `leads.review_texts`, and `outreach.to_address`.
- Need confirmation that Supabase Realtime publication includes the required tables.
- Need at least one test lead row to validate claim helpers like `claim_lead_for_designer`.

## TASK 10 Runtime Blockers

- Live logger validation still needs Supabase credentials and applied schema.
- Local console output needed UTF-8 when printing emoji logs from PowerShell.
- Context-manager failures now write `failed` actions and re-raise the original exception.
- Emoji/log-prefix mapping is Scout `🔍`, Designer `🎨`, Pitcher `✉️`, Closer `📞`.

## TASK 11 Runtime Blockers

- Need `DISCORD_WEBHOOK_URL` in `.env` to validate outbound posts.
- Need Discord webhook/channel created from Task 7.
- Discord failures currently print readable console logs and raise to the calling claw.

## TASKS 12-14 Runtime Blockers

- Need `APIFY_TOKEN` in `.env`.
- Need the Apify actor name and input shape verified against the live account.
- Need Supabase credentials/schema ready so scraped leads can be inserted and deduped.
- Need `NEMOTRON_BASE_URL`, `NEMOTRON_MODEL`, and Nemotron credentials or NemoClaw/OpenShell route for live pain extraction.
- Need Python dependencies installed locally for live `httpx`, `supabase`, and `openai` calls.

## TASK 15 Runtime Blockers

- Need live Supabase credentials and schema for Scout heartbeat integration.
- Need a working Apify scrape from Task 12 against Santa Cruz auto repair.
- Need a working Nemotron JSON call from Task 8 for `extract_pain_points`.
- Need Discord webhook URL if Scout heartbeat summaries should post during validation.

## TASK 16 Blockers

- Need a working Nemotron JSON call from Task 8.
- Need at least one qualified lead from Scout or seeded sample lead data.
- Need Python dependencies installed locally for live `openai`, `httpx`, `supabase`, and `playwright` calls.
- Need `playwright install chromium` before screenshot-based critique.
- Need `VERCEL_TOKEN` or Supabase Storage bucket `mockups` plus Supabase credentials before live deploy validation.

## TASK 21 Blockers

- Need at least one lead with `qualification_status` of `qualified_for_mockup` or `qualified_for_rebuild`.
- Need live Nemotron route for actual mockup generation.
- Need Playwright browser install or accept HTML-structure critique fallback.
- Need Vercel or Supabase Storage deploy credentials for hosted mockup URLs.

## TASK 22 Blockers

- Need Supabase URL and anon key for dashboard data reads.
- Need real or seeded leads/actions/generated_sites rows to make the dashboard meaningful.
- Need to decide whether Task 22 should stay read-only or include demo trigger buttons later.

## TASK 24 Blockers

- Need live Nemotron JSON route for email generation.
- Need at least one lead with `worked_by_designer = true`.
- Need a chosen `generated_sites` row with a public mockup URL for the lead.
- Need `leads.email` populated before Pitcher can become useful beyond draft-only output.

## TASK 27 Blockers

- Need live Supabase credentials and schema for Pitcher heartbeat integration.
- Need at least one Designer-completed lead plus chosen mockup URL.
- Need live Nemotron route for generating and critiquing real outreach variants.
- Need Discord webhook if approval summaries should post.
- Need `RESEND_API_KEY`, verified sender/domain, and `OUTREACH_FROM_ADDRESS` before approved emails can send.

## TASK 29 Blockers

- Need seeded or real `inbound` rows before Closer classification is meaningful.
- Need live Nemotron JSON route for reply classification.
- Need Supabase credentials/schema for updating inbound classification fields.
- Need Pitcher/Resend inbound webhook path ready if testing with real replies instead of seeded rows.

## TASK 32 Blockers

- Need seeded or real unhandled `inbound` email rows for the Closer heartbeat.
- Need live Supabase credentials/schema for inbound and meetings writes.
- Need live Nemotron route for classification and reply drafting, or accept fallback drafts for demo.
- Need Google Calendar OAuth credentials for live booking; otherwise `demo-gcal-*` event ids will be used.

## TASK 34 Blockers

- Need representative lead-related rows (`generated_sites`, `outreach`, `inbound`, `meetings`, `actions`) to make the lead detail page useful.
- Need decide whether mockup iframe previews should render `html_content` directly or only public Vercel/Supabase URLs.
- Need dashboard Supabase env values available at build/runtime for live detail reads.

## Remaining Demo Blockers

- Task 0 live completion: install/login to NemoClaw or Brev runtime, run `nemoclaw onboard --sandbox mainstreet`, verify sandbox status/connect, then run the Nemotron and Supabase smoke checks from `nemoclaw/README.md`.
- Need run the rehearsal checklist with real credentials and seeded data.
- Need record the backup demo video before presentation time.
- Need final live monitor pass to tune heartbeat intervals and verify logs.
- Need a bash-capable runtime such as Git Bash, WSL, or NemoClaw shell for live `start_all_claws.sh` and `stop_all_claws.sh` use.
- Need Vapi API key, phone number, public webhook URL, and tunnel/server deployment before live voice validation.
- Need run the rate-limit check in an environment with installed Python dependencies and real Nemotron/Apify credentials.

## Full Local Validation - 2026-05-16

- Git status was clean at validation start on `main` tracking `origin/main`; recent commits included placeholder replacement, Vapi stretch, demo runbook polish, memory/demo scripts, and quality upgrades.
- Python import sweep passed for `agents`, `integrations`, and `workers`.
- `python -m compileall agents integrations workers` passed.
- Claw one-shot checks passed without crashing:
  - `python -m agents.scout.claw --once`
  - `python -m agents.designer.claw --once`
  - `python -m agents.pitcher.claw --once`
  - `python -m agents.closer.claw --once`
- The claws failed gracefully because local runtime dependencies and live credentials are not configured.
- `python -m agents.scripts.rate_limit_check --nemotron-rounds 1 --skip-apify` failed clearly because the local `openai` package is missing.
- `python -m agents.scripts.seed_demo_data --clear` failed clearly because the local `supabase` package is missing.
- `python -m agents.integrations.vapi_client` skipped clearly because `VAPI_WEBHOOK_URL` is not configured.
- Dashboard validation passed:
  - `npm.cmd install --ignore-scripts`
  - `npm.cmd run typecheck`
  - `npm.cmd run build`
- Dashboard build emitted non-fatal webpack cache snapshot warnings.
- npm still reports 2 audit findings: 1 moderate and 1 high. No package upgrades were applied during validation.

## Full Local Validation Blockers - 2026-05-16

- Install Python dependencies with `pip install -r agents/requirements.txt`. Missing locally: `openai`, `supabase`, `httpx`, `playwright`, Discord, Google API, and dotenv packages.
- Configure Supabase env values: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `NEXT_PUBLIC_SUPABASE_URL`, and `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- Apply the Supabase schema and seed demo rows before rehearsal.
- Configure Nemotron/NemoClaw env values: `NVIDIA_API_KEY`, `NEMOTRON_BASE_URL`, and `NEMOTRON_MODEL`.
- Configure live integration keys as needed for the demo path: `APIFY_TOKEN`, `RESEND_API_KEY`, `OUTREACH_FROM_ADDRESS`, `VERCEL_TOKEN`, `DISCORD_WEBHOOK_URL`, and Google Calendar OAuth values.
- Run `playwright install chromium` before screenshot-based Designer validation.
- Use Git Bash, WSL, or NemoClaw shell for `agents/scripts/start_all_claws.sh` and `agents/scripts/stop_all_claws.sh`.
- Configure Vapi stretch values only if voice is included: `VAPI_API_KEY`, `VAPI_PHONE_NUMBER`, and `VAPI_WEBHOOK_URL`.

## Repo Audit Findings - 2026-05-16

- Section 10 Tasks 0-3 and 5-7 remain manual/live-environment incomplete: NemoClaw onboarding, rate-limit run with real credentials, Resend DNS/domain verification, Supabase cloud schema/bucket application, Vercel project, Apify live scrape, and Discord setup.
- Task 6 files are missing: `agents/scripts/test_apify.py` and `agents/scripts/sample_leads.json`.
- Task 30 is missing the one-time OAuth helper script `agents/scripts/gcal_oauth.py`.
- `nemoclaw/README.md` and `nemoclaw/network-policy.md` still contain Task 0 scaffolding instead of verified sandbox commands and exact hostnames.
- `agents/pyproject.toml` is behind `agents/requirements.txt`; it omits `discord.py`, Google Calendar dependencies, and `tzdata`.
- `README.md` Known Gaps is stale: it still calls `rate_limit_check.py`, `dashboard/app/api/discord-reply`, and `dashboard/app/api/trigger-demo` placeholders even though those files now contain working fallback implementations.
- Local validation on this machine: `python3 -m compileall agents integrations workers` passed; `npm run typecheck` and `npm run build` could not run because dashboard dependencies are not installed; preflight reports missing Python packages and required env vars.

## Local Env Notes - 2026-05-16

- Added a Scout-focused `.env` template with required Nemotron, Supabase, and Apify fields plus optional Scout heartbeat tuning.
- Fixed Scout Apify location targeting so the scraper sends `Santa Cruz, CA, United States` instead of bare `Santa Cruz`, preventing Santa Cruz, Spain matches while preserving `leads.city = Santa Cruz`.
- Added an SMTP email provider path for Pitcher so approved outreach can send through a personal Gmail, Outlook, or custom mailbox without Resend domain verification.

## 2026-05-16 14:47 PDT — Industry-Aware Designer Templates

- Added Designer industry profiles for automotive, dental, plumbing, electrical, roofing, landscaping, HVAC, and pet grooming leads.
- Wired the three polished client-facing website layouts to use industry-specific hero copy, services, stats, reviews, process language, and image assets.
- Validation: `python -m compileall agents/designer/tools/generate_mockup.py` passed.
- Validation: generated local smoke HTML for dentist, plumber, and electrician leads; each produced complete HTML with the right business name and industry title.

## 2026-05-16 14:49 PDT — Scout Balancing Schema Fix

- Fixed Scout niche balancing to count leads by `city` and `niche` only because the live `leads` table does not have a `state` column.
- Validation: `python -m compileall agents/scout/claw.py` passed.
- Validation: local query-shape smoke check confirmed `_lead_count` filters on `city` and `niche`, not `state`.

## 2026-05-16 14:59 PDT — Expanded Designer Template Library

- Expanded client-facing Designer mockups from 3 to 8 layouts by adding editorial, booking-first, local-proof, luxury-card, and service-menu templates.
- Added industry-tailored stock photo selection slots for hero, detail, portrait, and texture images so each layout can use different visual assets.
- Kept every new template wired to industry profiles for services, stats, reviews, hero copy, and contact flows.
- Validation: `python -m compileall agents/designer/tools/generate_mockup.py` passed.
- Validation: generated smoke HTML for all 8 template functions using a dental lead; each returned complete HTML with business and industry text.
- Validation: generated smoke HTML across dentist, plumber, electrician, landscaper, pet groomer, roofing, HVAC, and auto detailing leads.

## 2026-05-16 15:12 PDT — Broader Scout Niches

- Replaced narrow trade-service Scout defaults with broader high-volume local categories: restaurant, coffee shop, hair salon, barber shop, gym, day spa, cleaning service, and home services.
- Removed `auto detailing` from Scout defaults and from legacy Supabase target-list handling.
- Added a generic local-business Designer profile so broad Scout categories do not inherit plumbing copy.
- Validation: `python -m compileall agents/scout/claw.py agents/shared/supabase_client.py agents/designer/tools/generate_mockup.py` passed.
- Validation: legacy target niche lists now normalize to the broader default list and custom lists drop `auto detailing`.
- Validation: generated smoke HTML for a coffee shop lead; output was complete and did not contain plumbing copy.

## 2026-05-16 15:15 PDT — Scout Multi-Niche Fallback

- Updated Scout so one empty Places result no longer ends the heartbeat; it now tries up to `SCOUT_NICHE_ATTEMPTS` categories per run, defaulting to 4.
- Switched broad default search terms to plural, Places-friendly queries: restaurants, cafes, hair salons, barbers, fitness centers, spas, house cleaners, and contractors.
- Updated pending-lead processing to pull from all attempted niches in the heartbeat.
- Validation: `python -m compileall agents/scout/claw.py agents/shared/supabase_client.py` passed.
- Validation: local smoke check confirmed selected niche ordering and legacy singular target normalization.

## 2026-05-16 15:21 PDT — Scout Demo Lead Safety Net

- Added `SCOUT_DEMO_FALLBACK=true` behavior so Scout seeds one clearly labeled `DEMO - ...` lead when all live scrape attempts insert 0 rows.
- Added optional `SCOUT_TEST_EMAIL` / `OUTREACH_TEST_EMAIL` support so fallback leads can route Pitcher email to a safe test inbox.
- Fallback leads are realistic pending rows with missing websites, review text, rating, phone, and address so Scout can immediately qualify them for Designer.
- Validation: `python -m compileall agents/scout/claw.py` passed.
- Validation: fake insert smoke test confirmed fallback rows are clearly labeled, have `website = null`, and carry `SCOUT_TEST_EMAIL` when set.

## 2026-05-16 15:45 PDT — Pitcher Email-Aware Queue

- Updated Pitcher lead selection to scan the Designer-completed queue and skip leads without an email address.
- Pitcher now returns the first eligible lead that has both a recipient email and a generated mockup instead of burning the heartbeat on an unsendable lead.
- Validation: `python -m compileall agents/shared/supabase_client.py` passed.

## 2026-05-16 15:55 PDT — Email-Gated Pipeline

- Updated Scout qualification to skip leads with no email address before they enter the Designer queue.
- Updated Designer lead selection to scan past any qualified but no-email lead and only build websites for leads that Pitcher can contact.
- Validation: `python -m compileall agents/scout/claw.py agents/shared/supabase_client.py` passed.
- Validation: local Scout qualification smoke check skips no-email leads and qualifies email-ready missing-website leads.

## 2026-05-16 15:59 PDT — Dashboard Dev Port

- Updated the dashboard `npm run dev` script to run Next.js on port `3002`.
- Updated README and setup notes so dashboard instructions match the fixed dev port.
- Validation: `npm run typecheck` in `dashboard/` passed.

## 2026-05-16 16:07 PDT — Closer Email-Only Flow

- Removed phone-call handling from the Closer runtime path.
- Updated the shared inbound queue helper so Closer only pulls unhandled `email` rows.
- Updated Closer classification copy, tool docs, and README table notes to describe email replies only.
- Validation: `python -m compileall agents/closer/claw.py agents/closer/tools/classify_reply.py agents/shared/supabase_client.py` passed.
- Validation: `git diff --check` passed.

## 2026-05-16 16:18 PDT — Scout Demo Qualification

- Removed website-score thresholds from Scout qualification for the demo pipeline.
- Scout now qualifies any email-ready lead with basic business data as `qualified_for_mockup`.
- Scout still skips rows that are missing an email or are too incomplete to personalize.
- Validation: `python -m compileall agents/scout/claw.py` passed.
- Validation: `git diff --check` passed.

## 2026-05-16 16:30 PDT — Professional Sender Template

- Upgraded Pitcher sent-email HTML from plain paragraph tags to a polished Santa Claws email layout.
- Added a branded header, cleaner typography, footer, and a mockup CTA button when a generated-site URL exists.
- Kept the plain-text email body unchanged for deliverability and fallback clients.
- Validation: `python -m compileall agents/pitcher/tools/send_email.py` passed.
- Validation: local HTML smoke check confirmed the brand, business name, CTA text, and mockup URL render in the outgoing template.
- Validation: `git diff --check` passed.

## 2026-05-16 16:37 PDT — Business-Name Email Greetings

- Updated Pitcher generation prompts to address outreach to the business name instead of an owner or guessed person.
- Added a generation guard that rewrites opening salutations to `Hi {business_name},` before outreach is inserted.
- Validation: `python -m compileall agents/pitcher/tools/generate_email.py` passed.
- Validation: local salutation smoke checks rewrote guessed names while preserving the email body.
- Validation: `git diff --check` passed.

## 2026-05-16 16:45 PDT — Pitcher Email Polish Fixes

- Added deterministic Pitcher cleanup for malformed Vercel links, missing business-name greetings, and lowercase paragraph starts.
- Updated Pitcher prompts to require exact mockup URL copying with no spaces or line breaks inside links.
- Fixed sent-email CTA padding so the button aligns with the main email content.
- Validation: `python -m compileall agents/pitcher/tools/generate_email.py agents/pitcher/tools/send_email.py` passed.
- Validation: local smoke check repaired a broken `vercel. app` URL and capitalized/prepended the business greeting.
- Validation: local HTML smoke check confirmed the CTA uses aligned side padding.
- Validation: `git diff --check` passed.

## 2026-05-16 16:52 PDT — Exact Vercel Link Preservation

- Simplified Pitcher URL cleanup so Vercel-looking links are replaced with the exact stored mockup URL instead of being rebuilt from regex pieces.
- Validation: `python -m compileall agents/pitcher/tools/generate_email.py` passed.
- Validation: local smoke checks confirmed normal and spaced Vercel links preserve the full `https://santa-claws-leq3l8zo2-varad-patwas-projects.vercel.app` format.
- Validation: `git diff --check` passed.

## 2026-05-16 16:59 PDT — Truncated Vercel Link Repair

- Extended Pitcher cleanup to replace links truncated at `.vercel.` with the exact stored mockup URL.
- Added cleanup for spaced decimal ratings such as `4. 9-star`.
- Removed punctuation immediately after mockup URLs so mail clients do not include it in the link.
- Validation: `python -m compileall agents/pitcher/tools/generate_email.py` passed.
- Validation: local smoke check repaired the exact truncated `https://santa-claws-8k1c1migm-varad-patwas-projects. vercel.` body into the full `.vercel.app` URL.
- Validation: `git diff --check` passed.

## 2026-05-16 17:06 PDT — Exact Mockup URL Paste

- Replaced Pitcher URL repair logic with a simple `MOCKUP_URL` token replacement.
- Pitcher prompts no longer receive the real URL; they receive `MOCKUP_URL`, and code pastes the exact stored mockup URL before saving.
- If the model omits the token, Pitcher appends the exact stored mockup URL on its own line.
- Validation: `python -m compileall agents/pitcher/tools/generate_email.py` passed.
- Validation: local smoke checks confirmed the real URL is absent from prompts and exact in saved bodies.
- Validation: `git diff --check` passed.

## 2026-05-16 17:13 PDT — Vercel-Only Email Links

- Updated Pitcher to use only the `generated_sites.vercel_url` cell for outreach mockup links.
- Removed email fallback to `storage_url` / HTML storage links.
- Updated Pitcher lead selection to skip generated-site rows unless `vercel_url` is present.
- Validation: `python -m compileall agents/pitcher/claw.py agents/pitcher/tools/send_email.py agents/shared/supabase_client.py agents/pitcher/tools/generate_email.py` passed.
- Validation: local smoke check confirmed Pitcher ignores `storage_url` when `vercel_url` is missing and pastes the exact Vercel URL when present.
- Validation: `git diff --check` passed.

## 2026-05-16 17:24 PDT — Discord Agent Run Commands

- Added Discord commands to trigger one NemoClaw heartbeat: `RUN SCOUT`, `RUN DESIGNER`, `RUN PITCHER`, `RUN CLOSER`, and `RUN ALL`.
- Commands run `python -m agents.scripts.openclaw_run <claw> --once` in a subprocess and reply with the captured output.
- Updated Discord help text to list the new run commands alongside approvals and plain-English pipeline questions.
- Validation: `python -m compileall workers/discord_bridge.py` passed.
- Validation: local parser smoke check covered run/start commands for all claws and approval non-matches.
- Validation: `git diff --check` passed.

## 2026-05-16 17:32 PDT — Dashboard Mission Control Header

- Removed the "Tonight's route" hero copy from the dashboard.
- Replaced the decorative header panel with a Mission Control panel showing pipeline steps, refresh cadence, and Discord run-command hints.
- Added compact operational cards for shared memory, demo control, and live outputs.
- Validation: `npm run typecheck` in `dashboard/` passed.
- Validation: `git diff --check` passed.

## 2026-05-16 17:40 PDT — Discord Root Env Loading

- Updated the Discord worker to load the repo-root `.env` by absolute path instead of relying on the launch directory.
- Reused the resolved repo root as the subprocess cwd for Discord-run claw commands.
- Validation: `python -m compileall workers/discord_bridge.py` passed.
- Validation: local smoke check confirmed the resolved `.env` path and run-command parser.
- Validation: `git diff --check` passed.

## 2026-05-16 17:47 PDT — Apify Env Diagnostics

- Updated the Apify integration to load the repo-root `.env` by absolute path.
- Added safe Apify token fingerprints to non-2xx Apify errors so stale env loading can be diagnosed without printing secrets.
- Validation: `python -m compileall agents/integrations/apify_client.py` passed.
- Validation: local smoke check confirmed repo `.env` resolution and token fingerprint formatting.
- Validation: `git diff --check` passed.

## 2026-05-16 17:54 PDT — Dashboard Mission Control Removal

- Removed the Mission Control panel from the dashboard header.
- Verified the dashboard no longer contains the Mission Control, pipeline readiness, refresh, step-list, or Discord-controls copy.
- Validation: `npm run typecheck` in `dashboard/` passed.
- Validation: `git diff --check` passed.

## 2026-05-16 18:03 PDT — Hackathon Thumbnail

- Added a 3:2 Santa Claws hackathon submission thumbnail at `dashboard/public/thumbnail.svg`.
- The thumbnail uses the project name, concise value prop, NemoClaw/Nemotron/Supabase badges, and a mockup/agent visual.
- Validation: local SVG smoke check confirmed 1200x800 dimensions and project text.
- Validation: `git diff --check` passed.
