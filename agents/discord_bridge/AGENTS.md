# Discord Bridge Instructions

Discord Bridge runs as a long-lived bot process that handles one message at a time.

Workflow:

1. Connect to Discord using DISCORD_BOT_TOKEN.
2. Listen in the channel specified by DISCORD_APPROVAL_CHANNEL_ID.
3. On each message:
   a. If it matches PING or HELP — reply with usage instructions.
   b. If it matches APPROVE / SKIP / EDIT <outreach_id> [new body] — apply the decision
      to the `outreach` and `approvals` tables, then reply with confirmation.
   c. Otherwise — treat it as a plain-English pipeline question, gather pipeline context,
      call Nemotron for an answer under 400 characters, and reply.
4. Log every approval action to the `actions` table.

Do not call Scout, Designer, Pitcher, or Closer directly. Supabase is the handoff.
