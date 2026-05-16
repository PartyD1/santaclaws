import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import type { ActionRow, DashboardMetrics, Database, LeadDetailData, LeadRow } from "./types";

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
      emailsDrafted: 0,
      outreachSent: 0,
      repliesReceived: 0,
      meetingsBooked: 0,
    };
  }

  const [
    totalLeads,
    qualifiedLeads,
    sitesGenerated,
    emailsDrafted,
    outreachSent,
    repliesReceived,
    meetingsBooked,
  ] =
    await Promise.all([
      countRows("leads"),
      countRows("leads", (query) => query.not("qualification_status", "in", "(pending,skip)")),
      countRows("generated_sites"),
      countRows("outreach"),
      countRows("outreach", (query) => query.eq("status", "sent")),
      countRows("inbound"),
      countRows("meetings"),
    ]);

  return {
    totalLeads,
    qualifiedLeads,
    sitesGenerated,
    emailsDrafted,
    outreachSent,
    repliesReceived,
    meetingsBooked,
  };
}

export async function fetchLeadDetail(leadId: string): Promise<LeadDetailData> {
  const empty: LeadDetailData = {
    lead: null,
    generatedSites: [],
    outreach: [],
    inbound: [],
    meetings: [],
    actions: [],
  };
  const supabase = getSupabaseClient();
  if (!supabase) {
    return empty;
  }

  const [lead, generatedSites, outreach, inbound, meetings, actions] = await Promise.all([
    supabase.from("leads").select("*").eq("id", leadId).limit(1),
    supabase.from("generated_sites").select("*").eq("lead_id", leadId).order("generated_at", { ascending: false }),
    supabase.from("outreach").select("*").eq("lead_id", leadId).order("drafted_at", { ascending: false }),
    supabase.from("inbound").select("*").eq("lead_id", leadId).order("received_at", { ascending: false }),
    supabase.from("meetings").select("*").eq("lead_id", leadId).order("scheduled_for", { ascending: false }),
    supabase.from("actions").select("*").eq("lead_id", leadId).order("started_at", { ascending: false }).limit(100),
  ]);

  const errors = [lead.error, generatedSites.error, outreach.error, inbound.error, meetings.error, actions.error].filter(
    Boolean,
  );
  if (errors.length > 0) {
    throw new Error(`Could not load lead detail: ${errors[0]?.message}`);
  }

  return {
    lead: lead.data?.[0] ?? null,
    generatedSites: generatedSites.data ?? [],
    outreach: outreach.data ?? [],
    inbound: inbound.data ?? [],
    meetings: meetings.data ?? [],
    actions: actions.data ?? [],
  };
}
