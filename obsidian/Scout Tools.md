---
tags: [scout, tools]
claw: scout
---

# Scout Tools

> [[Scout Memory]] | [[Scout Soul]] | [[Scout Tools]] | [[Scout Agents]] | [[Scout Heartbeat]]

- `scrape_leads.run(city: str, niche: str, limit: int = 20) -> int`
  Scrapes Apify Google Places, dedupes by business name and address, inserts new lead rows.

- `score_website.run(url: str | None, lead_id: str | None = None) -> dict`
  Scores a website from 0-10 and returns short reasons.

- `extract_pain_points.run(lead: dict | UUID | str) -> list[str]`
  Uses Nemotron to extract up to three recurring complaints from review text.
