import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import type { ActionRow, DashboardMetrics, Database, LeadRow } from "./types";

let browserClient: SupabaseClient<Database> | null = null;

export function hasSupabaseConfig() {
  return Boolean(
    process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  );
}

export function getSupabaseClient() {
  if (!hasSupabaseConfig()) {
    return null;
  }

  if (!browserClient) {
    browserClient = createClient<Database>(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    );
  }

  return browserClient;
}

export async function fetchRecentActions(limit = 50): Promise<ActionRow[]> {
  const supabase = getSupabaseClient();
  if (!supabase) {
    return [];
  }

  const { data, error } = await supabase
    .from("actions")
    .select("*")
    .order("started_at", { ascending: false })
    .limit(limit);

  if (error) {
    throw new Error(`Could not load actions: ${error.message}`);
  }

  return data ?? [];
}

export async function fetchRecentLeads(limit = 25): Promise<LeadRow[]> {
  const supabase = getSupabaseClient();
  if (!supabase) {
    return [];
  }

  const { data, error } = await supabase
    .from("leads")
    .select("*")
    .order("updated_at", { ascending: false, nullsFirst: false })
    .limit(limit);

  if (error) {
    throw new Error(`Could not load leads: ${error.message}`);
  }

  return data ?? [];
}

async function countRows(
  table: "leads" | "generated_sites" | "outreach" | "inbound" | "meetings",
  filter?: (query: ReturnType<NonNullable<ReturnType<typeof getSupabaseClient>>["from"]>) => unknown,
) {
  const supabase = getSupabaseClient();
  if (!supabase) {
    return 0;
  }

  let query = supabase.from(table).select("id", { count: "exact", head: true });
  if (filter) {
    query = filter(query) as typeof query;
  }
  const { count, error } = await query;
  if (error) {
    throw new Error(`Could not count ${table}: ${error.message}`);
  }
  return count ?? 0;
}

export async function fetchMetrics(): Promise<DashboardMetrics> {
  if (!hasSupabaseConfig()) {
    return {
      totalLeads: 0,
      qualifiedLeads: 0,
      sitesGenerated: 0,
      outreachSent: 0,
      repliesReceived: 0,
      meetingsBooked: 0,
    };
  }

  const [totalLeads, qualifiedLeads, sitesGenerated, outreachSent, repliesReceived, meetingsBooked] =
    await Promise.all([
      countRows("leads"),
      countRows("leads", (query) => query.not("qualification_status", "in", "(pending,skip)")),
      countRows("generated_sites"),
      countRows("outreach", (query) => query.eq("status", "sent")),
      countRows("inbound"),
      countRows("meetings"),
    ]);

  return {
    totalLeads,
    qualifiedLeads,
    sitesGenerated,
    outreachSent,
    repliesReceived,
    meetingsBooked,
  };
}
