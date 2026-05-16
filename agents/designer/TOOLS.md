# Designer Tools

- `generate_mockup.run(lead: dict, variant: str, previous_critique: dict | None = None) -> str`
  Generates a single-file Tailwind HTML mockup through Nemotron.

- `screenshot_html.run(html: str) -> bytes`
  Screenshots generated HTML with Playwright.

- `critique_mockup.run(html: str, lead: dict) -> dict`
  Critiques a mockup with Nemotron vision, falling back to HTML checks.

- `deploy_to_vercel.run(html: str, slug: str, lead_id: str | None = None) -> dict`
  Deploys through Vercel with Supabase Storage fallback.

- `pick_winner.run(lead: dict, variants: list[dict]) -> dict`
  Picks the best variant using business context and critique scores.
