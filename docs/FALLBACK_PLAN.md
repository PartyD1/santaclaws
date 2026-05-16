# Fallback Plan

## Backup Demo Video Checklist

- Record the dashboard home with populated metrics.
- Record one lead detail page with all related sections visible.
- Record the mockup preview and chosen winner.
- Record Pitcher outreach and approval instructions.
- Record an inbound reply moving through Closer.
- Record a booked or demo meeting row.
- Record the action feed showing Scout, Designer, Pitcher, and Closer rows.
- Save the video locally and in a shared location before demo time.

## Exact Backup Demo Path

1. Start on `Mainstreet Dashboard`.
2. Show metrics: leads, qualified, mockups, drafts, sent, replies, meetings.
3. Open `DEMO - Pacific Coast Auto Repair`.
4. Show website score, qualification reason, and generated mockup.
5. Show outreach body and status.
6. Show inbound reply and meeting.
7. Return to activity feed and read two action rows.

## Live API Failure Fallbacks

- Supabase unavailable: use the backup video and local screenshots.
- Nemotron unavailable: show logs with clear skipped memory/generation messages.
- Apify unavailable: use seeded `DEMO -` leads.
- Vercel unavailable: use Supabase Storage or `html_content` iframe previews.
- Resend unavailable: keep outreach in `pending_approval` and show draft quality.
- Google Calendar unavailable: show `demo-gcal-*` meeting rows.
- Discord unavailable: use console approval instructions.

## Last Safe State

- Seeded demo data is acceptable for the final demo if live scraping is unstable.
- One polished mockup is enough if three live variants are slow.
- One Closer inbound classification is enough for the wow moment.
- Stop Scout first if rate limits become noisy; Designer, Pitcher, and Closer are more visible to judges.
