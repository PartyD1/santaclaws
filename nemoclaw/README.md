# NemoClaw Setup

This repo expects a NemoClaw/OpenShell sandbox named `mainstreet`. NemoClaw is
the runtime story for the demo: secure always-on claws, Supabase shared memory,
and Nemotron reasoning through the sandbox route.

## Local Prereq Check

From the repo root:

```bash
bash nemoclaw/install_and_onboard.sh
```

If the script warns that `nemoclaw` is missing, install/login to NemoClaw or
the Brev early-preview runtime first.

## Sandbox Onboarding

Run these from the machine where the NemoClaw CLI is installed:

```bash
nemoclaw onboard --sandbox mainstreet
nemoclaw mainstreet status
nemoclaw mainstreet connect
```

Inside the sandbox:

```bash
cd /workspace/mainstreet
python3 --version
python3 -m pip install -r agents/requirements.txt
python3 -m agents.shared.nemotron_client
python3 -m agents.scripts.preflight_check --skip-live
python3 -m agents.scripts.preflight_check
python3 -m agents.scripts.rate_limit_check --nemotron-rounds 3 --skip-apify
```

Task 0 is complete only when:

- `nemoclaw mainstreet status` reports a running sandbox.
- `python3 -m agents.shared.nemotron_client` prints `OK`.
- `python3 -m agents.scripts.preflight_check` can reach Supabase and query all expected tables.

Record the exact working CLI/install command here once NemoClaw is available:

```bash
# TODO(Task 0 live): paste the official install/login command used by the team.
```
