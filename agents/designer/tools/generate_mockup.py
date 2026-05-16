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


def _industry_key(lead: dict[str, Any]) -> str:
    """Map scraped niche labels to a small set of polished template profiles."""

    niche = str(lead.get("niche") or "").lower()
    if any(term in niche for term in ["dentist", "dental", "orthodont"]):
        return "dental"
    if any(term in niche for term in ["plumb", "water heater", "drain"]):
        return "plumbing"
    if any(term in niche for term in ["electric", "lighting", "panel"]):
        return "electrical"
    if any(term in niche for term in ["roof", "gutter"]):
        return "roofing"
    if any(term in niche for term in ["landscap", "garden", "lawn"]):
        return "landscaping"
    if any(term in niche for term in ["hvac", "heating", "air conditioning", "furnace"]):
        return "hvac"
    if any(term in niche for term in ["pet", "groom", "dog"]):
        return "pet_grooming"
    if any(term in niche for term in ["detail", "wash", "auto", "tire", "body", "car", "vehicle"]):
        return "automotive"
    return "local_service"


def _profile(lead: dict[str, Any]) -> dict[str, Any]:
    """Return industry-specific copy, stats, reviews, and real image assets."""

    profiles: dict[str, dict[str, Any]] = {
        "automotive": {
            "category": "premium auto service",
            "hero": "Dealership-grade care. Independent-shop clarity.",
            "sub": "Advanced diagnostics, clean communication, and high-confidence repairs for everyday, European, and performance vehicles.",
            "concierge_hero": "Service that feels managed, not mysterious.",
            "performance_hero": "Built for drivers who notice everything.",
            "eyebrow": "Premium dealership alternative",
            "image": "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?auto=format&fit=crop&w=1600&q=85",
            "detail": "https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?auto=format&fit=crop&w=1200&q=85",
            "services": [
                ("Advanced Diagnostics", "Electrical, drivability, warning lights, leaks, and performance issues explained before work begins."),
                ("Brake & Suspension", "Quiet stops, confident handling, pads, rotors, shocks, struts, and safety-critical repairs."),
                ("Factory Maintenance", "Mileage-based service, fluids, batteries, belts, filters, and preventive care for long vehicle life."),
                ("Performance Care", "High-attention service for drivers who care about response, ride quality, reliability, and detail."),
            ],
            "stats": [("4.9", "average rating"), ("18+", "years expertise"), ("24 hr", "diagnostic goal"), ("3,200+", "vehicles serviced")],
            "reviews": [
                ("Clean shop, clear quote, and no pressure. It felt like dealership quality without the runaround.", "Maya R."),
                ("They diagnosed the issue quickly and explained what mattered now versus what could wait.", "Jordan T."),
                ("Easy scheduling and the car came back feeling perfect.", "Elena S."),
            ],
            "process": ["Listen first", "Diagnose clearly", "Deliver cleanly"],
        },
        "dental": {
            "category": "modern dental care",
            "hero": "A calmer, clearer way to care for your smile.",
            "sub": "Preventive visits, cosmetic consults, emergency care, and family dentistry presented with warmth, confidence, and easy booking.",
            "concierge_hero": "Dental care that feels personal from the first click.",
            "performance_hero": "Confident care for healthier smiles.",
            "eyebrow": "Modern family dental studio",
            "image": "https://images.unsplash.com/photo-1606811971618-4486d14f3f99?auto=format&fit=crop&w=1600&q=85",
            "detail": "https://images.unsplash.com/photo-1629909613654-28e377c37b09?auto=format&fit=crop&w=1200&q=85",
            "services": [
                ("Preventive Care", "Cleanings, exams, digital x-rays, fluoride care, and proactive guidance for every age."),
                ("Cosmetic Dentistry", "Whitening, bonding, veneers, and smile upgrades explained with clear expectations."),
                ("Emergency Visits", "Fast help for tooth pain, chips, swelling, and urgent dental concerns."),
                ("Family Appointments", "Simple scheduling for kids, adults, and busy households."),
            ],
            "stats": [("4.9", "patient rating"), ("7k+", "smiles cared for"), ("Same day", "urgent visits"), ("98%", "comfort-first reviews")],
            "reviews": [
                ("The team made everything feel easy and calm. Best dental visit I have had.", "Priya S."),
                ("Clear pricing, gentle care, and a beautiful office.", "Daniel K."),
                ("They helped my whole family get scheduled without stress.", "Monica L."),
            ],
            "process": ["Book easily", "Feel comfortable", "Leave smiling"],
        },
        "plumbing": {
            "category": "trusted plumbing",
            "hero": "Fast plumbing help without the guesswork.",
            "sub": "Emergency leaks, water heaters, drain clearing, fixture upgrades, and clean communication from arrival to repair.",
            "concierge_hero": "Plumbing service that explains the problem before the invoice.",
            "performance_hero": "Built for homes that need water moving right.",
            "eyebrow": "Reliable home plumbing",
            "image": "https://images.unsplash.com/photo-1607472586893-edb57bdc0e39?auto=format&fit=crop&w=1600&q=85",
            "detail": "https://images.unsplash.com/photo-1585704032915-c3400ca199e7?auto=format&fit=crop&w=1200&q=85",
            "services": [
                ("Leak Repair", "Locate pipe, fixture, and slab leaks quickly with clean repair recommendations."),
                ("Drain Clearing", "Clogs, slow drains, sewer backups, and camera inspections when needed."),
                ("Water Heaters", "Repair, replacement, tankless upgrades, flushing, and safety checks."),
                ("Fixture Installs", "Faucets, toilets, disposals, valves, and remodel-ready plumbing work."),
            ],
            "stats": [("24/7", "urgent response"), ("4.8", "local rating"), ("90 min", "arrival goal"), ("12k+", "repairs completed")],
            "reviews": [
                ("They found the leak fast, explained the fix, and left the area spotless.", "Chris M."),
                ("Honest, quick, and the price made sense.", "Alyssa B."),
                ("Our water heater was replaced the same day. Huge relief.", "Rene P."),
            ],
            "process": ["Find the issue", "Explain options", "Fix it cleanly"],
        },
        "electrical": {
            "category": "licensed electrical service",
            "hero": "Safer power, cleaner installs, clearer estimates.",
            "sub": "Panels, outlets, EV chargers, lighting, troubleshooting, and code-aware work for homes and small businesses.",
            "concierge_hero": "Electrical work that feels organized and safe.",
            "performance_hero": "Power upgrades done with precision.",
            "eyebrow": "Modern electrical contractor",
            "image": "https://images.unsplash.com/photo-1621905252507-b35492cc74b4?auto=format&fit=crop&w=1600&q=85",
            "detail": "https://images.unsplash.com/photo-1565608087341-404b25492fee?auto=format&fit=crop&w=1200&q=85",
            "services": [
                ("Panel Upgrades", "Capacity planning, safer panels, breakers, subpanels, and modernization."),
                ("EV Chargers", "Home charging installs with clean routing and load-aware recommendations."),
                ("Lighting", "Interior, exterior, security, recessed, and energy-conscious lighting upgrades."),
                ("Troubleshooting", "Outlets, flickering lights, tripped breakers, and mysterious power issues."),
            ],
            "stats": [("4.9", "homeowner rating"), ("2k+", "projects wired"), ("100%", "permit-aware"), ("24 hr", "estimate follow-up")],
            "reviews": [
                ("They upgraded our panel cleanly and explained every step.", "Nina G."),
                ("The EV charger install looks perfect.", "Sam R."),
                ("Professional, safe, and easy to schedule.", "Leah T."),
            ],
            "process": ["Inspect safely", "Plan clearly", "Power reliably"],
        },
        "roofing": {
            "category": "roofing and exterior protection",
            "hero": "Roofing confidence before the next storm.",
            "sub": "Inspections, leak repair, replacements, gutters, and exterior protection with clear photos, timelines, and warranty guidance.",
            "concierge_hero": "Roofing work with photos, timelines, and no mystery.",
            "performance_hero": "Built to keep weather outside.",
            "eyebrow": "Trusted roofing contractor",
            "image": "https://images.unsplash.com/photo-1632759145351-1d592919f522?auto=format&fit=crop&w=1600&q=85",
            "detail": "https://images.unsplash.com/photo-1626885930974-4b69aa21bbf9?auto=format&fit=crop&w=1200&q=85",
            "services": [
                ("Roof Inspections", "Photo-backed condition reports for leaks, wear, flashing, vents, and storm damage."),
                ("Leak Repair", "Targeted repair for active leaks, missing shingles, flashing, and water intrusion."),
                ("Replacements", "Clear options for asphalt, metal, flat roofs, ventilation, and warranties."),
                ("Gutters", "Gutter repair, cleaning, guards, drainage, and exterior water control."),
            ],
            "stats": [("15 yr", "workmanship focus"), ("4.8", "local rating"), ("48 hr", "inspection goal"), ("1,900+", "roofs protected")],
            "reviews": [
                ("They showed photos, gave a clear plan, and finished ahead of the rain.", "Luis F."),
                ("Professional crew and no mess left behind.", "Hannah W."),
                ("The inspection made the decision easy.", "Omar J."),
            ],
            "process": ["Inspect thoroughly", "Document clearly", "Protect the home"],
        },
        "landscaping": {
            "category": "landscape design and maintenance",
            "hero": "Outdoor spaces that look cared for every week.",
            "sub": "Design, planting, irrigation, cleanups, hardscape details, and maintenance plans that make curb appeal feel effortless.",
            "concierge_hero": "Landscaping with a plan, not just a crew.",
            "performance_hero": "Built for curb appeal that lasts.",
            "eyebrow": "Premium landscape service",
            "image": "https://images.unsplash.com/photo-1558904541-efa843a96f01?auto=format&fit=crop&w=1600&q=85",
            "detail": "https://images.unsplash.com/photo-1598902108854-10e335adac99?auto=format&fit=crop&w=1200&q=85",
            "services": [
                ("Maintenance Plans", "Mowing, pruning, edging, seasonal color, and consistent property care."),
                ("Landscape Design", "Planting plans, curb appeal upgrades, outdoor rooms, and drought-aware choices."),
                ("Irrigation", "Sprinkler repair, drip systems, smart controllers, and water-efficient tuning."),
                ("Cleanups", "Overgrowth, hauling, storm cleanup, mulch, and property refreshes."),
            ],
            "stats": [("52 wk", "care plans"), ("4.9", "owner rating"), ("30%", "water savings goal"), ("800+", "yards refreshed")],
            "reviews": [
                ("Our yard finally looks intentional and easy to maintain.", "Becca H."),
                ("Reliable crew, beautiful planting, and smart irrigation fixes.", "Andre V."),
                ("They transformed the front yard in a weekend.", "Sofia N."),
            ],
            "process": ["Plan the space", "Build the look", "Maintain the beauty"],
        },
        "hvac": {
            "category": "heating and cooling service",
            "hero": "Comfort you can feel before the weather turns.",
            "sub": "AC repair, furnace service, heat pumps, tune-ups, indoor air quality, and fast scheduling for homes that need comfort now.",
            "concierge_hero": "Heating and cooling help with clear next steps.",
            "performance_hero": "Built for homes that stay comfortable.",
            "eyebrow": "Home comfort specialists",
            "image": "https://images.unsplash.com/photo-1621905251189-08b45d6a269e?auto=format&fit=crop&w=1600&q=85",
            "detail": "https://images.unsplash.com/photo-1581092918056-0c4c3acd3789?auto=format&fit=crop&w=1200&q=85",
            "services": [
                ("AC Repair", "Cooling diagnostics, refrigerant checks, airflow issues, and emergency summer repairs."),
                ("Heating Service", "Furnaces, heat pumps, thermostats, safety checks, and winter readiness."),
                ("System Replacement", "Right-sized systems, efficiency options, financing-ready estimates, and clean installs."),
                ("Maintenance", "Seasonal tune-ups, filters, coils, ducts, and comfort performance checks."),
            ],
            "stats": [("24/7", "comfort calls"), ("4.8", "home rating"), ("12 mo", "maintenance plans"), ("2,400+", "systems serviced")],
            "reviews": [
                ("They got our AC working before the heat wave and explained the issue clearly.", "Drew C."),
                ("Professional install, clean crew, and a quieter system.", "Anika M."),
                ("The maintenance plan already saved us a breakdown.", "Joel S."),
            ],
            "process": ["Diagnose comfort", "Explain options", "Restore airflow"],
        },
        "pet_grooming": {
            "category": "pet grooming studio",
            "hero": "A cleaner, calmer grooming day for pets and people.",
            "sub": "Baths, cuts, de-shedding, nail trims, breed-aware styling, and a booking flow built for busy pet parents.",
            "concierge_hero": "Grooming that feels gentle, organized, and easy to book.",
            "performance_hero": "Built for pets who deserve the good treatment.",
            "eyebrow": "Premium pet grooming",
            "image": "https://images.unsplash.com/photo-1516734212186-a967f81ad0d7?auto=format&fit=crop&w=1600&q=85",
            "detail": "https://images.unsplash.com/photo-1516734212186-a967f81ad0d7?auto=format&fit=crop&w=1200&q=85",
            "services": [
                ("Full Groom", "Bath, haircut, blow dry, brush-out, ears, nails, and finishing touches."),
                ("Bath & Brush", "Coat care, de-shedding, skin-friendly wash, and tidy-up service."),
                ("Nail Care", "Quick trims, grinding, paw care, and add-ons for regular visits."),
                ("Puppy Visits", "Gentle first appointments that help young pets learn grooming calmly."),
            ],
            "stats": [("4.9", "pet parent rating"), ("6k+", "happy grooms"), ("Same week", "booking goal"), ("100%", "gentle handling")],
            "reviews": [
                ("My nervous dog came home happy, clean, and adorable.", "Kate D."),
                ("Easy booking and the cut was exactly what we asked for.", "Miguel A."),
                ("The team is patient and so kind with older pets.", "Tara E."),
            ],
            "process": ["Welcome gently", "Groom carefully", "Send them home fresh"],
        },
    }
    return profiles.get(_industry_key(lead), profiles["plumbing"])


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


def _stable_template_index(lead: dict[str, Any], count: int) -> int:
    """Choose a stable template index from business identity."""

    seed = str(lead.get("business_name") or lead.get("id") or lead.get("address") or "")
    chars = [char.lower() for char in seed if char.isalnum()]
    if not chars or not count:
        return 0
    return (ord(chars[0]) + len(chars)) % count


def _client_website_html(lead: dict[str, Any], variant: str, reason: str = "client website template") -> str:
    """Render one of several finished client-facing website templates."""

    templates = [
        _client_showroom_html,
        _client_concierge_html,
        _client_performance_html,
        _client_editorial_html,
        _client_booking_html,
        _client_local_proof_html,
        _client_luxury_card_html,
        _client_service_menu_html,
    ]
    return templates[_stable_template_index(lead, len(templates))](lead, variant, reason)


def _stock_photo(profile: dict[str, Any], slot: str) -> str:
    """Return a stock image URL tailored to the profile and template slot."""

    key = str(profile.get("category", "local service")).lower()
    queries = {
        "premium auto service": {
            "hero": "auto,repair,garage",
            "detail": "mechanic,workshop",
            "portrait": "car,interior",
            "texture": "automotive,tools",
        },
        "modern dental care": {
            "hero": "dentist,clinic",
            "detail": "dental,office",
            "portrait": "smiling,patient",
            "texture": "dental,tools",
        },
        "trusted plumbing": {
            "hero": "plumber,home",
            "detail": "modern,bathroom",
            "portrait": "technician,plumbing",
            "texture": "pipes,tools",
        },
        "licensed electrical service": {
            "hero": "electrician,home",
            "detail": "electrical,panel",
            "portrait": "lighting,interior",
            "texture": "copper,wires",
        },
        "roofing and exterior protection": {
            "hero": "roofing,house",
            "detail": "roof,shingles",
            "portrait": "home,exterior",
            "texture": "roof,texture",
        },
        "landscape design and maintenance": {
            "hero": "landscape,garden",
            "detail": "yard,design",
            "portrait": "outdoor,living",
            "texture": "plants,texture",
        },
        "heating and cooling service": {
            "hero": "hvac,technician",
            "detail": "air,conditioning",
            "portrait": "home,comfort",
            "texture": "ventilation",
        },
        "pet grooming studio": {
            "hero": "dog,grooming",
            "detail": "pet,groomer",
            "portrait": "happy,dog",
            "texture": "pet,care",
        },
    }
    query = queries.get(key, {}).get(slot, f"{key},service").replace(" ", ",")
    # Source images keep demo pages visually fresh without storing binary assets.
    return f"https://source.unsplash.com/1600x1000/?{query}"


def _client_bits(lead: dict[str, Any]) -> dict[str, Any]:
    """Collect escaped client-template values in one place."""

    profile = _profile(lead)
    services = [(escape(str(title)), escape(str(copy))) for title, copy in profile["services"]]
    stats = [(escape(str(value)), escape(str(label))) for value, label in profile["stats"]]
    reviews = [(escape(str(quote)), escape(str(name))) for quote, name in profile["reviews"]]
    return {
        "business_name": escape(str(lead.get("business_name") or "Apex Local Co.")),
        "niche": escape(str(lead.get("niche") or "local service")),
        "city": escape(str(lead.get("city") or "Santa Cruz")),
        "phone": escape(str(lead.get("phone") or "(831) 555-0198")),
        "address": escape(str(lead.get("address") or f"{lead.get('city') or 'Santa Cruz'}, CA")),
        "hours": escape(str(lead.get("hours") or lead.get("opening_hours") or "Mon-Fri 8:00 AM - 6:00 PM")),
        "rating": escape(str(lead.get("google_rating") or "4.9")),
        "review_count": escape(str(lead.get("review_count") or "240")),
        "profile": profile,
        "category": escape(str(profile["category"])),
        "eyebrow": escape(str(profile["eyebrow"])),
        "hero": escape(str(profile["hero"])),
        "sub": escape(str(profile["sub"])),
        "services": services,
        "stats": stats,
        "reviews": reviews,
        "hero_image": _stock_photo(profile, "hero"),
        "detail_image": _stock_photo(profile, "detail"),
        "portrait_image": _stock_photo(profile, "portrait"),
        "texture_image": _stock_photo(profile, "texture"),
    }


def _client_showroom_html(lead: dict[str, Any], variant: str, reason: str = "client website template") -> str:
    """Render a finished premium client website, with no demo/audit language."""

    business_name = escape(str(lead.get("business_name") or "Apex Motor Works"))
    niche = escape(str(lead.get("niche") or "auto repair"))
    city = escape(str(lead.get("city") or "Santa Cruz"))
    phone = escape(str(lead.get("phone") or "(831) 555-0198"))
    address = escape(str(lead.get("address") or f"{city}, CA"))
    hours = escape(str(lead.get("hours") or lead.get("opening_hours") or "Mon-Fri 8:00 AM - 6:00 PM"))
    rating = escape(str(lead.get("google_rating") or "4.9"))
    review_count = escape(str(lead.get("review_count") or "240"))
    profile = _profile(lead)
    category = escape(str(profile["category"]))
    eyebrow = escape(str(profile["eyebrow"]))

    theme = {
        "clean_modern": {
            "accent": "#2563eb",
            "accent2": "#14b8a6",
            "dark": "#0f172a",
            "cream": "#f8fafc",
            "hero": "Precision service without the dealership wait.",
            "sub": "Factory-level diagnostics, transparent recommendations, and a calmer service experience for drivers who expect the details done right.",
            "image": "https://images.unsplash.com/photo-1619642751034-765dfdf7c58e?auto=format&fit=crop&w=1600&q=85",
            "bay": "https://images.unsplash.com/photo-1625047509168-a7026f36de04?auto=format&fit=crop&w=1200&q=85",
        },
        "retro_local": {
            "accent": "#b91c1c",
            "accent2": "#0f766e",
            "dark": "#111827",
            "cream": "#fff7ed",
            "hero": "Independent repair with premium attention to detail.",
            "sub": "A modern shop experience rooted in local trust: clear answers, careful inspections, and service that respects your schedule.",
            "image": "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1600&q=85",
            "bay": "https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?auto=format&fit=crop&w=1200&q=85",
        },
        "premium": {
            "accent": "#10b981",
            "accent2": "#38bdf8",
            "dark": "#09090b",
            "cream": "#f4f4f5",
            "hero": "Dealership-grade care. Independent-shop clarity.",
            "sub": "Advanced diagnostics, clean communication, and high-confidence repairs for European, performance, and everyday vehicles.",
            "image": "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?auto=format&fit=crop&w=1600&q=85",
            "bay": "https://images.unsplash.com/photo-1599256872237-5dcc0fbe9668?auto=format&fit=crop&w=1200&q=85",
        },
    }.get(variant)
    if theme is None:
        theme = {
            "accent": "#2563eb",
            "accent2": "#14b8a6",
            "dark": "#0f172a",
            "cream": "#f8fafc",
            "hero": "Precision service without the dealership wait.",
            "sub": "Factory-level diagnostics, transparent recommendations, and a calmer service experience for drivers who expect the details done right.",
            "image": "https://images.unsplash.com/photo-1619642751034-765dfdf7c58e?auto=format&fit=crop&w=1600&q=85",
            "bay": "https://images.unsplash.com/photo-1625047509168-a7026f36de04?auto=format&fit=crop&w=1200&q=85",
        }
    theme["hero"] = str(profile["hero"])
    theme["sub"] = str(profile["sub"])
    theme["image"] = str(profile["image"])
    theme["bay"] = str(profile["detail"])

    stats = [(str(value), str(label)) for value, label in profile["stats"]]
    stat_html = "".join(f"<div><strong>{value}</strong><span>{label}</span></div>" for value, label in stats)
    services = [(str(title), str(copy)) for title, copy in profile["services"]]
    service_html = "".join(
        f"""
        <article>
          <span>{index:02d}</span>
          <h3>{title}</h3>
          <p>{copy}</p>
        </article>"""
        for index, (title, copy) in enumerate(services, start=1)
    )
    reviews = [(str(quote), str(name)) for quote, name in profile["reviews"]]
    review_html = "".join(f"<blockquote><p>{quote}</p><cite>{name}</cite></blockquote>" for quote, name in reviews)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{business_name} | {category.title()} in {city}</title>
  <style>
    :root {{
      --accent: {theme['accent']};
      --accent2: {theme['accent2']};
      --dark: {theme['dark']};
      --cream: {theme['cream']};
      --ink: #111827;
      --muted: #687083;
      --line: rgba(17, 24, 39, .12);
      --shadow: 0 24px 70px rgba(15, 23, 42, .14);
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{ margin: 0; background: var(--cream); color: var(--ink); font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; letter-spacing: 0; }}
    a {{ color: inherit; }}
    .wrap {{ width: min(1180px, calc(100% - 34px)); margin: 0 auto; }}
    .nav {{ position: sticky; top: 0; z-index: 50; background: rgba(255,255,255,.9); backdrop-filter: blur(18px); border-bottom: 1px solid var(--line); }}
    .nav .wrap {{ min-height: 74px; display: flex; align-items: center; justify-content: space-between; gap: 22px; }}
    .brand strong {{ display: block; font-size: 20px; line-height: 1; }}
    .brand span, .eyebrow {{ display: block; margin-top: 5px; color: var(--muted); font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: .08em; }}
    .nav-links {{ display: flex; align-items: center; gap: 22px; color: #374151; font-size: 14px; font-weight: 700; }}
    .nav-links a {{ text-decoration: none; }}
    .button {{ display: inline-flex; align-items: center; justify-content: center; min-height: 46px; border-radius: 8px; padding: 0 20px; background: var(--accent); color: white; font-weight: 900; text-decoration: none; box-shadow: 0 16px 34px color-mix(in srgb, var(--accent) 35%, transparent); }}
    .button.dark {{ background: var(--dark); box-shadow: 0 16px 34px rgba(0,0,0,.22); }}
    .hero {{ position: relative; overflow: hidden; background: var(--dark); color: white; }}
    .hero::before {{ content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, rgba(0,0,0,.86), rgba(0,0,0,.55) 45%, rgba(0,0,0,.08)), url("{theme['image']}") center/cover; transform: scale(1.02); }}
    .hero .wrap {{ position: relative; min-height: 720px; display: grid; align-items: end; padding: 88px 0 54px; }}
    .hero-copy {{ max-width: 780px; }}
    h1 {{ margin: 18px 0 0; font-size: clamp(52px, 8vw, 104px); line-height: .88; letter-spacing: 0; }}
    .hero p {{ max-width: 650px; margin: 26px 0 0; color: rgba(255,255,255,.78); font-size: 20px; line-height: 1.7; }}
    .hero-actions {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 32px; }}
    .ghost {{ display: inline-flex; align-items: center; justify-content: center; min-height: 46px; border-radius: 8px; padding: 0 20px; border: 1px solid rgba(255,255,255,.34); color: white; font-weight: 900; text-decoration: none; }}
    .stats {{ position: relative; display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px; background: var(--line); border-bottom: 1px solid var(--line); }}
    .stats div {{ background: white; padding: 30px; }}
    .stats strong {{ display: block; font-size: 42px; line-height: 1; }}
    .stats span {{ display: block; margin-top: 10px; color: var(--muted); font-weight: 700; }}
    section {{ padding: 86px 0; }}
    .section-head {{ display: flex; align-items: end; justify-content: space-between; gap: 28px; margin-bottom: 34px; }}
    .section-head h2 {{ margin: 10px 0 0; max-width: 760px; font-size: clamp(36px, 5vw, 64px); line-height: .98; letter-spacing: 0; }}
    .section-head p {{ max-width: 430px; color: var(--muted); font-size: 17px; line-height: 1.65; }}
    .services {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }}
    .services article {{ min-height: 320px; border-radius: 8px; padding: 26px; background: white; border: 1px solid var(--line); box-shadow: 0 18px 46px rgba(15,23,42,.08); display: flex; flex-direction: column; justify-content: space-between; }}
    .services span {{ color: var(--accent); font-weight: 950; }}
    .services h3 {{ margin: 22px 0 0; font-size: 25px; line-height: 1.08; }}
    .services p {{ color: var(--muted); line-height: 1.62; }}
    .split {{ display: grid; grid-template-columns: .9fr 1.1fr; gap: 22px; align-items: stretch; }}
    .photo {{ min-height: 560px; border-radius: 8px; background: url("{theme['bay']}") center/cover; box-shadow: var(--shadow); }}
    .panel {{ border-radius: 8px; padding: clamp(30px, 5vw, 56px); background: white; border: 1px solid var(--line); box-shadow: var(--shadow); }}
    .panel h2 {{ margin: 12px 0 0; font-size: clamp(34px, 4vw, 58px); line-height: 1; }}
    .panel p, .panel li {{ color: var(--muted); line-height: 1.75; font-size: 17px; }}
    .panel ul {{ margin: 28px 0 0; padding: 0; list-style: none; display: grid; gap: 14px; }}
    .panel li {{ display: grid; grid-template-columns: 28px 1fr; gap: 12px; align-items: start; }}
    .panel li::before {{ content: "✓"; width: 28px; height: 28px; display: inline-flex; align-items: center; justify-content: center; border-radius: 8px; background: var(--accent); color: white; font-weight: 900; }}
    .reviews {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }}
    blockquote {{ margin: 0; border-radius: 8px; padding: 28px; background: white; border: 1px solid var(--line); box-shadow: 0 18px 46px rgba(15,23,42,.08); }}
    blockquote p {{ margin: 0; color: #344054; line-height: 1.7; font-size: 17px; }}
    cite {{ display: block; margin-top: 22px; color: var(--ink); font-style: normal; font-weight: 900; }}
    .contact {{ display: grid; grid-template-columns: 1fr .85fr; gap: 18px; }}
    .contact-card {{ border-radius: 8px; padding: 36px; background: var(--dark); color: white; box-shadow: var(--shadow); }}
    .contact-card p {{ color: rgba(255,255,255,.72); line-height: 1.7; }}
    .info {{ border-radius: 8px; padding: 36px; background: white; border: 1px solid var(--line); }}
    .info dl {{ display: grid; gap: 18px; margin: 26px 0 0; }}
    .info dt {{ color: var(--muted); font-size: 12px; font-weight: 900; text-transform: uppercase; letter-spacing: .08em; }}
    .info dd {{ margin: 4px 0 0; font-size: 18px; font-weight: 800; }}
    footer {{ padding: 34px 0 94px; color: var(--muted); text-align: center; }}
    .mobile-call {{ display: none; position: fixed; left: 14px; right: 14px; bottom: 14px; z-index: 60; }}
    @media (max-width: 980px) {{
      .services, .reviews, .stats {{ grid-template-columns: repeat(2, 1fr); }}
      .split, .contact {{ grid-template-columns: 1fr; }}
      .photo {{ min-height: 420px; }}
    }}
    @media (max-width: 680px) {{
      .nav-links {{ display: none; }}
      .hero .wrap {{ min-height: 660px; }}
      h1 {{ font-size: 50px; }}
      .stats, .services, .reviews {{ grid-template-columns: 1fr; }}
      .section-head {{ display: block; }}
      .nav .button {{ display: none; }}
      .mobile-call {{ display: flex; }}
    }}
  </style>
</head>
<body>
  <nav class="nav">
    <div class="wrap">
      <div class="brand"><strong>{business_name}</strong><span>{city} {category}</span></div>
      <div class="nav-links"><a href="#services">Services</a><a href="#about">About</a><a href="#reviews">Reviews</a><a href="#contact">Contact</a></div>
      <a class="button dark" href="tel:{phone}">Call {phone}</a>
    </div>
  </nav>
  <header class="hero">
    <div class="wrap">
      <div class="hero-copy">
        <span class="eyebrow">{eyebrow}</span>
        <h1>{theme['hero']}</h1>
        <p>{theme['sub']}</p>
        <div class="hero-actions"><a class="button" href="tel:{phone}">Call {phone}</a><a class="ghost" href="#services">Explore services</a></div>
      </div>
    </div>
  </header>
  <div class="stats">{stat_html}</div>
  <main>
    <section id="services">
      <div class="wrap">
        <div class="section-head">
          <div><span class="eyebrow">What we do</span><h2>Everything customers need, presented with confidence.</h2></div>
          <p>Clear categories help customers understand the business before they ever pick up the phone.</p>
        </div>
        <div class="services">{service_html}</div>
      </div>
    </section>
    <section id="about">
      <div class="wrap split">
        <div class="photo" aria-label="Premium auto repair shop"></div>
        <div class="panel">
          <span class="eyebrow">Why locals choose {business_name}</span>
          <h2>Local service with a premium standard.</h2>
          <p>{business_name} gives {city} customers a cleaner way to get help: clear expertise, thoughtful communication, and service that feels organized from the first call.</p>
          <ul>
            <li>Transparent recommendations before work begins.</li>
            <li>Clear service options for common needs and urgent situations.</li>
            <li>Convenient scheduling and a polished experience from first contact to completion.</li>
          </ul>
        </div>
      </div>
    </section>
    <section id="reviews">
      <div class="wrap">
        <div class="section-head">
          <div><span class="eyebrow">Customer confidence</span><h2>{rating} stars from {review_count} reviews.</h2></div>
          <p>A premium shop website should make trust obvious immediately, especially on mobile.</p>
        </div>
        <div class="reviews">{review_html}</div>
      </div>
    </section>
    <section id="contact">
      <div class="wrap contact">
        <div class="contact-card">
          <span class="eyebrow">Schedule service</span>
          <h2>Ready for a better repair experience?</h2>
          <p>Call now for diagnostics, maintenance, brake work, inspections, or a clear second opinion.</p>
          <a class="button" href="tel:{phone}" style="margin-top:18px;background:white;color:var(--dark)">Call {phone}</a>
        </div>
        <div class="info">
          <span class="eyebrow">Shop information</span>
          <dl>
            <div><dt>Address</dt><dd>{address}</dd></div>
            <div><dt>Hours</dt><dd>{hours}</dd></div>
            <div><dt>Service area</dt><dd>{city} and nearby drivers</dd></div>
          </dl>
        </div>
      </div>
    </section>
  </main>
  <footer class="wrap">{business_name} - {category.title()} in {city}</footer>
  <a class="button mobile-call" href="tel:{phone}">Call {phone}</a>
</body>
</html>"""


def _client_concierge_html(lead: dict[str, Any], variant: str, reason: str = "client website template") -> str:
    """Render a concierge-service layout for premium repair shops."""

    business_name = escape(str(lead.get("business_name") or "Apex Motor Works"))
    niche = escape(str(lead.get("niche") or "auto repair"))
    city = escape(str(lead.get("city") or "Santa Cruz"))
    phone = escape(str(lead.get("phone") or "(831) 555-0198"))
    address = escape(str(lead.get("address") or f"{city}, CA"))
    hours = escape(str(lead.get("hours") or lead.get("opening_hours") or "Mon-Fri 8:00 AM - 6:00 PM"))
    rating = escape(str(lead.get("google_rating") or "4.9"))
    review_count = escape(str(lead.get("review_count") or "240"))
    profile = _profile(lead)
    category = escape(str(profile["category"]))
    eyebrow = escape(str(profile["eyebrow"]))
    process = [escape(str(item)) for item in profile["process"]]
    services = [(escape(str(title)), escape(str(copy))) for title, copy in profile["services"][:3]]
    reviews = [(escape(str(quote)), escape(str(name))) for quote, name in profile["reviews"]]
    stats = [(escape(str(value)), escape(str(label))) for value, label in profile["stats"]]
    accent = {"clean_modern": "#0f766e", "retro_local": "#b45309", "premium": "#7c3aed"}.get(variant, "#0f766e")
    image = str(profile["image"])
    detail_image = str(profile["detail"])
    journey_html = "".join(
        f"""<article><span>{index:02d}</span><h3>{title}</h3><p>{copy}</p></article>"""
        for index, ((title, copy), _) in enumerate(zip(services, process), start=1)
    )
    stats_html = "".join(f"<div><strong>{value}</strong><span>{label}</span></div>" for value, label in stats)
    review_quote, review_name = reviews[0]
    service_list = "".join(f"<li>{title}: {copy}</li>" for title, copy in services)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{business_name} | {category.title()} in {city}</title>
  <style>
    *{{box-sizing:border-box}} body{{margin:0;background:#f7f3ea;color:#171717;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:0}} a{{color:inherit}} .wrap{{width:min(1160px,calc(100% - 34px));margin:0 auto}}
    nav{{position:sticky;top:0;z-index:50;background:#f7f3eaee;backdrop-filter:blur(16px);border-bottom:1px solid #ded6c8}} nav .wrap{{height:78px;display:flex;align-items:center;justify-content:space-between;gap:20px}} .brand strong{{display:block;font-size:22px}} .brand span,.eyebrow{{display:block;color:#7c7468;font-size:12px;font-weight:900;text-transform:uppercase;letter-spacing:.08em}} .links{{display:flex;gap:22px;font-weight:800;font-size:14px}} .links a{{text-decoration:none}} .btn{{display:inline-flex;align-items:center;justify-content:center;min-height:46px;border-radius:8px;padding:0 20px;background:{accent};color:white;text-decoration:none;font-weight:900;box-shadow:0 16px 32px color-mix(in srgb,{accent} 34%,transparent)}}
    .hero{{padding:34px 0 76px}} .hero-grid{{display:grid;grid-template-columns:.92fr 1.08fr;gap:22px;align-items:stretch}} .hero-copy{{background:#171717;color:white;border-radius:8px;padding:clamp(30px,5vw,62px);min-height:640px;display:flex;flex-direction:column;justify-content:space-between}} h1{{font-size:clamp(48px,7vw,92px);line-height:.9;margin:18px 0 0;letter-spacing:0}} .hero-copy p{{color:#d4d4d4;font-size:20px;line-height:1.65;max-width:640px}} .hero-photo{{border-radius:8px;background:url("{image}") center/cover;min-height:640px;box-shadow:0 30px 80px rgba(0,0,0,.16)}} .hero-actions{{display:flex;gap:12px;flex-wrap:wrap;margin-top:28px}} .outline{{border:1px solid rgba(255,255,255,.35);background:transparent}}
    .stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:30px}} .stats div{{border-top:1px solid rgba(255,255,255,.22);padding-top:18px}} .stats strong{{display:block;font-size:34px}} .stats span{{color:#d4d4d4;font-weight:700}}
    section{{padding:78px 0}} .intro{{display:grid;grid-template-columns:.75fr 1.25fr;gap:34px;margin-bottom:30px}} .intro h2{{font-size:clamp(34px,5vw,66px);line-height:.96;margin:10px 0 0}} .intro p{{font-size:18px;line-height:1.7;color:#625b52}} .journey{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}} .journey article{{background:white;border:1px solid #ded6c8;border-radius:8px;padding:28px;min-height:270px;box-shadow:0 18px 48px rgba(40,32,20,.08)}} .journey span{{color:{accent};font-weight:950}} .journey h3{{font-size:26px;line-height:1.05;margin:20px 0 0}} .journey p{{color:#625b52;line-height:1.65}}
    .split{{display:grid;grid-template-columns:1fr 1fr;gap:22px;align-items:stretch}} .shop-img{{border-radius:8px;background:url("{detail_image}") center/cover;min-height:520px;box-shadow:0 24px 70px rgba(0,0,0,.13)}} .panel{{background:white;border:1px solid #ded6c8;border-radius:8px;padding:clamp(30px,5vw,58px)}} .panel h2{{font-size:clamp(34px,5vw,58px);line-height:1;margin:12px 0}} .panel p,.panel li{{color:#625b52;font-size:17px;line-height:1.75}} .panel ul{{padding-left:20px}}
    .reviews{{display:grid;grid-template-columns:1.1fr .9fr;gap:18px}} blockquote{{margin:0;background:#171717;color:white;border-radius:8px;padding:38px}} blockquote p{{font-size:25px;line-height:1.45;margin:0}} cite{{display:block;margin-top:22px;color:#d4d4d4;font-style:normal;font-weight:800}} .contact{{background:#171717;color:white;border-radius:8px;padding:38px}} .contact p{{color:#d4d4d4;line-height:1.7}} footer{{padding:34px 0 92px;text-align:center;color:#625b52}} .mobile{{display:none;position:fixed;left:14px;right:14px;bottom:14px;z-index:60}}
    @media(max-width:900px){{.hero-grid,.intro,.split,.reviews{{grid-template-columns:1fr}}.journey,.stats{{grid-template-columns:repeat(2,1fr)}}.hero-copy,.hero-photo{{min-height:auto}}.hero-photo{{height:430px}}}} @media(max-width:640px){{.links,nav .btn{{display:none}}.journey,.stats{{grid-template-columns:1fr}}h1{{font-size:48px}}.mobile{{display:flex}}}}
  </style>
</head>
<body>
  <nav><div class="wrap"><div class="brand"><strong>{business_name}</strong><span>{city} {category}</span></div><div class="links"><a href="#process">Process</a><a href="#care">Care</a><a href="#reviews">Reviews</a><a href="#contact">Contact</a></div><a class="btn" href="tel:{phone}">Call {phone}</a></div></nav>
  <header class="hero"><div class="wrap hero-grid"><div class="hero-copy"><div><span class="eyebrow">{eyebrow}</span><h1>{escape(str(profile["concierge_hero"]))}</h1><p>{escape(str(profile["sub"]))}</p><div class="hero-actions"><a class="btn" href="tel:{phone}">Call {phone}</a><a class="btn outline" href="#process">See the process</a></div></div><div class="stats">{stats_html}</div></div><div class="hero-photo"></div></div></header>
  <main>
    <section id="process"><div class="wrap"><div class="intro"><div><span class="eyebrow">The service journey</span><h2>A calmer way to get expert help.</h2></div><p>Customers can quickly understand what happens next, from the first call through the visit, approval, and completion.</p></div><div class="journey">{journey_html}</div></div></section>
    <section id="care"><div class="wrap split"><div class="shop-img"></div><div class="panel"><span class="eyebrow">What we handle</span><h2>Focused services, clear expectations, and high-attention care.</h2><p>Built for customers who want expertise without confusion.</p><ul>{service_list}</ul></div></div></section>
    <section id="reviews"><div class="wrap reviews"><blockquote><p>"{review_quote}"</p><cite>{review_name}</cite></blockquote><div class="contact" id="contact"><span class="eyebrow">Schedule service</span><h2>Call {business_name}</h2><p>{address}<br>{hours}<br>{rating} rating from {review_count} reviews</p><a class="btn" href="tel:{phone}">Call {phone}</a></div></div></section>
  </main>
  <footer class="wrap">{business_name} - {category.title()} in {city}</footer><a class="btn mobile" href="tel:{phone}">Call {phone}</a>
</body>
</html>"""


def _client_performance_html(lead: dict[str, Any], variant: str, reason: str = "client website template") -> str:
    """Render a bold performance-garage layout for visual variety."""

    business_name = escape(str(lead.get("business_name") or "Apex Motor Works"))
    niche = escape(str(lead.get("niche") or "auto repair"))
    city = escape(str(lead.get("city") or "Santa Cruz"))
    phone = escape(str(lead.get("phone") or "(831) 555-0198"))
    address = escape(str(lead.get("address") or f"{city}, CA"))
    hours = escape(str(lead.get("hours") or lead.get("opening_hours") or "Mon-Fri 8:00 AM - 6:00 PM"))
    rating = escape(str(lead.get("google_rating") or "4.9"))
    profile = _profile(lead)
    category = escape(str(profile["category"]))
    eyebrow = escape(str(profile["eyebrow"]))
    services = [(escape(str(title)), escape(str(copy))) for title, copy in profile["services"][:3]]
    stats = [(escape(str(value)), escape(str(label))) for value, label in profile["stats"]]
    accent = {"clean_modern": "#f97316", "retro_local": "#ef4444", "premium": "#22c55e"}.get(variant, "#f97316")
    hero = str(profile["image"])
    detail = str(profile["detail"])
    stats_html = "".join(f"<div><strong>{value}</strong><span>{label}</span></div>" for value, label in stats)
    service_cards = "".join(
        f"""<article class="card"><span>{index:02d}</span><h3>{title}</h3><p>{copy}</p></article>"""
        for index, (title, copy) in enumerate(services, start=1)
    )
    service_list = "".join(f"<li>{title}: {copy}</li>" for title, copy in services)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{business_name} | {city} {category.title()}</title>
  <style>
    *{{box-sizing:border-box}} body{{margin:0;background:#070707;color:#f8fafc;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:0}} a{{color:inherit}} .wrap{{width:min(1180px,calc(100% - 34px));margin:0 auto}} .accent{{color:{accent}}}
    nav{{position:sticky;top:0;z-index:50;background:#070707e8;backdrop-filter:blur(18px);border-bottom:1px solid rgba(255,255,255,.12)}} nav .wrap{{height:76px;display:flex;align-items:center;justify-content:space-between;gap:20px}} .brand strong{{font-size:22px}} .brand span,.eyebrow{{display:block;color:#a1a1aa;font-size:12px;font-weight:900;text-transform:uppercase;letter-spacing:.08em}} .links{{display:flex;gap:22px;font-size:14px;font-weight:800}} .links a{{text-decoration:none}} .btn{{display:inline-flex;align-items:center;justify-content:center;min-height:46px;border-radius:8px;padding:0 20px;background:{accent};color:#070707;text-decoration:none;font-weight:950}}
    .hero{{position:relative;min-height:760px;display:grid;align-items:end;overflow:hidden}} .hero:before{{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.2),#070707 92%),linear-gradient(90deg,#070707 0%,rgba(0,0,0,.55) 42%,rgba(0,0,0,.1)),url("{hero}") center/cover}} .hero .wrap{{position:relative;padding:120px 0 70px}} h1{{max-width:880px;margin:18px 0 0;font-size:clamp(54px,9vw,118px);line-height:.82;letter-spacing:0;text-transform:uppercase}} .hero p{{max-width:640px;color:#d4d4d8;font-size:20px;line-height:1.7}} .hero-row{{display:flex;gap:12px;flex-wrap:wrap;margin-top:30px}} .ghost{{border:1px solid rgba(255,255,255,.25);background:transparent;color:white}}
    .stripe{{background:{accent};color:#070707}} .stripe .wrap{{display:grid;grid-template-columns:repeat(4,1fr);gap:1px}} .stripe div{{padding:26px 18px;border-left:1px solid rgba(0,0,0,.18)}} .stripe strong{{display:block;font-size:36px}} .stripe span{{font-weight:800}}
    section{{padding:84px 0}} .head{{display:flex;justify-content:space-between;gap:28px;align-items:end;margin-bottom:32px}} .head h2{{max-width:760px;font-size:clamp(36px,5vw,66px);line-height:.9;margin:10px 0 0;text-transform:uppercase}} .head p{{max-width:430px;color:#a1a1aa;line-height:1.7}} .grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}} .card{{border:1px solid rgba(255,255,255,.12);background:#111113;border-radius:8px;padding:28px;min-height:310px}} .card span{{color:{accent};font-weight:950}} .card h3{{font-size:28px;line-height:1;margin:22px 0}} .card p{{color:#a1a1aa;line-height:1.65}}
    .split{{display:grid;grid-template-columns:1.1fr .9fr;gap:22px}} .photo{{min-height:560px;border-radius:8px;background:url("{detail}") center/cover}} .panel{{background:#f8fafc;color:#111827;border-radius:8px;padding:clamp(32px,5vw,60px)}} .panel h2{{font-size:clamp(34px,5vw,62px);line-height:.95;margin:12px 0}} .panel p,.panel li{{color:#4b5563;line-height:1.75;font-size:17px}} .contact{{border-radius:8px;background:#111113;border:1px solid rgba(255,255,255,.12);padding:34px;display:grid;grid-template-columns:1fr auto;gap:24px;align-items:center}} footer{{padding:36px 0 94px;text-align:center;color:#a1a1aa}} .mobile{{display:none;position:fixed;left:14px;right:14px;bottom:14px;z-index:60}}
    @media(max-width:900px){{.stripe .wrap,.grid,.split,.contact{{grid-template-columns:1fr}}.hero{{min-height:680px}}}} @media(max-width:640px){{.links,nav .btn{{display:none}}h1{{font-size:52px}}.mobile{{display:flex}}}}
  </style>
</head>
<body>
  <nav><div class="wrap"><div class="brand"><strong>{business_name}</strong><span>{city} {category}</span></div><div class="links"><a href="#work">Work</a><a href="#standard">Standard</a><a href="#contact">Contact</a></div><a class="btn" href="tel:{phone}">Call {phone}</a></div></nav>
  <header class="hero"><div class="wrap"><span class="eyebrow">{eyebrow}</span><h1>{escape(str(profile["performance_hero"]))}</h1><p>{escape(str(profile["sub"]))}</p><div class="hero-row"><a class="btn" href="tel:{phone}">Call {phone}</a><a class="btn ghost" href="#work">View services</a></div></div></header>
  <div class="stripe"><div class="wrap">{stats_html}</div></div>
  <main>
    <section id="work"><div class="wrap"><div class="head"><div><span class="eyebrow">Core services</span><h2>Sharp expertise. Clean execution.</h2></div><p>Everything is positioned for customers who want speed, clarity, and confidence.</p></div><div class="grid">{service_cards}</div></div></section>
    <section id="standard"><div class="wrap split"><div class="photo"></div><div class="panel"><span class="eyebrow">The standard</span><h2>Local team. Premium process.</h2><p>Customers get the confidence they expect from a polished service brand with the practicality of a local specialist.</p><ul>{service_list}</ul></div></div></section>
    <section id="contact"><div class="wrap contact"><div><span class="eyebrow">Schedule service</span><h2>Call {business_name}</h2><p>{address}<br>{hours}</p></div><a class="btn" href="tel:{phone}">Call {phone}</a></div></section>
  </main>
  <footer class="wrap">{business_name} - {category.title()} in {city}</footer><a class="btn mobile" href="tel:{phone}">Call {phone}</a>
</body>
</html>"""


def _client_editorial_html(lead: dict[str, Any], variant: str, reason: str = "client website template") -> str:
    """Render an editorial magazine-style local business site."""

    c = _client_bits(lead)
    accent = {"clean_modern": "#2563eb", "retro_local": "#c2410c", "premium": "#0f766e"}.get(variant, "#2563eb")
    service_html = "".join(
        f"<article><span>{index:02d}</span><h3>{title}</h3><p>{copy}</p></article>"
        for index, (title, copy) in enumerate(c["services"][:4], start=1)
    )
    stat_html = "".join(f"<div><strong>{value}</strong><span>{label}</span></div>" for value, label in c["stats"])
    quote, reviewer = c["reviews"][0]
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{c['business_name']} | {c['category'].title()} in {c['city']}</title>
  <style>
    *{{box-sizing:border-box}} body{{margin:0;background:#fafaf7;color:#171717;font-family:Georgia,"Times New Roman",serif;letter-spacing:0}} a{{color:inherit}} .wrap{{width:min(1160px,calc(100% - 34px));margin:0 auto}} .sans{{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
    nav{{position:sticky;top:0;z-index:50;background:#fafaf7ee;backdrop-filter:blur(16px);border-bottom:1px solid #dedbd2}} nav .wrap{{min-height:74px;display:flex;align-items:center;justify-content:space-between;gap:20px}} .brand strong{{font-family:Inter,ui-sans-serif,system-ui;font-size:20px}} .eyebrow,.brand span{{display:block;color:{accent};font-family:Inter,ui-sans-serif,system-ui;font-size:12px;font-weight:900;text-transform:uppercase;letter-spacing:.08em}} .btn{{display:inline-flex;min-height:46px;align-items:center;justify-content:center;border-radius:8px;padding:0 20px;background:#171717;color:white;text-decoration:none;font-family:Inter,ui-sans-serif,system-ui;font-weight:900}}
    .hero{{padding:44px 0 72px}} .hero-grid{{display:grid;grid-template-columns:1.1fr .9fr;gap:26px;align-items:end}} h1{{max-width:840px;margin:18px 0 0;font-size:clamp(58px,9vw,118px);line-height:.86;letter-spacing:0}} .lead{{font-family:Inter,ui-sans-serif,system-ui;max-width:640px;color:#57534e;font-size:20px;line-height:1.7}} .photo{{min-height:620px;border-radius:8px;background:linear-gradient(180deg,rgba(0,0,0,0),rgba(0,0,0,.18)),url("{c['hero_image']}") center/cover;box-shadow:0 24px 70px rgba(0,0,0,.14)}} .stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:#dedbd2;border:1px solid #dedbd2}} .stats div{{background:white;padding:24px}} .stats strong{{display:block;font-family:Inter,ui-sans-serif,system-ui;font-size:34px}} .stats span{{font-family:Inter,ui-sans-serif,system-ui;color:#57534e;font-weight:750}}
    section{{padding:76px 0}} .section-head{{display:flex;align-items:end;justify-content:space-between;gap:26px;margin-bottom:28px}} .section-head h2{{margin:10px 0 0;font-size:clamp(38px,5vw,70px);line-height:.92;max-width:760px}} .section-head p{{font-family:Inter,ui-sans-serif,system-ui;max-width:420px;color:#57534e;line-height:1.7}} .services{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}} .services article{{border-top:3px solid {accent};background:white;border-radius:8px;padding:24px;min-height:285px;box-shadow:0 16px 44px rgba(23,23,23,.08)}} .services span{{font-family:Inter,ui-sans-serif,system-ui;color:{accent};font-weight:950}} .services h3{{font-size:30px;line-height:1;margin:20px 0 0}} .services p{{font-family:Inter,ui-sans-serif,system-ui;color:#57534e;line-height:1.65}}
    .quote{{background:#171717;color:white;border-radius:8px;padding:clamp(30px,5vw,62px);display:grid;grid-template-columns:1fr .75fr;gap:28px;align-items:center}} blockquote{{margin:0;font-size:clamp(30px,4vw,56px);line-height:1.04}} cite{{display:block;margin-top:20px;color:#d4d4d4;font-family:Inter,ui-sans-serif,system-ui;font-style:normal;font-weight:800}} .mini-photo{{min-height:360px;border-radius:8px;background:url("{c['detail_image']}") center/cover}} footer{{padding:34px 0 94px;text-align:center;color:#57534e;font-family:Inter,ui-sans-serif,system-ui}} .mobile{{display:none;position:fixed;left:14px;right:14px;bottom:14px;z-index:60}}
    @media(max-width:920px){{.hero-grid,.quote{{grid-template-columns:1fr}}.services,.stats{{grid-template-columns:repeat(2,1fr)}}.photo{{min-height:440px}}}} @media(max-width:640px){{nav .btn{{display:none}}h1{{font-size:50px}}.services,.stats{{grid-template-columns:1fr}}.section-head{{display:block}}.mobile{{display:flex}}}}
  </style>
</head>
<body>
  <nav><div class="wrap"><div class="brand sans"><strong>{c['business_name']}</strong><span>{c['city']} {c['category']}</span></div><a class="btn" href="tel:{c['phone']}">Call {c['phone']}</a></div></nav>
  <header class="hero"><div class="wrap hero-grid"><div><span class="eyebrow">{c['eyebrow']}</span><h1>{c['hero']}</h1><p class="lead">{c['sub']}</p><a class="btn" href="#contact">Schedule service</a></div><div class="photo"></div></div></header>
  <div class="wrap stats">{stat_html}</div>
  <main>
    <section><div class="wrap"><div class="section-head"><div><span class="eyebrow">Services</span><h2>Expert help, organized like a premium publication.</h2></div><p>Customers see the offer, the proof, and the next step without reading a wall of text.</p></div><div class="services">{service_html}</div></div></section>
    <section><div class="wrap quote"><div><blockquote>"{quote}"</blockquote><cite>{reviewer}</cite></div><div class="mini-photo"></div></div></section>
    <section id="contact"><div class="wrap section-head"><div><span class="eyebrow">Visit or call</span><h2>{c['business_name']}</h2></div><p>{c['address']}<br>{c['hours']}<br>{c['rating']} rating from {c['review_count']} reviews</p></div></section>
  </main>
  <footer class="wrap">{c['business_name']} - {c['category'].title()} in {c['city']}</footer><a class="btn mobile" href="tel:{c['phone']}">Call {c['phone']}</a>
</body>
</html>"""


def _client_booking_html(lead: dict[str, Any], variant: str, reason: str = "client website template") -> str:
    """Render a conversion-first booking website with dense useful sections."""

    c = _client_bits(lead)
    accent = {"clean_modern": "#0284c7", "retro_local": "#be123c", "premium": "#7c3aed"}.get(variant, "#0284c7")
    service_rows = "".join(f"<li><strong>{title}</strong><span>{copy}</span></li>" for title, copy in c["services"][:4])
    stats = "".join(f"<div><strong>{value}</strong><span>{label}</span></div>" for value, label in c["stats"])
    review_cards = "".join(f"<blockquote><p>{quote}</p><cite>{name}</cite></blockquote>" for quote, name in c["reviews"][:2])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{c['business_name']} | Book {c['category'].title()}</title>
  <style>
    *{{box-sizing:border-box}} body{{margin:0;background:#eef2f7;color:#0f172a;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:0}} a{{color:inherit}} .wrap{{width:min(1180px,calc(100% - 34px));margin:0 auto}} .btn{{display:inline-flex;align-items:center;justify-content:center;min-height:48px;border-radius:8px;padding:0 20px;background:{accent};color:white;text-decoration:none;font-weight:950;box-shadow:0 18px 36px color-mix(in srgb,{accent} 30%,transparent)}} .eyebrow{{color:{accent};font-size:12px;font-weight:950;text-transform:uppercase;letter-spacing:.08em}}
    nav{{position:sticky;top:0;z-index:50;background:#fffffff2;backdrop-filter:blur(18px);border-bottom:1px solid #dbe3ef}} nav .wrap{{height:74px;display:flex;align-items:center;justify-content:space-between;gap:18px}} .brand strong{{display:block;font-size:21px}} .brand span{{color:#64748b;font-size:13px;font-weight:800}} .hero{{padding:46px 0}} .grid{{display:grid;grid-template-columns:1fr 420px;gap:18px;align-items:stretch}} .hero-card{{border-radius:8px;background:white;padding:clamp(30px,5vw,64px);box-shadow:0 24px 70px rgba(15,23,42,.13);border:1px solid #dbe3ef}} h1{{max-width:760px;margin:14px 0 0;font-size:clamp(48px,7vw,88px);line-height:.9;letter-spacing:0}} .hero-card p{{max-width:640px;color:#475569;font-size:19px;line-height:1.7}} .booking{{border-radius:8px;background:#0f172a;color:white;padding:26px;display:flex;flex-direction:column;gap:16px;box-shadow:0 24px 70px rgba(15,23,42,.2)}} .booking h2{{font-size:32px;line-height:1;margin:0}} .field{{border-radius:8px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.12);padding:15px;color:#cbd5e1}} .booking .btn{{background:white;color:#0f172a;box-shadow:none}} .photo{{height:260px;border-radius:8px;background:url("{c['hero_image']}") center/cover;margin-top:20px}}
    .stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:18px}} .stats div{{border-radius:8px;background:#f8fafc;border:1px solid #dbe3ef;padding:18px}} .stats strong{{display:block;font-size:30px}} .stats span{{display:block;margin-top:6px;color:#64748b;font-weight:750}} section{{padding:56px 0}} .split{{display:grid;grid-template-columns:.9fr 1.1fr;gap:18px}} .panel{{border-radius:8px;background:white;border:1px solid #dbe3ef;padding:32px;box-shadow:0 18px 50px rgba(15,23,42,.08)}} .panel h2{{font-size:clamp(34px,5vw,58px);line-height:1;margin:10px 0}} .services{{list-style:none;margin:0;padding:0;display:grid;gap:12px}} .services li{{display:grid;grid-template-columns:190px 1fr;gap:16px;border-bottom:1px solid #e2e8f0;padding:18px 0}} .services span{{color:#64748b;line-height:1.6}} .image-panel{{min-height:520px;border-radius:8px;background:url("{c['detail_image']}") center/cover;box-shadow:0 18px 50px rgba(15,23,42,.1)}} .reviews{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}} blockquote{{margin:0;background:white;border:1px solid #dbe3ef;border-radius:8px;padding:24px}} blockquote p{{color:#334155;line-height:1.65}} cite{{font-style:normal;font-weight:900}} footer{{padding:30px 0 94px;text-align:center;color:#64748b}} .mobile{{display:none;position:fixed;left:14px;right:14px;bottom:14px;z-index:60}}
    @media(max-width:900px){{.grid,.split{{grid-template-columns:1fr}}.stats{{grid-template-columns:repeat(2,1fr)}}}} @media(max-width:640px){{nav .btn{{display:none}}h1{{font-size:46px}}.stats,.reviews{{grid-template-columns:1fr}}.services li{{grid-template-columns:1fr}}.mobile{{display:flex}}}}
  </style>
</head>
<body>
  <nav><div class="wrap"><div class="brand"><strong>{c['business_name']}</strong><span>{c['category']} in {c['city']}</span></div><a class="btn" href="tel:{c['phone']}">Call {c['phone']}</a></div></nav>
  <header class="hero"><div class="wrap grid"><div class="hero-card"><span class="eyebrow">{c['eyebrow']}</span><h1>{c['hero']}</h1><p>{c['sub']}</p><div class="stats">{stats}</div><div class="photo"></div></div><aside class="booking"><span class="eyebrow">Fast booking</span><h2>Start here.</h2><div class="field">1. Choose the service you need</div><div class="field">2. Call for the fastest opening</div><div class="field">3. Get clear next steps</div><a class="btn" href="tel:{c['phone']}">Call {c['phone']}</a><p>{c['address']}<br>{c['hours']}</p></aside></div></header>
  <main><section><div class="wrap split"><div class="image-panel"></div><div class="panel"><span class="eyebrow">Service menu</span><h2>Clear options, easy decisions.</h2><ul class="services">{service_rows}</ul></div></div></section><section><div class="wrap reviews">{review_cards}</div></section></main>
  <footer class="wrap">{c['business_name']} - {c['city']} {c['category']}</footer><a class="btn mobile" href="tel:{c['phone']}">Call {c['phone']}</a>
</body>
</html>"""


def _client_local_proof_html(lead: dict[str, Any], variant: str, reason: str = "client website template") -> str:
    """Render a neighborhood-proof website with reviews and local trust first."""

    c = _client_bits(lead)
    accent = {"clean_modern": "#0d9488", "retro_local": "#a16207", "premium": "#4f46e5"}.get(variant, "#0d9488")
    services = "".join(f"<article><h3>{title}</h3><p>{copy}</p></article>" for title, copy in c["services"][:3])
    stats = "".join(f"<div><strong>{value}</strong><span>{label}</span></div>" for value, label in c["stats"])
    reviews = "".join(f"<blockquote><p>{quote}</p><cite>{name}</cite></blockquote>" for quote, name in c["reviews"])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{c['business_name']} | Local {c['category'].title()}</title>
  <style>
    *{{box-sizing:border-box}} body{{margin:0;background:#fffdf7;color:#1c1917;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:0}} a{{color:inherit}} .wrap{{width:min(1140px,calc(100% - 34px));margin:0 auto}} .btn{{display:inline-flex;min-height:46px;align-items:center;justify-content:center;border-radius:8px;padding:0 20px;background:{accent};color:white;text-decoration:none;font-weight:950}} .eyebrow{{color:{accent};font-size:12px;font-weight:950;text-transform:uppercase;letter-spacing:.08em}}
    nav{{border-bottom:1px solid #e7e0d2;background:#fffdf7}} nav .wrap{{height:74px;display:flex;align-items:center;justify-content:space-between}} .brand strong{{font-size:22px}} .hero{{padding:52px 0 38px}} h1{{font-size:clamp(50px,8vw,96px);line-height:.88;margin:16px 0 0;max-width:920px}} .hero p{{color:#57534e;font-size:20px;line-height:1.7;max-width:690px}} .hero-photo{{margin-top:34px;min-height:500px;border-radius:8px;background:linear-gradient(180deg,rgba(0,0,0,.08),rgba(0,0,0,.32)),url("{c['portrait_image']}") center/cover;display:flex;align-items:end;padding:24px;color:white;box-shadow:0 24px 70px rgba(28,25,23,.14)}} .proof{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:16px}} .proof div{{background:white;border:1px solid #e7e0d2;border-radius:8px;padding:20px}} .proof strong{{font-size:32px}} .proof span{{display:block;color:#78716c;margin-top:6px;font-weight:750}}
    section{{padding:62px 0}} .two{{display:grid;grid-template-columns:.78fr 1.22fr;gap:18px}} .card{{background:white;border:1px solid #e7e0d2;border-radius:8px;padding:30px;box-shadow:0 16px 44px rgba(28,25,23,.07)}} .card h2{{font-size:clamp(34px,5vw,60px);line-height:1;margin:12px 0}} .services{{display:grid;gap:14px}} .services article{{background:#f8f4ea;border-radius:8px;padding:24px}} .services h3{{margin:0;font-size:25px}} .services p{{color:#57534e;line-height:1.65}} .reviews{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}} blockquote{{margin:0;background:#1c1917;color:white;border-radius:8px;padding:24px}} blockquote p{{line-height:1.6;color:#f5f5f4}} cite{{display:block;margin-top:18px;font-style:normal;font-weight:900;color:#d6d3d1}} footer{{padding:34px 0 92px;color:#78716c;text-align:center}} .mobile{{display:none;position:fixed;left:14px;right:14px;bottom:14px;z-index:60}}
    @media(max-width:900px){{.proof{{grid-template-columns:repeat(2,1fr)}}.two,.reviews{{grid-template-columns:1fr}}}} @media(max-width:640px){{nav .btn{{display:none}}h1{{font-size:46px}}.proof{{grid-template-columns:1fr}}.hero-photo{{min-height:380px}}.mobile{{display:flex}}}}
  </style>
</head>
<body>
  <nav><div class="wrap"><div class="brand"><strong>{c['business_name']}</strong></div><a class="btn" href="tel:{c['phone']}">Call {c['phone']}</a></div></nav>
  <header class="hero"><div class="wrap"><span class="eyebrow">{c['city']} recommended {c['category']}</span><h1>{c['hero']}</h1><p>{c['sub']}</p><a class="btn" href="#contact">Get help today</a><div class="hero-photo"><h2>{c['rating']} stars from {c['review_count']} local reviews</h2></div><div class="proof">{stats}</div></div></header>
  <main><section><div class="wrap two"><div class="card"><span class="eyebrow">Local confidence</span><h2>Proof before pitch.</h2><p>{c['business_name']} leads with clear services, real contact details, and trust signals customers can scan fast.</p></div><div class="services">{services}</div></div></section><section><div class="wrap reviews">{reviews}</div></section><section id="contact"><div class="wrap card"><span class="eyebrow">Call or visit</span><h2>{c['business_name']}</h2><p>{c['address']}<br>{c['hours']}</p><a class="btn" href="tel:{c['phone']}">Call {c['phone']}</a></div></section></main>
  <footer class="wrap">{c['business_name']} - {c['category'].title()} in {c['city']}</footer><a class="btn mobile" href="tel:{c['phone']}">Call {c['phone']}</a>
</body>
</html>"""


def _client_luxury_card_html(lead: dict[str, Any], variant: str, reason: str = "client website template") -> str:
    """Render a high-end dark card layout with layered photography."""

    c = _client_bits(lead)
    accent = {"clean_modern": "#60a5fa", "retro_local": "#f59e0b", "premium": "#34d399"}.get(variant, "#34d399")
    services = "".join(f"<article><span>{index:02d}</span><h3>{title}</h3><p>{copy}</p></article>" for index, (title, copy) in enumerate(c["services"][:4], start=1))
    stats = "".join(f"<div><strong>{value}</strong><span>{label}</span></div>" for value, label in c["stats"])
    quote, name = c["reviews"][1]
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{c['business_name']} | Premium {c['category'].title()}</title>
  <style>
    *{{box-sizing:border-box}} body{{margin:0;background:#08080a;color:#f8fafc;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:0}} a{{color:inherit}} .wrap{{width:min(1180px,calc(100% - 34px));margin:0 auto}} .btn{{display:inline-flex;min-height:48px;align-items:center;justify-content:center;border-radius:8px;padding:0 20px;background:{accent};color:#08080a;text-decoration:none;font-weight:950}} .eyebrow{{color:{accent};font-size:12px;font-weight:950;text-transform:uppercase;letter-spacing:.08em}}
    nav{{position:sticky;top:0;z-index:50;background:#08080ade;backdrop-filter:blur(18px);border-bottom:1px solid rgba(255,255,255,.12)}} nav .wrap{{height:76px;display:flex;align-items:center;justify-content:space-between}} .brand strong{{font-size:22px}} .brand span{{display:block;color:#a1a1aa;font-size:13px;font-weight:800}} .hero{{padding:56px 0}} .frame{{border:1px solid rgba(255,255,255,.12);border-radius:8px;padding:18px;background:linear-gradient(145deg,rgba(255,255,255,.08),rgba(255,255,255,.03));box-shadow:0 34px 90px rgba(0,0,0,.45)}} .hero-grid{{display:grid;grid-template-columns:1fr .85fr;gap:18px}} .hero-copy{{padding:clamp(28px,5vw,58px)}} h1{{font-size:clamp(50px,8vw,104px);line-height:.84;margin:16px 0 0}} .hero-copy p{{max-width:620px;color:#cbd5e1;font-size:20px;line-height:1.7}} .photo{{min-height:650px;border-radius:8px;background:linear-gradient(180deg,rgba(0,0,0,0),rgba(0,0,0,.42)),url("{c['hero_image']}") center/cover}} .stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:28px}} .stats div{{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.1);border-radius:8px;padding:18px}} .stats strong{{font-size:32px}} .stats span{{display:block;color:#a1a1aa;margin-top:6px;font-weight:750}}
    section{{padding:68px 0}} .services{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}} .services article{{background:#111114;border:1px solid rgba(255,255,255,.1);border-radius:8px;padding:24px;min-height:300px}} .services span{{color:{accent};font-weight:950}} .services h3{{font-size:27px;line-height:1;margin:22px 0}} .services p{{color:#a1a1aa;line-height:1.65}} .split{{display:grid;grid-template-columns:.9fr 1.1fr;gap:18px}} .texture{{min-height:460px;border-radius:8px;background:url("{c['texture_image']}") center/cover}} .panel{{border-radius:8px;background:#f8fafc;color:#111827;padding:clamp(30px,5vw,58px)}} .panel h2{{font-size:clamp(34px,5vw,62px);line-height:.94;margin:12px 0}} .panel p{{color:#475569;line-height:1.75}} footer{{padding:34px 0 94px;text-align:center;color:#a1a1aa}} .mobile{{display:none;position:fixed;left:14px;right:14px;bottom:14px;z-index:60}}
    @media(max-width:940px){{.hero-grid,.split{{grid-template-columns:1fr}}.services,.stats{{grid-template-columns:repeat(2,1fr)}}.photo{{min-height:440px}}}} @media(max-width:640px){{nav .btn{{display:none}}h1{{font-size:48px}}.services,.stats{{grid-template-columns:1fr}}.mobile{{display:flex}}}}
  </style>
</head>
<body>
  <nav><div class="wrap"><div class="brand"><strong>{c['business_name']}</strong><span>{c['category']} in {c['city']}</span></div><a class="btn" href="tel:{c['phone']}">Call {c['phone']}</a></div></nav>
  <header class="hero"><div class="wrap frame"><div class="hero-grid"><div class="hero-copy"><span class="eyebrow">{c['eyebrow']}</span><h1>{c['hero']}</h1><p>{c['sub']}</p><a class="btn" href="#contact">Start now</a><div class="stats">{stats}</div></div><div class="photo"></div></div></div></header>
  <main><section><div class="wrap services">{services}</div></section><section><div class="wrap split"><div class="texture"></div><div class="panel"><span class="eyebrow">Customer voice</span><h2>"{quote}"</h2><p>- {name}</p><p>{c['business_name']} turns a local service page into a premium brand moment with focused services, credible proof, and a direct call path.</p></div></div></section><section id="contact"><div class="wrap panel"><span class="eyebrow">Schedule service</span><h2>Call {c['business_name']}</h2><p>{c['address']}<br>{c['hours']}</p><a class="btn" href="tel:{c['phone']}">Call {c['phone']}</a></div></section></main>
  <footer class="wrap">{c['business_name']} - Premium {c['category'].title()} in {c['city']}</footer><a class="btn mobile" href="tel:{c['phone']}">Call {c['phone']}</a>
</body>
</html>"""


def _client_service_menu_html(lead: dict[str, Any], variant: str, reason: str = "client website template") -> str:
    """Render a crisp service-menu layout built for scanning and mobile action."""

    c = _client_bits(lead)
    accent = {"clean_modern": "#0891b2", "retro_local": "#b91c1c", "premium": "#16a34a"}.get(variant, "#0891b2")
    services = "".join(f"<article><h3>{title}</h3><p>{copy}</p><a href='tel:{c['phone']}'>Ask about {title}</a></article>" for title, copy in c["services"][:4])
    stats = "".join(f"<li><strong>{value}</strong><span>{label}</span></li>" for value, label in c["stats"])
    review, reviewer = c["reviews"][2]
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{c['business_name']} | {c['category'].title()}</title>
  <style>
    *{{box-sizing:border-box}} body{{margin:0;background:#f8fafc;color:#0f172a;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:0}} a{{color:inherit}} .wrap{{width:min(1180px,calc(100% - 34px));margin:0 auto}} .btn{{display:inline-flex;min-height:46px;align-items:center;justify-content:center;border-radius:8px;padding:0 20px;background:{accent};color:white;text-decoration:none;font-weight:950}} .eyebrow{{color:{accent};font-size:12px;font-weight:950;text-transform:uppercase;letter-spacing:.08em}}
    .top{{background:#0f172a;color:white}} nav .wrap{{height:76px;display:flex;align-items:center;justify-content:space-between}} .brand strong{{font-size:22px}} .hero{{padding:58px 0}} .hero-grid{{display:grid;grid-template-columns:.95fr 1.05fr;gap:22px;align-items:stretch}} .hero-copy{{display:flex;flex-direction:column;justify-content:center}} h1{{font-size:clamp(50px,8vw,104px);line-height:.86;margin:16px 0 0}} .hero-copy p{{color:#cbd5e1;font-size:20px;line-height:1.7;max-width:620px}} .hero-photo{{min-height:560px;border-radius:8px;background:url("{c['detail_image']}") center/cover}} .proof{{display:grid;grid-template-columns:repeat(4,1fr);gap:0;list-style:none;padding:0;margin:0;border-top:1px solid rgba(255,255,255,.14)}} .proof li{{padding:24px;border-right:1px solid rgba(255,255,255,.14)}} .proof strong{{display:block;font-size:32px}} .proof span{{display:block;color:#cbd5e1;margin-top:6px;font-weight:750}}
    section{{padding:70px 0}} .head{{display:flex;align-items:end;justify-content:space-between;gap:28px;margin-bottom:26px}} .head h2{{font-size:clamp(36px,5vw,68px);line-height:.92;margin:10px 0 0;max-width:720px}} .head p{{max-width:420px;color:#64748b;line-height:1.7}} .menu{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}} .menu article{{background:white;border:1px solid #dbe3ef;border-radius:8px;padding:26px;min-height:250px;box-shadow:0 16px 44px rgba(15,23,42,.07)}} .menu h3{{font-size:30px;margin:0}} .menu p{{color:#64748b;line-height:1.65}} .menu a{{display:inline-flex;margin-top:10px;color:{accent};font-weight:950;text-decoration:none}} .banner{{border-radius:8px;background:white;border:1px solid #dbe3ef;padding:34px;display:grid;grid-template-columns:1.1fr .9fr;gap:22px;align-items:center}} .banner blockquote{{font-size:clamp(28px,4vw,52px);line-height:1.05;margin:0}} .banner p{{color:#64748b;line-height:1.7}} .banner-img{{min-height:320px;border-radius:8px;background:url("{c['portrait_image']}") center/cover}} footer{{padding:34px 0 94px;text-align:center;color:#64748b}} .mobile{{display:none;position:fixed;left:14px;right:14px;bottom:14px;z-index:60}}
    @media(max-width:900px){{.hero-grid,.banner{{grid-template-columns:1fr}}.proof{{grid-template-columns:repeat(2,1fr)}}}} @media(max-width:640px){{nav .btn{{display:none}}h1{{font-size:48px}}.proof,.menu{{grid-template-columns:1fr}}.hero-photo{{min-height:380px}}.mobile{{display:flex}}}}
  </style>
</head>
<body>
  <div class="top"><nav><div class="wrap"><div class="brand"><strong>{c['business_name']}</strong></div><a class="btn" href="tel:{c['phone']}">Call {c['phone']}</a></div></nav><header class="hero"><div class="wrap hero-grid"><div class="hero-copy"><span class="eyebrow">{c['eyebrow']}</span><h1>{c['hero']}</h1><p>{c['sub']}</p><a class="btn" href="#menu">See services</a></div><div class="hero-photo"></div></div></header><ul class="wrap proof">{stats}</ul></div>
  <main><section id="menu"><div class="wrap"><div class="head"><div><span class="eyebrow">Service menu</span><h2>Everything is easy to scan and easy to book.</h2></div><p>{c['business_name']} gives customers direct language, useful categories, and a strong mobile call path.</p></div><div class="menu">{services}</div></div></section><section><div class="wrap banner"><div><span class="eyebrow">Review highlight</span><blockquote>"{review}"</blockquote><p>- {reviewer}</p></div><div class="banner-img"></div></div></section><section id="contact"><div class="wrap banner"><div><span class="eyebrow">Contact</span><h2>{c['business_name']}</h2><p>{c['address']}<br>{c['hours']}<br>{c['rating']} rating from {c['review_count']} reviews</p></div><a class="btn" href="tel:{c['phone']}">Call {c['phone']}</a></div></section></main>
  <footer class="wrap">{c['business_name']} - {c['category'].title()} in {c['city']}</footer><a class="btn mobile" href="tel:{c['phone']}">Call {c['phone']}</a>
</body>
</html>"""


def run(lead: dict[str, Any], variant: str, previous_critique: dict[str, Any] | None = None) -> str:
    """Generate a valid single-file Tailwind HTML mockup."""

    lead_id = _lead_id(lead)
    business_name = str(lead.get("business_name") or "")
    user_prompt = _prompt(lead, variant, previous_critique)
    last_payload: dict[str, Any] | None = None

    if _template_mode_enabled():
        html = _client_website_html(lead, variant)
        _safe_log(
            "generate_mockup",
            "succeeded",
            f"rendered client website {variant} mockup for {business_name}.",
            lead_id,
            {"variant": variant, "renderer": "client_website_template"},
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
            html = _client_website_html(lead, variant, str(exc))
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
