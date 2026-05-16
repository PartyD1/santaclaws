import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import type {
  ActionRow,
  AgentMemoryRow,
  ClawDetailData,
  ClawName,
  DashboardMetrics,
  Database,
  GeneratedSiteRow,
  InboundRow,
  LeadDetailData,
  LeadRow,
  MeetingRow,
  OutreachRow,
} from "./types";

let browserClient: SupabaseClient<Database> | null = null;

function supabaseBrowserKey() {
  return (
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ||
    ""
  );
}

export function hasSupabaseConfig() {
  return Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL && supabaseBrowserKey());
}

export function supabaseConfigMessage() {
  if (hasSupabaseConfig()) {
    return null;
  }
  const missing = [];
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL) {
    missing.push("NEXT_PUBLIC_SUPABASE_URL");
  }
  if (!supabaseBrowserKey()) {
    missing.push("NEXT_PUBLIC_SUPABASE_ANON_KEY or NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY");
  }
  return `Live Supabase credentials are not configured yet. Missing: ${missing.join(", ")}.`;
}

export function getSupabaseClient() {
  if (!hasSupabaseConfig()) {
    return null;
  }

  if (!browserClient) {
    browserClient = createClient<Database>(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      supabaseBrowserKey(),
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

export async function fetchClawDetail(clawName: ClawName): Promise<ClawDetailData> {
  const empty: ClawDetailData = {
    clawName,
    actions: [],
    memory: [],
    leads: [],
    generatedSites: [],
    outreach: [],
    inbound: [],
    meetings: [],
    warnings: [],
  };
  const supabase = getSupabaseClient();
  if (!supabase) {
    return empty;
  }

  const warnings: string[] = [];
  const [actions, memory] = await Promise.all([
    supabase.from("actions").select("*").eq("claw_name", clawName).order("started_at", { ascending: false }).limit(100),
    supabase
      .from("agent_memory")
      .select("*")
      .eq("claw_name", clawName)
      .order("created_at", { ascending: false })
      .limit(30),
  ]);

  if (actions.error) {
    throw new Error(`Could not load ${clawName} actions: ${actions.error.message}`);
  }
  if (memory.error) {
    warnings.push(`Memory table unavailable: ${memory.error.message}`);
  }

  const data: ClawDetailData = {
    ...empty,
    actions: actions.data ?? [],
    memory: (memory.data ?? []) as AgentMemoryRow[],
    warnings,
  };

  if (clawName === "scout") {
    const leads = await supabase
      .from("leads")
      .select("*")
      .order("updated_at", { ascending: false, nullsFirst: false })
      .limit(25);
    if (leads.error) {
      warnings.push(`Could not load Scout leads: ${leads.error.message}`);
    } else {
      data.leads = leads.data ?? [];
    }
  } else if (clawName === "designer") {
    const [leads, generatedSites] = await Promise.all([
      supabase
        .from("leads")
        .select("*")
        .in("qualification_status", ["qualified_for_mockup", "qualified_for_rebuild"])
        .order("updated_at", { ascending: false, nullsFirst: false })
        .limit(20),
      supabase.from("generated_sites").select("*").order("generated_at", { ascending: false }).limit(25),
    ]);
    if (leads.error) {
      warnings.push(`Could not load Designer queue: ${leads.error.message}`);
    } else {
      data.leads = leads.data ?? [];
    }
    if (generatedSites.error) {
      warnings.push(`Could not load generated sites: ${generatedSites.error.message}`);
    } else {
      data.generatedSites = (generatedSites.data ?? []) as GeneratedSiteRow[];
    }
  } else if (clawName === "pitcher") {
    const [leads, outreach] = await Promise.all([
      supabase
        .from("leads")
        .select("*")
        .eq("worked_by_designer", true)
        .order("updated_at", { ascending: false, nullsFirst: false })
        .limit(20),
      supabase.from("outreach").select("*").order("drafted_at", { ascending: false }).limit(25),
    ]);
    if (leads.error) {
      warnings.push(`Could not load Pitcher queue: ${leads.error.message}`);
    } else {
      data.leads = leads.data ?? [];
    }
    if (outreach.error) {
      warnings.push(`Could not load outreach: ${outreach.error.message}`);
    } else {
      data.outreach = (outreach.data ?? []) as OutreachRow[];
    }
  } else if (clawName === "closer") {
    const [inbound, meetings] = await Promise.all([
      supabase.from("inbound").select("*").order("received_at", { ascending: false }).limit(25),
      supabase.from("meetings").select("*").order("booked_at", { ascending: false, nullsFirst: false }).limit(25),
    ]);
    if (inbound.error) {
      warnings.push(`Could not load inbound replies: ${inbound.error.message}`);
    } else {
      data.inbound = (inbound.data ?? []) as InboundRow[];
    }
    if (meetings.error) {
      warnings.push(`Could not load meetings: ${meetings.error.message}`);
    } else {
      data.meetings = (meetings.data ?? []) as MeetingRow[];
    }
  }

  return data;
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
