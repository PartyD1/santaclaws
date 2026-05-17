# Discord Bridge Tools

- `parse_command(content: str) -> ApprovalCommand | None`
  Parses APPROVE / SKIP / EDIT commands from raw Discord message text.

- `apply_command(command: ApprovalCommand, decided_by: str) -> dict`
  Writes approval decision to `outreach` and `approvals` tables in Supabase.

- `handle_query(message) -> None`
  Gathers pipeline context and calls Nemotron to answer a plain-English question.

- `run_bot() -> int`
  Starts the Discord client and blocks until the bot disconnects or credentials are missing.
