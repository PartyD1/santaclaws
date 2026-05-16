# Placeholder Audit

## Must-Implement Before Demo

- `integrations/*.py`: replaced task placeholders with compatibility imports to the implemented `agents.integrations` clients.
- `agents/scripts/rate_limit_check.py`: implemented Nemotron and Apify smoke/rate checks.
- `agents/scripts/nuke_db.py`: replaced unsafe reset placeholder with guarded demo-data cleanup only.
- `dashboard/app/api/discord-reply/route.ts`: implemented minimal approval command handler.
- `dashboard/app/api/trigger-demo/route.ts`: implemented demo inbound trigger using seeded `DEMO -` leads.
- `dashboard/lib/supabase-server.ts`: implemented server Supabase client helper.
- `workers/inbound_email_worker.py`: replaced placeholder with an operator-facing status helper.
- `nemoclaw/install_and_onboard.sh`: replaced placeholder with a practical onboarding checklist.
- `agents/nemoclaw.json`: removed stale placeholder wording.

## Acceptable Placeholders

- `agents/*/MEMORY.md`: intentionally starts with "No observations yet"; memory updater appends real observations.
- Package `__init__.py` files: intentionally small package markers.
- `docker-compose.yml`: intentionally empty because local Supabase is optional and the demo uses cloud Supabase.
- `agents/shared/nemotron_client.py`: the `openshell` placeholder API key is intentional for the NemoClaw/OpenShell inference route.
- `docs/Mainstreet_NemoClaw_Codex_Execution_Spec.md`: still contains historical placeholder wording in task descriptions.

## Safe To Delete

- None deleted. The remaining small files either preserve package imports, document optional runtime setup, or are referenced by the execution spec.
