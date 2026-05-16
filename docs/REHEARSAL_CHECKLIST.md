# Rehearsal Checklist

## Before Rehearsal

- Apply Supabase schema and seed demo data.
- Verify dashboard build and dev server.
- Verify all four claws run once without crashing.
- Confirm one good mockup URL or `html_content` preview is available.
- Confirm one inbound reply exists for Closer.
- Assign roles: driver, narrator, log watcher, backup operator.

## Three-Minute Version

1. Driver opens dashboard home.
2. Narrator: "Mainstreet NemoClaw runs four claws for local-business outreach."
3. Driver opens a qualified lead.
4. Narrator points to mockup winner, critique score, and iteration count.
5. Driver shows outreach and inbound reply.
6. Driver refreshes action feed or waits for polling.
7. Narrator closes: "The system found the lead, made the mockup, drafted outreach, classified the reply, and prepared the meeting path."

## Five-Minute Version

1. Driver opens dashboard metrics and claw cards.
2. Narrator explains Scout, Designer, Pitcher, Closer in one sentence each.
3. Driver opens lead detail and mockup preview.
4. Narrator calls out self-critique and winner selection.
5. Driver opens Discord approval or Supabase outreach row.
6. Narrator explains Pitcher's four-angle email selection.
7. Driver shows inbound reply and Closer classification.
8. Driver shows meeting row or Calendar.
9. Narrator finishes on action feed and MEMORY.md update.

## Who Clicks What

- Driver: dashboard, lead detail, Discord, Calendar.
- Log watcher: terminal logs and `logs/*.log`.
- Backup operator: runs seeder, restarts claws, opens fallback screenshots/video.
- Narrator: stays hands-free and keeps the story moving.

## Failure Lines

- Empty dashboard: "We seeded a fallback set so the judges can still inspect the full pipeline shape."
- Nemotron outage: "The architecture fails visibly: each claw logs the skipped model step instead of pretending it succeeded."
- Email not sending: "Pitcher still produced and queued the approved draft; Resend is the only blocked external hop."
- Calendar not booking: "Closer proposed safe slots and wrote a demo meeting row, which is the intended fallback."

## Final Pass

- Run the three-minute version twice.
- Run the five-minute version once with an intentional API failure.
- Record screen and audio after the second clean run.
- Stop claws when rehearsal is complete.
