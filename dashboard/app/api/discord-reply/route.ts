import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";

export const runtime = "nodejs";

type JsonObject = Record<string, unknown>;

const COMMAND_RE = /^\s*(APPROVE|SKIP|EDIT)\s+([0-9a-fA-F-]{32,36})(?:\s+([\s\S]+))?\s*$/i;

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
  if (value && typeof value === "object") {
    const record = value as JsonObject;
    return valueAsString(record.content) || valueAsString(record.text) || valueAsString(record.body);
  }
  return "";
}

function parseCommand(payload: JsonObject) {
  const content = valueAsString(payload.content ?? payload.text ?? payload.message);
  const match = content.match(COMMAND_RE);
  if (!match) {
    return null;
  }
  const decision = match[1].toLowerCase();
  const outreachId = match[2];
  const newBody = (match[3] ?? "").trim();
  if (decision === "edit" && !newBody) {
    throw new Error("EDIT requires a new body after the outreach id.");
  }
  return { decision, outreachId, newBody };
}

export async function POST(request: Request) {
  let payload: JsonObject;
  try {
    payload = (await request.json()) as JsonObject;
  } catch {
    return NextResponse.json({ ok: true, applied: false, reason: "invalid json" });
  }

  let command;
  try {
    command = parseCommand(payload);
  } catch (exc) {
    return NextResponse.json({
      ok: true,
      applied: false,
      reason: exc instanceof Error ? exc.message : "invalid approval command",
    });
  }
  if (!command) {
    return NextResponse.json({ ok: true, applied: false, reason: "no approval command" });
  }

  const supabase = supabaseClient();
  if (!supabase) {
    return NextResponse.json({ ok: true, applied: false, reason: "supabase not configured" });
  }

  const updatePayload: JsonObject =
    command.decision === "skip"
      ? { status: "skipped" }
      : { status: "approved", approved_at: new Date().toISOString() };
  if (command.decision === "edit") {
    updatePayload.body = command.newBody;
  }

  const update = await supabase.from("outreach").update(updatePayload).eq("id", command.outreachId).select("id").limit(1);
  if (update.error) {
    return NextResponse.json({ ok: true, applied: false, reason: update.error.message });
  }
  if (!update.data?.[0]) {
    return NextResponse.json({ ok: true, applied: false, reason: "outreach row not found" });
  }

  await supabase.from("approvals").insert({
    target_type: "outreach",
    target_id: command.outreachId,
    decision: command.decision,
    edit_payload: command.decision === "edit" ? { body: command.newBody } : null,
    decided_at: new Date().toISOString(),
    decided_by: valueAsString(payload.author ?? payload.user) || "discord-webhook",
  });

  return NextResponse.json({ ok: true, applied: true, outreach_id: command.outreachId, decision: command.decision });
}
