"use client";

import { useEffect, useRef, useState } from "react";
import { fetchMetrics, hasSupabaseConfig } from "@/lib/supabase";
import type { DashboardMetrics } from "@/lib/types";

const emptyMetrics: DashboardMetrics = {
  totalLeads: 0,
  qualifiedLeads: 0,
  sitesGenerated: 0,
  emailsDrafted: 0,
  outreachSent: 0,
  repliesReceived: 0,
  meetingsBooked: 0,
};

const metricLabels: Array<[keyof DashboardMetrics, string]> = [
  ["totalLeads", "Leads"],
  ["qualifiedLeads", "Qualified"],
  ["sitesGenerated", "Mockups"],
  ["emailsDrafted", "Drafts"],
  ["outreachSent", "Emails sent"],
  ["repliesReceived", "Replies"],
  ["meetingsBooked", "Meetings"],
];

export function MetricsBar() {
  const [metrics, setMetrics] = useState<DashboardMetrics>(emptyMetrics);
  const previousMeetings = useRef(0);
  const [pulseMeetings, setPulseMeetings] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadMetrics() {
      try {
        const nextMetrics = await fetchMetrics();
        if (!cancelled) {
          if (nextMetrics.meetingsBooked > previousMeetings.current) {
            setPulseMeetings(true);
            window.setTimeout(() => setPulseMeetings(false), 1200);
          }
          previousMeetings.current = nextMetrics.meetingsBooked;
          setMetrics(nextMetrics);
          setError(null);
        }
      } catch (exc) {
        if (!cancelled) {
          setError(exc instanceof Error ? exc.message : "Could not load metrics.");
        }
      }
    }

    void loadMetrics();
    const interval = window.setInterval(loadMetrics, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="grid gap-3 sm:grid-cols-4 lg:grid-cols-7">
        {metricLabels.map(([key, label]) => (
          <div
            key={key}
            className={`min-w-0 rounded-md p-2 ${key === "meetingsBooked" && pulseMeetings ? "animate-pulse bg-emerald-50" : ""}`}
          >
            <p className="text-xs font-medium text-slate-500">{label}</p>
            <p className="mt-1 text-2xl font-semibold tracking-normal text-slate-950">{metrics[key]}</p>
          </div>
        ))}
      </div>
      {(error || !hasSupabaseConfig()) && (
        <p className="mt-3 text-xs text-slate-500">
          {error ?? "Live Supabase credentials are not configured yet."}
        </p>
      )}
    </section>
  );
}
