---
tags: [guide, docs]
---

# Obsidian Vault — Usage Guide

This vault mirrors live memory from all four Mainstreet NemoClaw agents. Notes update automatically every time a claw writes a memory entry.

---

## Opening the Vault

### Browser via SSH tunnel (recommended)
Port 6080 is not publicly exposed. First open the tunnel from your local machine:
```bash
ssh -L 6080:localhost:6080 ubuntu@35.197.1.31 -N
```
Keep that terminal open, then visit:
```
http://localhost:6080/vnc.html
```
Click **Connect** — no password required.

### Browser (direct — requires GCP firewall rule for port 6080)
If you've opened port 6080 in the GCP VPC firewall:
```
http://35.197.1.31:6080/vnc.html
```

### Locally (recommended for speed)
1. Install [Obsidian](https://obsidian.md) on your machine
2. Clone or pull the repo — the vault is at `obsidian/` in the project root
3. Open Obsidian → **Open folder as vault** → select the `obsidian/` directory
4. Notes stay fresh via `git pull` or Obsidian Sync

---

## Vault Structure

| Note | Contents |
| --- | --- |
| [[Home]] | Index page — links to all four agents and pipeline overview |
| [[Scout Memory]] | Lead scraping results, qualification counts, Apify errors |
| [[Designer Memory]] | Mockup generation outcomes, winning variants, deploy URLs |
| [[Pitcher Memory]] | Outreach email angles, approval results |
| [[Closer Memory]] | Reply classifications, meeting booking outcomes |
| [[Guide]] | This file |

---

## Key Views

### Graph view (`Ctrl+G`)
Shows all agent notes as nodes connected by pipeline wikilinks. Use this to see the full agent chain at a glance.

### Quick switcher (`Ctrl+O`)
Type any agent name to jump directly to its memory note.

### Search (`Ctrl+Shift+F`)
Full-text search across all memory entries. Useful searches:
- `#error` — all entries tagged as errors across every agent
- `error` — free-text search for error messages
- `mockup` — find all designer mockup decisions
- `Santa Cruz` — filter by target city

### Tag pane (left sidebar → Tags icon)
Browse entries by `#memory`, `#scout`, `#designer`, `#pitcher`, `#closer`.

---

## How Live Sync Works

Every claw heartbeat that produces a durable memory pattern calls:

```
memory_updater._persist_memory()
  ├── insert_memory()        → Supabase agent_memory table
  ├── append_memory()        → agents/{claw}/MEMORY.md  (compatibility cache)
  └── obsidian_writer.append_entry()  → obsidian/{Claw} Memory.md  ← this vault
```

The Obsidian write is best-effort — a failure there never breaks a claw.

---

## Rebuilding the Vault

If you clear the database or want to reset all notes from the local `MEMORY.md` files:

```bash
source .venv/bin/activate
python -c "from agents.shared.obsidian_writer import init_vault; init_vault()"
```

This is safe to re-run at any time — it overwrites the four agent notes from current `MEMORY.md` content.

---

## Entry Format

Each observation in an agent note looks like:

```
### 2026-05-16 19:37 UTC
✅ Scout processed 5 auto repair leads in Santa Cruz: 3 mockup, 0 rebuild, 2 skipped.

### 2026-05-16 19:31 UTC
❌ Last scout heartbeat had a recoverable error: Apify rejected with HTTP 402.
```

- `✅` — normal observation (no "error" in the text)
- `❌` — recoverable error logged by the claw
- Timestamps are always UTC

---

## Restarting the VNC Stack

If the browser VNC session drops, restart everything with:

```bash
# Kill existing processes
pkill Xvfb; pkill x11vnc; pkill websockify; pkill obsidian

# Restart virtual display
Xvfb :99 -screen 0 1920x1080x24 &

# Restart VNC + noVNC proxy
x11vnc -display :99 -nopw -listen localhost -forever &
websockify --web=/usr/share/novnc/ 6080 localhost:5900 &

# Relaunch Obsidian
DISPLAY=:99 obsidian --no-sandbox --disable-gpu &
```
