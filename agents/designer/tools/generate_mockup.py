"""Designer tool for generating one HTML mockup variant with Nemotron."""

from __future__ import annotations

import os
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


def _template_mode_enabled() -> bool:
    """Return True when Designer should render through local premium templates."""

    return os.environ.get("DESIGNER_USE_NEMOTRON_HTML", "").strip().lower() not in {"1", "true", "yes"}


def _website_score(lead: dict[str, Any]) -> int:
    """Return the Scout website score when available."""

    try:
        return max(0, min(10, int(lead.get("website_score") or 0)))
    except (TypeError, ValueError):
        return 0


def _audit_stats(lead: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Build demo-safe opportunity stats from Scout's audit fields."""

    score = _website_score(lead)
    phone_score = 2 if score <= 3 else 3 if score <= 6 else 4
    trust_score = 2 if score <= 4 else 3 if score <= 7 else 4
    mobile_score = 1 if score <= 3 else 3 if score <= 6 else 4
    return [
        ("Current site score", f"{score}/10", "Scout audit"),
        ("Mobile CTA clarity", f"{phone_score}/5", "Estimated from page scan"),
        ("Trust signal coverage", f"{trust_score}/5", "Estimated rebuild opportunity"),
        ("Local SEO readiness", f"{mobile_score}/5", "Estimated visibility lift"),
    ]


def _fallback_html(lead: dict[str, Any], variant: str, reason: str = "template renderer") -> str:
    """Build a deterministic professional mockup template."""

    business_name = escape(str(lead.get("business_name") or "Local Auto Repair"))
    niche = escape(str(lead.get("niche") or "auto repair"))
    city = escape(str(lead.get("city") or "Santa Cruz"))
    phone = escape(str(lead.get("phone") or "Call now"))
    address = escape(str(lead.get("address") or f"{city}, CA"))
    hours = escape(str(lead.get("hours") or lead.get("opening_hours") or "Call for today's hours"))
    rating = escape(str(lead.get("google_rating") or "local favorite"))
    review_count = escape(str(lead.get("review_count") or ""))
    website_score = _website_score(lead)
    score_reasons = [escape(str(item)) for item in lead.get("website_score_reasons") or []][:4]
    if not score_reasons:
        score_reasons = ["mobile call path can be clearer", "services should be easier to scan", "trust cues need stronger placement"]
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
            "ring": "ring-sky-200",
            "gradient": "from-sky-50 via-white to-emerald-50",
            "headline": f"Reliable {niche} in {city}, made easy to book",
        },
        "retro_local": {
            "body": "bg-stone-50 text-stone-950",
            "hero": "bg-[#f7f1e7]",
            "hero_panel": "bg-[#12343b] text-white",
            "accent": "bg-red-700 text-white",
            "soft": "bg-teal-50 border-teal-100",
            "label": "text-red-700",
            "ring": "ring-red-200",
            "gradient": "from-[#f7f1e7] via-white to-teal-50",
            "headline": f"Straightforward repairs from a local {city} shop",
        },
        "premium": {
            "body": "bg-zinc-50 text-zinc-950",
            "hero": "bg-zinc-950 text-white",
            "hero_panel": "bg-white text-zinc-950",
            "accent": "bg-emerald-500 text-zinc-950",
            "soft": "bg-zinc-100 border-zinc-200",
            "label": "text-emerald-600",
            "ring": "ring-emerald-200",
            "gradient": "from-zinc-950 via-zinc-900 to-emerald-950",
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
            "ring": "ring-sky-200",
            "gradient": "from-sky-50 via-white to-emerald-50",
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
    audit_cards = "\n".join(
        f"""
        <div class="rounded-md border border-slate-200 bg-white p-4 shadow-sm">
          <p class="text-xs font-semibold uppercase tracking-normal text-slate-500">{label}</p>
          <p class="mt-2 text-3xl font-bold tracking-normal text-slate-950">{value}</p>
          <p class="mt-2 text-sm text-slate-500">{caption}</p>
        </div>"""
        for label, value, caption in _audit_stats(lead)
    )
    reason_items = "\n".join(
        f"""<li class="flex gap-3"><span class="mt-2 h-2 w-2 shrink-0 rounded-full bg-slate-950"></span><span>{item.capitalize()}</span></li>"""
        for item in score_reasons
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
  <header class="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
    <div class="mx-auto flex max-w-6xl flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p class="text-xs font-semibold uppercase tracking-normal text-slate-500">{city} {niche}</p>
        <p class="text-lg font-bold tracking-normal text-slate-950">{business_name}</p>
      </div>
      <a class="w-full rounded-md bg-slate-950 px-4 py-3 text-center text-sm font-semibold text-white sm:w-auto" href="tel:{phone}">Call {phone}</a>
    </div>
  </header>
  <main>
    <section class="{palette['hero']} bg-gradient-to-br {palette['gradient']} px-5 py-10 sm:py-14">
      <div class="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[1.15fr_0.85fr] lg:items-stretch">
        <div class="flex flex-col justify-center rounded-md border border-slate-200 bg-white p-6 shadow-sm ring-1 {palette['ring']} sm:p-8">
          <p class="{palette['label']} text-sm font-semibold uppercase tracking-normal">Mainstreet rebuild preview for {city} drivers</p>
          <h1 class="mt-3 max-w-3xl text-4xl font-bold tracking-normal sm:text-5xl">{palette['headline']}</h1>
          <p class="mt-5 max-w-2xl text-lg leading-8 text-slate-600">A sharper front door for {business_name}: practical service information, fast phone access, trust cues above the fold, and a calmer path from problem to appointment.</p>
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
          <div class="mt-6 rounded-md bg-white/10 p-4">
            <p class="text-sm font-semibold opacity-80">Scout audit score</p>
            <p class="mt-1 text-4xl font-bold tracking-normal">{website_score}/10</p>
            <p class="mt-1 text-sm opacity-70">Used to guide this rebuild preview.</p>
          </div>
        </aside>
      </div>
    </section>
    <section class="px-5 py-10">
      <div class="mx-auto max-w-6xl">
        <div class="mb-5 flex flex-col justify-between gap-2 sm:flex-row sm:items-end">
          <div>
            <p class="{palette['label']} text-sm font-semibold uppercase tracking-normal">Opportunity snapshot</p>
            <h2 class="mt-2 text-3xl font-bold tracking-normal">A page built around measurable customer friction.</h2>
          </div>
          <p class="max-w-xl text-sm leading-6 text-slate-600">These are demo-safe estimates derived from Scout's website audit, not claims about shop revenue or operations.</p>
        </div>
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{audit_cards}
        </div>
      </div>
    </section>
    <section class="px-5 py-10">
      <div class="mx-auto max-w-6xl">
        <div class="mb-5">
          <p class="{palette['label']} text-sm font-semibold uppercase tracking-normal">Service clarity</p>
          <h2 class="mt-2 text-3xl font-bold tracking-normal">Customers can understand the shop in seconds.</h2>
        </div>
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
          <ul class="mt-5 space-y-3 text-sm leading-6 text-slate-700">{reason_items}
          </ul>
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


def _agency_template_html(lead: dict[str, Any], variant: str, reason: str = "template renderer") -> str:
    """Render a more polished agency-style website preview."""

    business_name = escape(str(lead.get("business_name") or "Local Auto Repair"))
    niche = escape(str(lead.get("niche") or "auto repair"))
    city = escape(str(lead.get("city") or "Santa Cruz"))
    phone = escape(str(lead.get("phone") or "Call now"))
    address = escape(str(lead.get("address") or f"{city}, CA"))
    hours = escape(str(lead.get("hours") or lead.get("opening_hours") or "Call for today's hours"))
    rating = escape(str(lead.get("google_rating") or "4.8"))
    review_count = escape(str(lead.get("review_count") or "local"))
    score = _website_score(lead)
    score_reasons = [escape(str(item)).capitalize() for item in lead.get("website_score_reasons") or []][:3]
    if not score_reasons:
        score_reasons = ["Phone CTA is hard to find", "Service menu needs more clarity", "Trust proof is buried"]
    pain_points = [escape(str(item)).capitalize() for item in lead.get("top_review_pain_points") or []][:3]
    if not pain_points:
        pain_points = ["Make booking obvious", "Clarify repair categories", "Surface local trust faster"]

    themes = {
        "clean_modern": {
            "bg": "#f6f8fb",
            "ink": "#101828",
            "muted": "#667085",
            "panel": "#ffffff",
            "dark": "#111827",
            "accent": "#0ea5e9",
            "accent2": "#16a34a",
            "soft": "#e0f2fe",
            "hero": "Precision repair, clear answers, faster bookings.",
        },
        "retro_local": {
            "bg": "#f8f4ed",
            "ink": "#172426",
            "muted": "#66706b",
            "panel": "#fffaf1",
            "dark": "#12343b",
            "accent": "#b42318",
            "accent2": "#0f766e",
            "soft": "#fef3c7",
            "hero": "A sharper digital front door for a trusted neighborhood shop.",
        },
        "premium": {
            "bg": "#f4f4f5",
            "ink": "#111111",
            "muted": "#71717a",
            "panel": "#ffffff",
            "dark": "#09090b",
            "accent": "#10b981",
            "accent2": "#38bdf8",
            "soft": "#dcfce7",
            "hero": "Dealer-level confidence with independent-shop clarity.",
        },
    }
    theme = themes.get(variant, themes["clean_modern"])

    reasons = "".join(f"<li>{item}</li>" for item in score_reasons)
    pains = "".join(
        f"""
        <article>
          <span>0{index}</span>
          <h3>{item}</h3>
          <p>Turn this friction into a clear service path with stronger copy, faster calls, and better section hierarchy.</p>
        </article>"""
        for index, item in enumerate(pain_points, start=1)
    )
    stats = [
        ("Audit score", f"{score}/10", "Scout website scan"),
        ("CTA clarity", "High lift", "Phone-first rebuild"),
        ("Trust path", "Above fold", "Rating, reviews, services"),
        ("Demo read", "30 sec", "Judges see the story fast"),
    ]
    stat_cards = "".join(f"<div><span>{label}</span><strong>{value}</strong><small>{caption}</small></div>" for label, value, caption in stats)
    service_cards = "".join(
        f"""
        <article>
          <div>{number}</div>
          <h3>{title}</h3>
          <p>{copy}</p>
        </article>"""
        for number, title, copy in [
            ("01", "Diagnostics", "Make warning lights, noises, and performance issues feel straightforward instead of stressful."),
            ("02", "Brake and safety", "Give safety-critical services a clean path from concern to phone call."),
            ("03", "Maintenance", "Package everyday work like oil, fluids, batteries, and trip checks into scannable categories."),
            ("04", "Appointments", "Prioritize tap-to-call and location details for mobile customers in a hurry."),
        ]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{business_name} | {niche.title()} in {city}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    :root {{
      --bg: {theme['bg']};
      --ink: {theme['ink']};
      --muted: {theme['muted']};
      --panel: {theme['panel']};
      --dark: {theme['dark']};
      --accent: {theme['accent']};
      --accent2: {theme['accent2']};
      --soft: {theme['soft']};
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: var(--bg); color: var(--ink); font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; letter-spacing: 0; }}
    .shell {{ width: min(1180px, calc(100% - 32px)); margin: 0 auto; }}
    .nav {{ position: sticky; top: 0; z-index: 20; backdrop-filter: blur(18px); background: color-mix(in srgb, var(--panel) 88%, transparent); border-bottom: 1px solid rgba(17,24,39,.1); }}
    .nav-inner {{ min-height: 76px; display: flex; align-items: center; justify-content: space-between; gap: 18px; }}
    .brand small, .eyebrow, .metric span, .audit-label {{ display: block; color: var(--muted); font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: .08em; }}
    .brand strong {{ display: block; font-size: 19px; line-height: 1.1; }}
    .call {{ display: inline-flex; align-items: center; justify-content: center; min-height: 44px; border-radius: 8px; padding: 0 18px; background: var(--dark); color: white; font-weight: 800; text-decoration: none; box-shadow: 0 12px 28px rgba(0,0,0,.16); }}
    .hero {{ padding: 54px 0 34px; }}
    .hero-grid {{ display: grid; grid-template-columns: minmax(0, 1.08fr) minmax(320px, .92fr); gap: 22px; align-items: stretch; }}
    .hero-card {{ min-height: 560px; display: flex; flex-direction: column; justify-content: space-between; border-radius: 8px; padding: clamp(28px, 5vw, 56px); background: radial-gradient(circle at 15% 10%, var(--soft), transparent 32%), linear-gradient(145deg, var(--panel), #fff); border: 1px solid rgba(17,24,39,.1); box-shadow: 0 24px 70px rgba(17,24,39,.12); }}
    h1 {{ max-width: 820px; margin: 16px 0 0; font-size: clamp(46px, 7vw, 84px); line-height: .92; letter-spacing: 0; }}
    .lead {{ max-width: 680px; margin: 24px 0 0; color: var(--muted); font-size: 19px; line-height: 1.7; }}
    .cta-row {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 30px; }}
    .secondary {{ display: inline-flex; align-items: center; justify-content: center; min-height: 44px; border-radius: 8px; padding: 0 18px; border: 1px solid rgba(17,24,39,.18); color: var(--ink); font-weight: 800; text-decoration: none; background: white; }}
    .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 42px; }}
    .metrics div {{ border-radius: 8px; padding: 16px; background: rgba(255,255,255,.72); border: 1px solid rgba(17,24,39,.09); }}
    .metrics strong {{ display: block; margin-top: 8px; font-size: 26px; line-height: 1; }}
    .metrics small {{ display: block; margin-top: 8px; color: var(--muted); line-height: 1.35; }}
    .side {{ border-radius: 8px; background: var(--dark); color: white; padding: 26px; box-shadow: 0 24px 70px rgba(17,24,39,.2); display: flex; flex-direction: column; gap: 18px; }}
    .score {{ padding: 24px; border-radius: 8px; background: linear-gradient(145deg, rgba(255,255,255,.16), rgba(255,255,255,.06)); border: 1px solid rgba(255,255,255,.14); }}
    .score strong {{ display: block; font-size: 72px; line-height: .9; letter-spacing: 0; }}
    .score p, .board p {{ color: rgba(255,255,255,.7); line-height: 1.55; }}
    .board {{ display: grid; gap: 12px; }}
    .board div {{ padding: 18px; border-radius: 8px; background: rgba(255,255,255,.09); border: 1px solid rgba(255,255,255,.1); }}
    .board h3 {{ margin: 0; font-size: 18px; }}
    section {{ padding: 54px 0; }}
    .section-head {{ display: flex; justify-content: space-between; gap: 24px; align-items: end; margin-bottom: 22px; }}
    .section-head h2 {{ margin: 8px 0 0; max-width: 720px; font-size: clamp(32px, 4vw, 52px); line-height: 1; }}
    .section-head p {{ max-width: 430px; color: var(--muted); line-height: 1.65; }}
    .services {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }}
    .services article {{ min-height: 245px; display: flex; flex-direction: column; justify-content: space-between; border-radius: 8px; padding: 22px; background: var(--panel); border: 1px solid rgba(17,24,39,.1); box-shadow: 0 16px 40px rgba(17,24,39,.08); }}
    .services article div {{ color: var(--accent); font-weight: 900; }}
    .services h3, .pain h3 {{ margin: 14px 0 0; font-size: 22px; }}
    .services p, .pain p {{ color: var(--muted); line-height: 1.6; }}
    .audit {{ border-radius: 8px; padding: 34px; background: var(--panel); border: 1px solid rgba(17,24,39,.1); box-shadow: 0 18px 50px rgba(17,24,39,.1); display: grid; grid-template-columns: .8fr 1.2fr; gap: 28px; }}
    .audit ul {{ margin: 20px 0 0; padding-left: 18px; color: var(--muted); line-height: 1.8; }}
    .pain {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }}
    .pain article {{ border-radius: 8px; padding: 24px; background: color-mix(in srgb, var(--soft) 58%, white); border: 1px solid rgba(17,24,39,.08); }}
    .pain span {{ display: inline-flex; width: 36px; height: 36px; align-items: center; justify-content: center; border-radius: 8px; background: var(--dark); color: white; font-weight: 900; }}
    .contact {{ display: grid; grid-template-columns: 1fr .85fr; gap: 18px; }}
    .contact > div {{ border-radius: 8px; padding: 30px; background: var(--panel); border: 1px solid rgba(17,24,39,.1); }}
    .contact .dark {{ background: var(--dark); color: white; }}
    .contact .dark p {{ color: rgba(255,255,255,.7); }}
    footer {{ padding: 30px 0 92px; color: var(--muted); text-align: center; }}
    .mobile-call {{ display: none; position: fixed; left: 14px; right: 14px; bottom: 14px; z-index: 30; }}
    @media (max-width: 920px) {{
      .hero-grid, .audit, .contact {{ grid-template-columns: 1fr; }}
      .metrics, .services, .pain {{ grid-template-columns: repeat(2, 1fr); }}
      .hero-card {{ min-height: auto; }}
    }}
    @media (max-width: 640px) {{
      .nav-inner, .section-head {{ align-items: stretch; flex-direction: column; }}
      h1 {{ font-size: 43px; }}
      .metrics, .services, .pain {{ grid-template-columns: 1fr; }}
      .nav .call {{ display: none; }}
      .mobile-call {{ display: block; }}
    }}
  </style>
</head>
<body>
  <nav class="nav">
    <div class="shell nav-inner">
      <div class="brand"><small>{city} {niche}</small><strong>{business_name}</strong></div>
      <a class="call" href="tel:{phone}">Call {phone}</a>
    </div>
  </nav>
  <main>
    <section class="hero">
      <div class="shell hero-grid">
        <div class="hero-card">
          <div>
            <span class="eyebrow">Mainstreet rebuild preview</span>
            <h1>{theme['hero']}</h1>
            <p class="lead">A deploy-ready homepage concept for {business_name}, built around faster phone calls, clearer service categories, and a stronger first impression for {city} drivers.</p>
            <div class="cta-row">
              <a class="call" href="tel:{phone}">Call {phone}</a>
              <a class="secondary" href="#contact">See location and hours</a>
            </div>
          </div>
          <div class="metrics">{stat_cards}</div>
        </div>
        <aside class="side">
          <div class="score"><span class="audit-label">Scout audit score</span><strong>{score}/10</strong><p>Used to shape the rebuild priority, content hierarchy, and conversion path.</p></div>
          <div class="board">
            <div><h3>Immediate repair need</h3><p>Make diagnostics, brakes, and maintenance easy to understand without digging through pages.</p></div>
            <div><h3>Mobile-first action</h3><p>Keep the phone call available in the first viewport and at the bottom of mobile screens.</p></div>
            <div><h3>Local confidence</h3><p>Bring rating, reviews, address, and service clarity into a single trustworthy flow.</p></div>
          </div>
        </aside>
      </div>
    </section>
    <section>
      <div class="shell">
        <div class="section-head">
          <div><span class="eyebrow">Service clarity</span><h2>Customers know what this shop can handle before they call.</h2></div>
          <p>Instead of a generic landing page, this mockup gives common auto-repair needs their own clear decision points.</p>
        </div>
        <div class="services">{service_cards}</div>
      </div>
    </section>
    <section>
      <div class="shell audit">
        <div>
          <span class="eyebrow">Audit-backed direction</span>
          <h2>Designed around the friction Scout found.</h2>
          <ul>{reasons}</ul>
        </div>
        <div class="pain">{pains}</div>
      </div>
    </section>
    <section id="contact">
      <div class="shell contact">
        <div>
          <span class="eyebrow">Visit the shop</span>
          <h2>{business_name}</h2>
          <p>{address}</p>
          <p>Hours: {hours}</p>
          <p>Rating signal: {rating} from {review_count} reviews</p>
        </div>
        <div class="dark">
          <span class="audit-label">Primary conversion</span>
          <h2>Make the next step impossible to miss.</h2>
          <p>The site keeps the highest-intent action direct: call the shop, ask about the repair, and schedule the visit.</p>
          <a class="call" style="background:white;color:var(--dark);margin-top:18px" href="tel:{phone}">Call {phone}</a>
        </div>
      </div>
    </section>
  </main>
  <footer class="shell">{business_name} - {city} {niche}. Rebuild preview generated from Scout audit data.</footer>
  <a class="call mobile-call" href="tel:{phone}">Call {phone}</a>
</body>
</html>"""


def run(lead: dict[str, Any], variant: str, previous_critique: dict[str, Any] | None = None) -> str:
    """Generate a valid single-file Tailwind HTML mockup."""

    lead_id = _lead_id(lead)
    business_name = str(lead.get("business_name") or "")
    user_prompt = _prompt(lead, variant, previous_critique)
    last_payload: dict[str, Any] | None = None

    if _template_mode_enabled():
        html = _agency_template_html(lead, variant)
        _safe_log(
            "generate_mockup",
            "succeeded",
            f"rendered template-first {variant} mockup for {business_name}.",
            lead_id,
            {"variant": variant, "renderer": "premium_template"},
        )
        return html

    for attempt in range(2):
        try:
            payload = nemotron_client.chat_json(
                system="You are Designer, a NemoClaw claw generating Tailwind HTML mockups. Return JSON only.",
                user=user_prompt,
                retries=1,
            )
        except Exception as exc:
            html = _agency_template_html(lead, variant, str(exc))
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
