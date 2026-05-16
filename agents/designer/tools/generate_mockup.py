"""Designer tool for generating one HTML mockup variant with Nemotron."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.shared import nemotron_client
from agents.shared.logger import logger


PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"
VALID_VARIANTS = {"clean_modern", "retro_local", "premium"}


def _safe_log(action_type: str, status: str, message: str, lead_id: str | None, result: dict[str, Any]) -> None:
    """Best-effort action logging."""

    try:
        logger.log("designer", action_type, status, message, lead_id=lead_id, result=result)
    except Exception as exc:  # pragma: no cover - local/no-credential path.
        print(f"Designer log skipped: {exc}")


def _lead_id(lead: dict[str, Any]) -> str | None:
    """Return a string lead id when present."""

    value = lead.get("id")
    return None if value is None else str(value)


def _variant_block(variant: str) -> str:
    """Load the variant style block."""

    if variant not in VALID_VARIANTS:
        raise ValueError(f"Unknown mockup variant: {variant}")
    return (PROMPT_DIR / f"variants_{variant}.txt").read_text(encoding="utf-8")


def _previous_critique_block(previous_critique: dict[str, Any] | None) -> str:
    """Format prior critique feedback for regeneration."""

    if not previous_critique:
        return ""
    return (
        "Previous critique to fix:\n"
        f"- Score: {previous_critique.get('score')}\n"
        f"- Issues: {previous_critique.get('issues', [])}\n"
        f"- Suggestions: {previous_critique.get('suggestions', [])}"
    )


def _prompt(lead: dict[str, Any], variant: str, previous_critique: dict[str, Any] | None) -> str:
    """Build the generation prompt."""

    template = (PROMPT_DIR / "designer_generate.txt").read_text(encoding="utf-8")
    return template.format(
        business_name=lead.get("business_name", "Unknown business"),
        niche=lead.get("niche", "auto repair"),
        city=lead.get("city", ""),
        address=lead.get("address") or "Address not listed",
        phone=lead.get("phone") or "Phone not listed",
        hours=lead.get("hours") or lead.get("opening_hours") or "Hours not listed",
        rating=lead.get("google_rating") or "unknown",
        review_count=lead.get("review_count") or 0,
        pain_points=", ".join(lead.get("top_review_pain_points") or []) or "none provided",
        variant_name=variant,
        variant_style_block=_variant_block(variant),
        previous_critique_block=_previous_critique_block(previous_critique),
    )


def _valid_html(html: str, business_name: str | None = None) -> bool:
    """Validate the minimum contract for generated HTML."""

    lowered = html.lower()
    if "<!doctype" not in lowered or "</html>" not in lowered:
        return False
    if business_name and business_name.lower() not in lowered:
        return False
    return True


def _fallback_html(lead: dict[str, Any], variant: str, reason: str) -> str:
    """Build a deterministic demo mockup when Nemotron is unavailable."""

    business_name = str(lead.get("business_name") or "Local Auto Repair")
    city = str(lead.get("city") or "Santa Cruz")
    phone = str(lead.get("phone") or "Call now")
    address = str(lead.get("address") or f"{city}, CA")
    rating = lead.get("google_rating") or "local favorite"
    pain_points = [str(item) for item in lead.get("top_review_pain_points") or []][:3]
    if not pain_points:
        pain_points = ["clear service menu", "faster appointment booking", "mobile-friendly contact flow"]
    style = {
        "clean_modern": ("bg-slate-950", "bg-sky-500", "Clean, fast, and mobile-ready"),
        "retro_local": ("bg-emerald-950", "bg-amber-400", "Trusted neighborhood service"),
        "premium": ("bg-zinc-950", "bg-rose-500", "Premium care without the dealership wait"),
    }.get(variant, ("bg-slate-950", "bg-sky-500", "Built for local trust"))
    hero_bg, accent_bg, headline = style
    pain_items = "\n".join(f"<li>{item}</li>" for item in pain_points)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{business_name} | Auto Repair in {city}</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-white text-slate-950">
  <main>
    <section class="{hero_bg} px-6 py-16 text-white">
      <div class="mx-auto max-w-5xl">
        <p class="text-sm font-semibold uppercase tracking-normal text-white/70">{city} auto repair</p>
        <h1 class="mt-4 max-w-3xl text-5xl font-bold tracking-normal">{business_name}</h1>
        <p class="mt-5 max-w-2xl text-xl text-white/80">{headline}. Book service, ask a question, or get a quote from a shop people already trust.</p>
        <div class="mt-8 flex flex-wrap gap-3">
          <a class="{accent_bg} rounded-md px-5 py-3 font-semibold text-white" href="tel:{phone}">Call {phone}</a>
          <a class="rounded-md border border-white/30 px-5 py-3 font-semibold text-white" href="#contact">Get directions</a>
        </div>
      </div>
    </section>
    <section class="px-6 py-12">
      <div class="mx-auto grid max-w-5xl gap-8 md:grid-cols-3">
        <div>
          <h2 class="text-2xl font-bold tracking-normal">Services</h2>
          <p class="mt-3 text-slate-600">Diagnostics, brakes, oil changes, tune-ups, and repair guidance for local drivers.</p>
        </div>
        <div>
          <h2 class="text-2xl font-bold tracking-normal">Why customers call</h2>
          <ul class="mt-3 list-disc space-y-2 pl-5 text-slate-600">{pain_items}</ul>
        </div>
        <div id="contact">
          <h2 class="text-2xl font-bold tracking-normal">Contact</h2>
          <p class="mt-3 text-slate-600">{address}</p>
          <p class="mt-2 text-slate-600">Rating: {rating}</p>
          <a class="mt-5 inline-block rounded-md bg-slate-950 px-5 py-3 font-semibold text-white" href="tel:{phone}">Schedule service</a>
        </div>
      </div>
    </section>
  </main>
  <footer class="px-6 py-8 text-center text-sm text-slate-500">Demo Mainstreet mockup generated by Designer fallback. Reason: {reason[:160]}</footer>
</body>
</html>"""


def run(lead: dict[str, Any], variant: str, previous_critique: dict[str, Any] | None = None) -> str:
    """Generate a valid single-file Tailwind HTML mockup."""

    lead_id = _lead_id(lead)
    business_name = str(lead.get("business_name") or "")
    user_prompt = _prompt(lead, variant, previous_critique)
    last_payload: dict[str, Any] | None = None

    for attempt in range(2):
        try:
            payload = nemotron_client.chat_json(
                system="You are Designer, a NemoClaw claw generating Tailwind HTML mockups. Return JSON only.",
                user=user_prompt,
                retries=1,
            )
        except Exception as exc:
            html = _fallback_html(lead, variant, str(exc))
            _safe_log(
                "generate_mockup",
                "succeeded",
                f"generated fallback {variant} mockup for {business_name}.",
                lead_id,
                {"variant": variant, "attempt": attempt + 1, "fallback_reason": str(exc)},
            )
            return html
        last_payload = payload
        html = str(payload.get("html") or "").strip()
        if _valid_html(html, business_name):
            _safe_log(
                "generate_mockup",
                "succeeded",
                f"generated {variant} mockup for {business_name}.",
                lead_id,
                {"variant": variant, "attempt": attempt + 1},
            )
            return html
        user_prompt += "\n\nPrevious output was malformed. Regenerate one complete HTML document in JSON."

    _safe_log(
        "generate_mockup",
        "failed",
        f"failed to generate valid {variant} mockup for {business_name}.",
        lead_id,
        {"variant": variant, "last_payload": last_payload},
    )
    raise ValueError(f"Nemotron returned invalid HTML for variant {variant}.")
