"""Designer tool for generating one HTML mockup variant with Nemotron."""

from __future__ import annotations

from html import escape
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

    business_name = escape(str(lead.get("business_name") or "Local Auto Repair"))
    niche = escape(str(lead.get("niche") or "auto repair"))
    city = escape(str(lead.get("city") or "Santa Cruz"))
    phone = escape(str(lead.get("phone") or "Call now"))
    address = escape(str(lead.get("address") or f"{city}, CA"))
    hours = escape(str(lead.get("hours") or lead.get("opening_hours") or "Call for today's hours"))
    rating = escape(str(lead.get("google_rating") or "local favorite"))
    review_count = escape(str(lead.get("review_count") or ""))
    pain_points = [escape(str(item)) for item in lead.get("top_review_pain_points") or []][:3]
    if not pain_points:
        pain_points = ["clear service menu", "faster appointment booking", "mobile-friendly contact flow"]
    palette = {
        "clean_modern": {
            "body": "bg-slate-50 text-slate-950",
            "hero": "bg-white",
            "hero_panel": "bg-slate-950 text-white",
            "accent": "bg-sky-600 text-white",
            "soft": "bg-sky-50 border-sky-100",
            "label": "text-sky-700",
            "headline": f"Reliable {niche} in {city}, made easy to book",
        },
        "retro_local": {
            "body": "bg-stone-50 text-stone-950",
            "hero": "bg-[#f7f1e7]",
            "hero_panel": "bg-[#12343b] text-white",
            "accent": "bg-red-700 text-white",
            "soft": "bg-teal-50 border-teal-100",
            "label": "text-red-700",
            "headline": f"Straightforward repairs from a local {city} shop",
        },
        "premium": {
            "body": "bg-zinc-50 text-zinc-950",
            "hero": "bg-zinc-950 text-white",
            "hero_panel": "bg-white text-zinc-950",
            "accent": "bg-emerald-500 text-zinc-950",
            "soft": "bg-zinc-100 border-zinc-200",
            "label": "text-emerald-600",
            "headline": f"Confident diagnostics and service for {city} drivers",
        },
    }.get(variant, {})
    if not palette:
        palette = {
            "body": "bg-slate-50 text-slate-950",
            "hero": "bg-white",
            "hero_panel": "bg-slate-950 text-white",
            "accent": "bg-sky-600 text-white",
            "soft": "bg-sky-50 border-sky-100",
            "label": "text-sky-700",
            "headline": f"Reliable {niche} in {city}, made easy to book",
        }

    services = [
        ("Diagnostics", "Clear next steps for warning lights, strange sounds, and drivability issues."),
        ("Brake service", "Pads, rotors, inspections, and safety checks explained in plain language."),
        ("Maintenance", "Oil, fluids, belts, batteries, tires, and seasonal care for daily drivers."),
        ("Appointments", "A simple call-first flow that works on mobile and helps customers act fast."),
    ]
    service_cards = "\n".join(
        f"""
        <article class="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
          <p class="{palette['label']} text-sm font-semibold uppercase tracking-normal">{title}</p>
          <p class="mt-3 text-sm leading-6 text-slate-600">{copy}</p>
        </article>"""
        for title, copy in services
    )
    pain_cards = "\n".join(
        f"""
        <li class="rounded-md border border-slate-200 bg-white p-4 shadow-sm">
          <span class="text-sm font-semibold text-slate-950">Website improvement</span>
          <p class="mt-2 text-sm leading-6 text-slate-600">{item.capitalize()} so customers know what to do next.</p>
        </li>"""
        for item in pain_points
    )
    rating_text = f"{rating} rating" if not review_count else f"{rating} rating from {review_count} reviews"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{business_name} | {niche.title()} in {city}</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="{palette['body']}">
  <header class="border-b border-slate-200 bg-white">
    <div class="mx-auto flex max-w-6xl flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p class="text-xs font-semibold uppercase tracking-normal text-slate-500">{city} {niche}</p>
        <p class="text-lg font-bold tracking-normal text-slate-950">{business_name}</p>
      </div>
      <a class="w-full rounded-md bg-slate-950 px-4 py-3 text-center text-sm font-semibold text-white sm:w-auto" href="tel:{phone}">Call {phone}</a>
    </div>
  </header>
  <main>
    <section class="{palette['hero']} px-5 py-10 sm:py-14">
      <div class="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[1.15fr_0.85fr] lg:items-stretch">
        <div class="flex flex-col justify-center rounded-md border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <p class="{palette['label']} text-sm font-semibold uppercase tracking-normal">{city} drivers</p>
          <h1 class="mt-3 max-w-3xl text-4xl font-bold tracking-normal sm:text-5xl">{palette['headline']}</h1>
          <p class="mt-5 max-w-2xl text-lg leading-8 text-slate-600">A clearer website for {business_name}: practical service information, fast phone access, and a calmer path from problem to appointment.</p>
          <div class="mt-7 flex flex-col gap-3 sm:flex-row">
            <a class="{palette['accent']} rounded-md px-5 py-3 text-center font-semibold shadow-sm" href="tel:{phone}">Call {phone}</a>
            <a class="rounded-md border border-slate-300 bg-white px-5 py-3 text-center font-semibold text-slate-950" href="#contact">Hours and location</a>
          </div>
          <div class="mt-7 grid gap-3 text-sm sm:grid-cols-3">
            <div class="rounded-md border border-slate-200 bg-slate-50 p-3"><strong>Fast</strong><br><span class="text-slate-600">Tap-to-call on mobile</span></div>
            <div class="rounded-md border border-slate-200 bg-slate-50 p-3"><strong>Clear</strong><br><span class="text-slate-600">Services up front</span></div>
            <div class="rounded-md border border-slate-200 bg-slate-50 p-3"><strong>Local</strong><br><span class="text-slate-600">{rating_text}</span></div>
          </div>
        </div>
        <aside class="{palette['hero_panel']} rounded-md p-6 shadow-sm sm:p-8">
          <p class="text-sm font-semibold uppercase tracking-normal opacity-70">Today's service board</p>
          <div class="mt-6 space-y-4">
            <div class="rounded-md bg-white/10 p-4"><p class="font-semibold">Check engine light</p><p class="mt-1 text-sm opacity-75">Diagnostics and clear repair options.</p></div>
            <div class="rounded-md bg-white/10 p-4"><p class="font-semibold">Brake inspection</p><p class="mt-1 text-sm opacity-75">Noise, vibration, and safety checks.</p></div>
            <div class="rounded-md bg-white/10 p-4"><p class="font-semibold">Maintenance visit</p><p class="mt-1 text-sm opacity-75">Oil, fluids, battery, and road-trip readiness.</p></div>
          </div>
        </aside>
      </div>
    </section>
    <section class="px-5 py-10">
      <div class="mx-auto max-w-6xl">
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{service_cards}
        </div>
      </div>
    </section>
    <section class="{palette['soft']} border-y px-5 py-10">
      <div class="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-start">
        <div>
          <p class="{palette['label']} text-sm font-semibold uppercase tracking-normal">What the new site fixes</p>
          <h2 class="mt-2 text-3xl font-bold tracking-normal">Less hunting around. More confident calls.</h2>
          <p class="mt-4 leading-7 text-slate-600">The page puts the shop's phone number, services, trust signals, and location in a simple flow built for repeat local customers.</p>
        </div>
        <ul class="grid gap-3 sm:grid-cols-3">{pain_cards}
        </ul>
      </div>
    </section>
    <section id="contact" class="px-5 py-12">
      <div class="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[1fr_0.8fr]">
        <div class="rounded-md border border-slate-200 bg-white p-6 shadow-sm">
          <p class="{palette['label']} text-sm font-semibold uppercase tracking-normal">Visit or call</p>
          <h2 class="mt-2 text-3xl font-bold tracking-normal">Ready when a customer needs help now.</h2>
          <div class="mt-6 grid gap-4 sm:grid-cols-2">
            <div class="rounded-md bg-slate-50 p-4">
              <p class="text-sm font-semibold text-slate-500">Address</p>
              <p class="mt-1 font-medium">{address}</p>
            </div>
            <div class="rounded-md bg-slate-50 p-4">
              <p class="text-sm font-semibold text-slate-500">Hours</p>
              <p class="mt-1 font-medium">{hours}</p>
            </div>
          </div>
        </div>
        <div class="rounded-md bg-slate-950 p-6 text-white shadow-sm">
          <p class="text-sm font-semibold uppercase tracking-normal text-white/60">Primary action</p>
          <h2 class="mt-2 text-3xl font-bold tracking-normal">Call {business_name}</h2>
          <p class="mt-4 text-white/70">The phone CTA stays visible, readable, and easy to tap from any device.</p>
          <a class="mt-6 block rounded-md bg-white px-5 py-3 text-center font-semibold text-slate-950" href="tel:{phone}">Call {phone}</a>
        </div>
      </div>
    </section>
  </main>
  <footer class="border-t border-slate-200 bg-white px-5 py-6 text-center text-sm text-slate-500">{business_name} - {city} {niche}. Built for clear calls, local trust, and mobile service requests.</footer>
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
