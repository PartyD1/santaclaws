import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";

export const runtime = "nodejs";

function env(name: string) {
  return process.env[name]?.trim() ?? "";
}

function supabaseClient() {
  const url = env("SUPABASE_URL") || env("NEXT_PUBLIC_SUPABASE_URL");
  const key = env("SUPABASE_SERVICE_KEY") || env("SUPABASE_ANON_KEY") || env("NEXT_PUBLIC_SUPABASE_ANON_KEY");
  if (!url || !key) {
    return null;
  }
  return createClient(url, key);
}

export async function POST() {
  const supabase = supabaseClient();
  if (!supabase) {
    return NextResponse.json({ ok: true, inserted: false, reason: "supabase not configured" });
  }

  const lead = await supabase
    .from("leads")
    .select("id, email")
    .ilike("business_name", "DEMO - %")
    .order("updated_at", { ascending: false, nullsFirst: false })
    .limit(1);
  if (lead.error) {
    return NextResponse.json({ ok: true, inserted: false, reason: lead.error.message });
  }
  const leadRow = lead.data?.[0];
  if (!leadRow?.id) {
    return NextResponse.json({ ok: true, inserted: false, reason: "no demo lead found; run seed_demo_data first" });
  }

  const inbound = await supabase
    .from("inbound")
    .insert({
      lead_id: leadRow.id,
      channel: "email",
      from_address: leadRow.email,
      raw_content: "Demo trigger: interested, could we talk next week?",
    })
    .select("id")
    .limit(1);
  if (inbound.error) {
    return NextResponse.json({ ok: true, inserted: false, reason: inbound.error.message });
  }

  return NextResponse.json({ ok: true, inserted: true, inbound_id: inbound.data?.[0]?.id ?? null });
}
