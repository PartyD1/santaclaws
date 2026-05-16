"use client";

import { useEffect, useState } from "react";
import { fetchLeadDetail, hasSupabaseConfig, supabaseConfigMessage } from "@/lib/supabase";
import type { ActionRow, InboundRow, LeadDetailData, MeetingRow, OutreachRow } from "@/lib/types";
import { MockupPreview } from "./MockupPreview";

type LeadDetailProps = {
  leadId: string;
};

const emptyDetail: LeadDetailData = {
  lead: null,
  generatedSites: [],
  outreach: [],
  inbound: [],
  meetings: [],
  actions: [],
};

function formatDate(value: string | null) {
  if (!value) {
    return "-";
  }
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function statusLabel(value: string | null | undefined) {
  return (value || "unknown").replaceAll("_", " ");
}

function EmptyRow({ label }: { label: string }) {
  return <div className="rounded-lg border border-dashed border-slate-200 px-4 py-8 text-center text-sm text-slate-500">{label}</div>;
}

function OutreachCard({ item }: { item: OutreachRow }) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-950">{item.subject}</h3>
        <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">{statusLabel(item.status)}</span>
      </div>
      <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{item.body}</p>
      <p className="mt-3 text-xs text-slate-500">
        {item.angle.replaceAll("_", " ")} / Score {item.critique_score ?? "-"} / {formatDate(item.drafted_at)}
      </p>
    </article>
  );
}

function InboundCard({ item }: { item: InboundRow }) {
  const body = item.channel === "voice" ? item.transcript || item.raw_content : item.raw_content;
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-slate-950">{item.from_address ?? "Unknown sender"}</h3>
          <p className="mt-1 text-xs font-medium uppercase text-slate-500">{item.channel}</p>
        </div>
        <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">
          {statusLabel(item.classification)}
        </span>
      </div>
      <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{body}</p>
      <p className="mt-3 text-xs text-slate-500">
        Confidence {item.classification_confidence ?? "-"} / {item.classification_key_phrase ?? "No key phrase"} /{" "}
        {formatDate(item.received_at)}
      </p>
    </article>
  );
}

function MeetingCard({ item }: { item: MeetingRow }) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-950">{formatDate(item.scheduled_for)}</h3>
        <span className="rounded-md bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700">{statusLabel(item.status)}</span>
      </div>
      <p className="mt-2 text-sm text-slate-700">{item.attendee_email ?? "No attendee email"}</p>
      <p className="mt-3 text-xs text-slate-500">{item.google_event_id ?? "No calendar event id"}</p>
    </article>
  );
}

function ActionItem({ action }: { action: ActionRow }) {
  return (
    <li className="border-b border-slate-100 py-3 last:border-b-0">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase text-slate-500">{action.claw_name}</span>
        <time className="text-xs text-slate-400">{formatDate(action.started_at)}</time>
      </div>
      <p className="mt-1 text-sm text-slate-800">{action.human_readable_log}</p>
      <p className="mt-1 text-xs text-slate-500">
        {action.action_type} / {action.status}
      </p>
    </li>
  );
}

export function LeadDetail({ leadId }: LeadDetailProps) {
  const [detail, setDetail] = useState<LeadDetailData>(emptyDetail);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadDetail() {
      try {
        const nextDetail = await fetchLeadDetail(leadId);
        if (!cancelled) {
          setDetail(nextDetail);
          setError(null);
        }
      } catch (exc) {
        if (!cancelled) {
          setError(exc instanceof Error ? exc.message : "Could not load lead detail.");
        }
      }
    }

    void loadDetail();
    const interval = window.setInterval(loadDetail, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [leadId]);

  const { lead } = detail;

  if (!hasSupabaseConfig()) {
    return <EmptyRow label={supabaseConfigMessage() ?? "Live Supabase credentials are not configured yet."} />;
  }

  if (error) {
    return <EmptyRow label={error} />;
  }

  if (!lead) {
    return <EmptyRow label="Lead not found yet." />;
  }

  return (
    <div className="space-y-5">
      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
          <div>
            <p className="text-xs font-semibold uppercase text-slate-500">NemoClaw Lead</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-normal text-slate-950">{lead.business_name}</h1>
            <p className="mt-2 text-sm text-slate-600">{lead.address ?? "No address"} / {lead.city}</p>
          </div>
          <span className="rounded-md bg-slate-100 px-3 py-2 text-sm font-medium text-slate-700">
            {statusLabel(lead.qualification_status)}
          </span>
        </div>
        <div className="mt-5 grid gap-4 md:grid-cols-4">
          <div>
            <p className="text-xs text-slate-500">Website Score</p>
            <p className="mt-1 text-xl font-semibold text-slate-950">{lead.website_score ?? "-"}/10</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Google Rating</p>
            <p className="mt-1 text-xl font-semibold text-slate-950">{lead.google_rating ?? "-"}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Email</p>
            <p className="mt-1 truncate text-sm font-medium text-slate-800">{lead.email ?? "Missing"}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Website</p>
            {lead.website ? (
              <a className="mt-1 block truncate text-sm font-medium text-sky-700 hover:underline" href={lead.website} target="_blank" rel="noreferrer">
                {lead.website}
              </a>
            ) : (
              <p className="mt-1 text-sm font-medium text-slate-800">Missing</p>
            )}
          </div>
        </div>
        <p className="mt-4 text-sm leading-6 text-slate-700">{lead.qualification_reason ?? "No qualification reason yet."}</p>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold text-slate-950">Generated Mockups</h2>
        <div className="grid gap-4 lg:grid-cols-2">
          {detail.generatedSites.map((site) => <MockupPreview key={site.id} site={site} />)}
          {detail.generatedSites.length === 0 && <EmptyRow label="No generated mockups yet." />}
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-2">
        <div>
          <h2 className="mb-3 text-lg font-semibold text-slate-950">Outreach</h2>
          <div className="space-y-3">
            {detail.outreach.map((item) => <OutreachCard key={item.id} item={item} />)}
            {detail.outreach.length === 0 && <EmptyRow label="No outreach drafts yet." />}
          </div>
        </div>
        <div>
          <h2 className="mb-3 text-lg font-semibold text-slate-950">Inbound Replies</h2>
          <div className="space-y-3">
            {detail.inbound.map((item) => <InboundCard key={item.id} item={item} />)}
            {detail.inbound.length === 0 && <EmptyRow label="No inbound replies yet." />}
          </div>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-2">
        <div>
          <h2 className="mb-3 text-lg font-semibold text-slate-950">Booked Meetings</h2>
          <div className="space-y-3">
            {detail.meetings.map((item) => <MeetingCard key={item.id} item={item} />)}
            {detail.meetings.length === 0 && <EmptyRow label="No booked meetings yet." />}
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-950">Action Timeline</h2>
          <ul className="mt-2">
            {detail.actions.map((action) => <ActionItem key={action.id} action={action} />)}
            {detail.actions.length === 0 && <li className="py-8 text-center text-sm text-slate-500">No actions yet.</li>}
          </ul>
        </div>
      </section>
    </div>
  );
}
