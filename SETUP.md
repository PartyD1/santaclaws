# Mainstreet Team Setup Commands

This file is for the hackathon team only. It is a command scratchpad for getting from a laptop into Brev/Ubuntu/NemoClaw and running the Mainstreet claws.

Replace `santaclaws1` with the Brev instance name if it changes.

## 1. Setting Up Brev

Install or update the Brev CLI on your laptop if needed, then log in:

```bash
brev login
```

Open the Brev instance:

```bash
brev shell santaclaws1
```

If Brev asks you to log in from the browser, finish that flow and wait for the Ubuntu prompt:

```text
ubuntu@...:~$
```

Clone the repo on the Brev Ubuntu box if it is not there yet:

```bash
cd ~
git clone https://github.com/PartyD1/santaclaws.git mainstreet
cd ~/mainstreet
```

If the repo already exists, update it:

```bash
cd ~/mainstreet
git pull
```

Create the Python environment:

```bash
cd ~/mainstreet
sudo apt update
sudo apt install -y python3-venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r agents/requirements.txt
```

Create or edit the environment file:

```bash
cd ~/mainstreet
cp .env.example .env
nano .env
```

Inside Brev/NemoClaw, keep the routed Nemotron settings:

```bash
NEMOTRON_BASE_URL=https://inference.local/v1
NEMOTRON_MODEL=nvidia/nemotron-3-nano-omni-30b-a3b-reasoning
```

Run the preflight checker:

```bash
cd ~/mainstreet
source .venv/bin/activate
python -m agents.scripts.preflight_check --skip-live
```

After Supabase tables are ready, run the live check:

```bash
python -m agents.scripts.preflight_check
```

## 2. Going From Laptop To Brev Ubuntu

From your laptop:

```bash
brev shell santaclaws1
```

Once inside Ubuntu:

```bash
cd ~/mainstreet
source .venv/bin/activate
```

Check where you are:

```bash
pwd
ls -la
```

You should see:

```text
agents
dashboard
docs
nemoclaw
README.md
.env
```

If `.env` is missing:

```bash
cp .env.example .env
nano .env
```

## 3. Going From Ubuntu To NemoClaw

Preferred NemoClaw command if the CLI is available:

```bash
nemoclaw mainstreet status
nemoclaw mainstreet connect
```

On the current Brev box, the NemoClaw install directory has been seen at:

```bash
cd ~/NemoClaw
ls
```

The Mainstreet code should still be run from the repo:

```bash
cd ~/mainstreet
source .venv/bin/activate
```

Confirm the NemoClaw/OpenShell inference route is configured:

```bash
python - <<'PY'
from dotenv import load_dotenv
import os
load_dotenv()
print("NEMOTRON_BASE_URL=", os.getenv("NEMOTRON_BASE_URL"))
print("NEMOTRON_MODEL=", os.getenv("NEMOTRON_MODEL"))
PY
```

Smoke-test Nemotron:

```bash
python -m agents.shared.nemotron_client
```

If that fails with a connection error, the Supabase-backed memory fallback still works after the `agent_memory` table exists, but Nemotron generation/critique may need the NemoClaw route fixed.

## 4. Running Agent Tests Individually

From Brev Ubuntu:

```bash
cd ~/mainstreet
source .venv/bin/activate
```

Run one heartbeat for each claw:

```bash
python -m agents.scripts.openclaw_run scout --once
python -m agents.scripts.openclaw_run designer --once
python -m agents.scripts.openclaw_run pitcher --once
python -m agents.scripts.openclaw_run closer --once
```

Those commands read each claw's `HEARTBEAT.md` entrypoint and load the
OpenClaw-compatible `SOUL.md`, `AGENTS.md`, `TOOLS.md`, and `MEMORY.md`
context before running the heartbeat.

Useful smoke checks:

```bash
python -m agents.scripts.preflight_check
python -m agents.shared.nemotron_client
python -m agents.scripts.rate_limit_check --nemotron-rounds 1 --skip-apify
python -m compileall agents integrations workers
```

Check durable memory after a heartbeat:

```sql
select claw_name, source, pattern, created_at
from agent_memory
order by created_at desc
limit 10;
```

Run that SQL in the Supabase SQL Editor.

## 5. Running The Development Server

On Brev Ubuntu, start the dashboard:

```bash
cd ~/mainstreet/dashboard
npm install
npm run dev
```

Next.js prints the remote port. If it says:

```text
Local: http://localhost:3002
```

then, from a new laptop terminal, forward that Brev port:

```bash
brev port-forward santaclaws1 -p 3000:3002
```

Open this on your laptop:

```text
http://localhost:3000
```

If Next.js uses port `3000`, use:

```bash
brev port-forward santaclaws1 -p 3000:3000
```

## 6. Running Everything

On Brev Ubuntu:

```bash
cd ~/mainstreet
source .venv/bin/activate
python -m agents.scripts.preflight_check
bash agents/scripts/start_all_claws.sh
```

Watch all claw logs:

```bash
tail -f logs/*.log
```

Or watch one claw:

```bash
tail -f logs/scout.log
tail -f logs/designer.log
tail -f logs/pitcher.log
tail -f logs/closer.log
```

Stop all claws:

```bash
bash agents/scripts/stop_all_claws.sh
```

Run the Discord approval worker in a separate terminal if Discord approval is configured:

```bash
cd ~/mainstreet
source .venv/bin/activate
python -m workers.discord_bridge
```

Run the dashboard in another terminal:

```bash
cd ~/mainstreet/dashboard
npm run dev
```

Forward the printed dashboard port from your laptop:

```bash
brev port-forward santaclaws1 -p 3000:<remote-port>
```

Open:

```text
http://localhost:3000
```

Seed fallback demo data if the dashboard is empty:

```bash
cd ~/mainstreet
source .venv/bin/activate
python -m agents.scripts.seed_demo_data
```

Clear and reseed demo data:

```bash
python -m agents.scripts.seed_demo_data --clear
```
