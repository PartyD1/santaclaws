import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";

export const runtime = "nodejs";

type JsonObject = Record<string, unknown>;

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

function valueAsString(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  if (Array.isArray(value)) {
    return value.map(valueAsString).filter(Boolean).join(", ");
  }
  if (value && typeof value === "object") {
    const record = value as JsonObject;
    return valueAsString(record.email) || valueAsString(record.address) || valueAsString(record.text);
  }
  return "";
}

function emailOnly(value: unknown): string {
  const text = valueAsString(value);
  const match = text.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i);
  return (match?.[0] ?? text).trim().toLowerCase();
}

function textFromPayload(payload: JsonObject) {
  const text = valueAsString(payload.text);
  const html = valueAsString(payload.html);
  const subject = valueAsString(payload.subject);
  const body = text || html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  return [subject ? `Subject: ${subject}` : "", body].filter(Boolean).join("\n\n");
}

async function findLeadId(fromAddress: string) {
  const supabase = supabaseClient();
  if (!supabase || !fromAddress) {
    return null;
  }

  const outreach = await supabase
    .from("outreach")
    .select("lead_id")
    .ilike("to_address", fromAddress)
    .order("drafted_at", { ascending: false })
    .limit(1);
  if (outreach.data?.[0]?.lead_id) {
    return String(outreach.data[0].lead_id);
  }

  const lead = await supabase.from("leads").select("id").ilike("email", fromAddress).limit(1);
  if (lead.data?.[0]?.id) {
    return String(lead.data[0].id);
  }
  return null;
}

export async function POST(request: Request) {
  let payload: JsonObject;
  try {
    payload = (await request.json()) as JsonObject;
  } catch {
    return NextResponse.json({ ok: true, inserted: false, reason: "invalid json" });
  }

  const supabase = supabaseClient();
  if (!supabase) {
    return NextResponse.json({ ok: true, inserted: false, reason: "supabase not configured" });
  }

  const fromAddress = emailOnly(payload.from ?? payload.sender);
  const rawContent = textFromPayload(payload);
  const leadId = await findLeadId(fromAddress);
  const insertPayload: JsonObject = {
    channel: "email",
    from_address: fromAddress || null,
    raw_content: rawContent || JSON.stringify(payload),
  };
  if (leadId) {
    insertPayload.lead_id = leadId;
  }

  const { data, error } = await supabase.from("inbound").insert(insertPayload).select("id").limit(1);
  if (error) {
    return NextResponse.json({ ok: true, inserted: false, reason: error.message });
  }

  return NextResponse.json({ ok: true, inserted: true, inbound_id: data?.[0]?.id ?? null });
}
