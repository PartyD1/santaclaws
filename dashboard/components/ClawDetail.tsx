"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { fetchClawDetail, hasSupabaseConfig, supabaseConfigMessage } from "@/lib/supabase";
import type {
  ActionRow,
  AgentMemoryRow,
  ClawDetailData,
  ClawName,
  GeneratedSiteRow,
  InboundRow,
  LeadRow,
  MeetingRow,
  OutreachRow,
} from "@/lib/types";

type ClawDetailProps = {
  clawName: ClawName;
};

const clawMeta: Record<string, { title: string; cadenceSeconds: number; focus: string; accent: string }> = {
  scout: {
    title: "Scout Claw",
    cadenceSeconds: 60,
    focus: "Finds businesses, scores websites, extracts pain points, and qualifies leads.",
    accent: "bg-teal-500",
  },
  designer: {
    title: "Designer Claw",
    cadenceSeconds: 60,
    focus: "Builds mockup variants, critiques them, picks a winner, and publishes it.",
    accent: "bg-amber-500",
  },
  pitcher: {
    title: "Pitcher Claw",
    cadenceSeconds: 60,
    focus: "Drafts outreach angles, critiques them, and queues the best email.",
    accent: "bg-rose-500",
  },
  closer: {
    title: "Closer Claw",
    cadenceSeconds: 30,
    focus: "Classifies replies, proposes times, drafts responses, and books meetings.",
    accent: "bg-violet-500",
  },
};

const emptyDetail = (clawName: ClawName): ClawDetailData => ({
  clawName,
  actions: [],
  memory: [],
  leads: [],
  generatedSites: [],
  outreach: [],
  inbound: [],
  meetings: [],
  warnings: [],
});

function formatDate(value: string | null) {
  if (!value) {
    return "-";
  }
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function formatAge(value: string | null) {
  if (!value) {
    return "No heartbeat yet";
  }
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) {
    return `${seconds}s ago`;
  }
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  return `${Math.floor(minutes / 60)}h ago`;
}

function statusLabel(value: string | null | undefined) {
  return (value || "unknown").replaceAll("_", " ");
}

function statusClass(status: string) {
  if (status === "Live") {
    return "bg-emerald-50 text-emerald-700";
  }
  if (status === "Attention") {
    return "bg-rose-50 text-rose-700";
  }
  return "bg-amber-50 text-amber-800";
}

function deriveStatus(latest: ActionRow | undefined, cadenceSeconds: number) {
  if (!latest?.started_at) {
    return "Waiting";
  }
  if (latest.status === "failed") {
    return "Attention";
  }
  const ageSeconds = Math.max(0, Math.floor((Date.now() - new Date(latest.started_at).getTime()) / 1000));
  return ageSeconds <= cadenceSeconds * 3 ? "Live" : "Waiting";
}

function EmptyState({ label }: { label: string }) {
  return <div className="rounded-lg border border-dashed border-slate-200 px-4 py-8 text-center text-sm text-slate-500">{label}</div>;
}

function ActionTimeline({ actions }: { actions: ActionRow[] }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
        <h2 className="text-base font-semibold text-slate-950">Live Action Log</h2>
        <span className="text-xs font-medium text-slate-500">{actions.length} rows</span>
      </div>
      <div className="max-h-[620px] overflow-y-auto">
        {actions.map((action) => (
          <article key={action.id} className="border-b border-slate-100 px-4 py-3.5 last:border-b-0">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-semibold uppercase text-slate-500">{action.action_type}</span>
              <time className="text-xs text-slate-400">{formatDate(action.started_at)}</time>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-800">{action.human_readable_log}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600">
                {action.status}
              </span>
              {action.lead_id && (
                <Link className="rounded-md bg-sky-50 px-2 py-1 text-xs font-semibold text-sky-700 hover:underline" href={`/leads/${action.lead_id}`}>
                  lead
                </Link>
              )}
            </div>
          </article>
        ))}
        {actions.length === 0 && <EmptyState label="No actions for this claw yet." />}
      </div>
    </section>
  );
}

function MemoryPanel({ memory, warnings }: { memory: AgentMemoryRow[]; warnings: string[] }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 px-4 py-3">
        <h2 className="text-base font-semibold text-slate-950">Persistent Memory</h2>
      </div>
      <div className="space-y-3 p-4">
        {warnings.map((warning) => (
          <p key={warning} className="rounded-md bg-amber-50 px-3 py-2 text-xs font-medium text-amber-800">
            {warning}
          </p>
        ))}
        {memory.map((entry) => (
          <article key={entry.id} className="rounded-md border border-slate-100 bg-slate-50 p-3">
            <p className="text-sm leading-6 text-slate-800">{entry.pattern}</p>
            <p className="mt-2 text-xs text-slate-500">
              {entry.source} / {formatDate(entry.created_at)}
            </p>
          </article>
        ))}
        {memory.length === 0 && <EmptyState label="No durable memory rows yet." />}
      </div>
    </section>
  );
}

function LeadsPanel({ leads, title }: { leads: LeadRow[]; title: string }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 px-4 py-3">
        <h2 className="text-base font-semibold text-slate-950">{title}</h2>
      </div>
      <div className="divide-y divide-slate-100">
        {leads.map((lead) => (
          <article key={lead.id} className="px-4 py-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Link className="font-medium text-sky-700 hover:underline" href={`/leads/${lead.id}`}>
                {lead.business_name}
              </Link>
              <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">
                {statusLabel(lead.qualification_status)}
              </span>
            </div>
            <p className="mt-1 text-sm text-slate-600">
              Score {lead.website_score ?? "-"} / Designer {lead.worked_by_designer ? "done" : "waiting"} / Pitcher{" "}
              {lead.worked_by_pitcher ? "done" : "waiting"}
            </p>
          </article>
        ))}
        {leads.length === 0 && <EmptyState label="No matching leads yet." />}
      </div>
    </section>
  );
}

function GeneratedSitesPanel({ sites }: { sites: GeneratedSiteRow[] }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 px-4 py-3">
        <h2 className="text-base font-semibold text-slate-950">Generated Mockups</h2>
      </div>
      <div className="divide-y divide-slate-100">
        {sites.map((site) => (
          <article key={site.id} className="px-4 py-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-medium text-slate-950">{statusLabel(site.variant)}</span>
              <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">
                {site.is_chosen_winner ? "winner" : "variant"}
              </span>
            </div>
            <p className="mt-1 text-sm text-slate-600">
              Score {site.self_critique_score ?? "-"} / Iterations {site.self_critique_iterations ?? "-"} /{" "}
              {formatDate(site.generated_at)}
            </p>
            {(site.vercel_url || site.storage_url) && (
              <a className="mt-2 inline-block text-sm font-medium text-sky-700 hover:underline" href={site.vercel_url ?? site.storage_url ?? "#"} target="_blank" rel="noreferrer">
                open mockup
              </a>
            )}
          </article>
        ))}
        {sites.length === 0 && <EmptyState label="No generated mockups yet." />}
      </div>
    </section>
  );
}

function OutreachPanel({ outreach }: { outreach: OutreachRow[] }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 px-4 py-3">
        <h2 className="text-base font-semibold text-slate-950">Outreach Drafts</h2>
      </div>
      <div className="divide-y divide-slate-100">
        {outreach.map((item) => (
          <article key={item.id} className="px-4 py-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-medium text-slate-950">{item.subject}</span>
              <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">
                {statusLabel(item.status)}
              </span>
            </div>
            <p className="mt-1 text-sm text-slate-600">
              {statusLabel(item.angle)} / Score {item.critique_score ?? "-"} / {formatDate(item.drafted_at)}
            </p>
          </article>
        ))}
        {outreach.length === 0 && <EmptyState label="No outreach drafts yet." />}
      </div>
    </section>
  );
}

function CloserPanel({ inbound, meetings }: { inbound: InboundRow[]; meetings: MeetingRow[] }) {
  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-4 py-3">
          <h2 className="text-base font-semibold text-slate-950">Inbound Replies</h2>
        </div>
        <div className="divide-y divide-slate-100">
          {inbound.map((item) => (
            <article key={item.id} className="px-4 py-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium text-slate-950">{item.from_address ?? item.channel}</span>
                <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">
                  {statusLabel(item.classification)}
                </span>
              </div>
              <p className="mt-1 line-clamp-2 text-sm text-slate-600">{item.transcript || item.raw_content}</p>
            </article>
          ))}
          {inbound.length === 0 && <EmptyState label="No inbound replies yet." />}
        </div>
      </section>
      <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-4 py-3">
          <h2 className="text-base font-semibold text-slate-950">Meetings</h2>
        </div>
        <div className="divide-y divide-slate-100">
          {meetings.map((meeting) => (
            <article key={meeting.id} className="px-4 py-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium text-slate-950">{formatDate(meeting.scheduled_for)}</span>
                <span className="rounded-md bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700">
                  {statusLabel(meeting.status)}
                </span>
              </div>
              <p className="mt-1 text-sm text-slate-600">{meeting.attendee_email ?? "No attendee email"}</p>
            </article>
          ))}
          {meetings.length === 0 && <EmptyState label="No meetings booked yet." />}
        </div>
      </section>
    </div>
  );
}

function WorkPanel({ detail }: { detail: ClawDetailData }) {
  if (detail.clawName === "designer") {
    return (
      <div className="grid gap-5 xl:grid-cols-2">
        <LeadsPanel leads={detail.leads} title="Designer Queue" />
        <GeneratedSitesPanel sites={detail.generatedSites} />
      </div>
    );
  }
  if (detail.clawName === "pitcher") {
    return (
      <div className="grid gap-5 xl:grid-cols-2">
        <LeadsPanel leads={detail.leads} title="Pitcher Queue" />
        <OutreachPanel outreach={detail.outreach} />
      </div>
    );
  }
  if (detail.clawName === "closer") {
    return <CloserPanel inbound={detail.inbound} meetings={detail.meetings} />;
  }
  return <LeadsPanel leads={detail.leads} title="Recently Qualified Leads" />;
}

export function ClawDetail({ clawName }: ClawDetailProps) {
  const [detail, setDetail] = useState<ClawDetailData>(() => emptyDetail(clawName));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadDetail() {
      try {
        const nextDetail = await fetchClawDetail(clawName);
        if (!cancelled) {
          setDetail(nextDetail);
          setError(null);
        }
      } catch (exc) {
        if (!cancelled) {
          setError(exc instanceof Error ? exc.message : "Could not load claw detail.");
        }
      }
    }

    void loadDetail();
    const interval = window.setInterval(loadDetail, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [clawName]);

  const meta = clawMeta[String(clawName)] ?? {
    title: `${String(clawName)} Claw`,
    cadenceSeconds: 60,
    focus: "NemoClaw runtime worker.",
    accent: "bg-slate-500",
  };
  const latest = detail.actions[0];
  const status = useMemo(() => deriveStatus(latest, meta.cadenceSeconds), [latest, meta.cadenceSeconds]);

  if (!hasSupabaseConfig()) {
    return <EmptyState label={supabaseConfigMessage() ?? "Live Supabase credentials are not configured yet."} />;
  }

  if (error) {
    return <EmptyState label={error} />;
  }

  return (
    <div className="space-y-5">
      <header className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <Link className="text-sm font-medium text-sky-700 hover:underline" href="/">
          Back to dashboard
        </Link>
        <div className="mt-4 flex flex-col justify-between gap-4 md:flex-row md:items-start">
          <div>
            <div className="flex items-center gap-2">
              <span className={`h-3 w-3 rounded-full ${meta.accent}`} />
              <p className="text-xs font-semibold uppercase text-slate-500">{clawName}</p>
            </div>
            <h1 className="mt-1 text-3xl font-semibold tracking-normal text-slate-950">{meta.title}</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">{meta.focus}</p>
          </div>
          <span className={`rounded-md px-3 py-2 text-sm font-semibold ${statusClass(status)}`}>{status}</span>
        </div>
        <div className="mt-5 grid gap-4 md:grid-cols-4">
          <div>
            <p className="text-xs text-slate-500">Last Heartbeat</p>
            <p className="mt-1 text-lg font-semibold text-slate-950">{formatAge(latest?.started_at ?? null)}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Cadence</p>
            <p className="mt-1 text-lg font-semibold text-slate-950">{meta.cadenceSeconds}s</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Recent Actions</p>
            <p className="mt-1 text-lg font-semibold text-slate-950">{detail.actions.length}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Memory Rows</p>
            <p className="mt-1 text-lg font-semibold text-slate-950">{detail.memory.length}</p>
          </div>
        </div>
        {latest && <p className="mt-4 text-sm leading-6 text-slate-700">{latest.human_readable_log}</p>}
      </header>

      <WorkPanel detail={detail} />

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_430px]">
        <ActionTimeline actions={detail.actions} />
        <MemoryPanel memory={detail.memory} warnings={detail.warnings} />
      </section>
    </div>
  );
}
