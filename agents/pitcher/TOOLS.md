# Pitcher Tools

- `generate_email.run(lead, mockup_url, angle) -> dict`
- `critique_email.run(subject, body, lead, mockup_url=None) -> dict`
- `send_email.run(outreach_id) -> dict`

Supported angles:

- `specific_pain`
- `competitor_comparison`
- `social_proof`
- `curiosity`

Approval commands are handled by `workers.discord_bridge`:

- `APPROVE <outreach_id>`
- `SKIP <outreach_id>`
- `EDIT <outreach_id> <new body>`
