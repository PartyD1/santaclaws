# NemoClaw Setup

This repo expects a NemoClaw/OpenShell sandbox named `mainstreet`. NemoClaw is
the runtime story for the demo: secure always-on claws, Supabase shared memory,
and Nemotron reasoning through the managed `inference.local` route (no API key
needed inside the sandbox).

## Quickstart (3 steps)

```bash
# 1. Host — create the sandbox and add network policies
bash nemoclaw/install_and_onboard.sh

# 2. Host — open a shell inside the sandbox
nemoclaw mainstreet connect

# 3. Sandbox — install deps and start all 5 agents
bash /workspace/mainstreet/nemoclaw/start_inside_sandbox.sh
```

After step 3, all agents run inside the sandbox. Stream logs from the host:

```bash
nemoclaw mainstreet logs --follow
```

## Monitoring

```bash
nemoclaw mainstreet status          # sandbox health + inference status
nemoclaw mainstreet logs --follow   # live agent output
nemoclaw mainstreet doctor          # diagnose problems
```

## Inference Routing

Inside the sandbox `NEMOTRON_BASE_URL` automatically resolves to
`https://inference.local/v1` — no `NVIDIA_API_KEY` required.

Outside the sandbox (local dev fallback), set:

```
NEMOTRON_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_API_KEY=<your key>
```

See `nemoclaw/model-routing.md` for details.

## Network Policies

Required egress domains are listed in `nemoclaw/network-policy.md`.
`install_and_onboard.sh` adds the `discord` preset automatically. For other
services (Supabase, Apify, Resend, Vercel, Google APIs), add policies as needed:

```bash
nemoclaw mainstreet policy-add <preset-name>
```

## Task 0 Completion Criteria

- `nemoclaw mainstreet status` reports a running sandbox.
- `python3 -m agents.shared.nemotron_client` prints `OK` (via `inference.local`).
- `python3 -m agents.scripts.preflight_check` reaches Supabase and all expected tables.
