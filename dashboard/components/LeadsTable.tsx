"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchRecentLeads } from "@/lib/supabase";
import type { LeadRow } from "@/lib/types";

function formatScore(score: number | null) {
  return typeof score === "number" ? `${score}/10` : "-";
}

function formatStatus(status: string) {
  return status.replaceAll("_", " ");
}

export function LeadsTable() {
  const [leads, setLeads] = useState<LeadRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadLeads() {
      try {
        const rows = await fetchRecentLeads();
        if (!cancelled) {
          setLeads(rows);
          setError(null);
        }
      } catch (exc) {
        if (!cancelled) {
          setError(exc instanceof Error ? exc.message : "Could not load leads.");
        }
      }
    }

    void loadLeads();
    const interval = window.setInterval(loadLeads, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  return (
    <section className="rounded-lg border border-red-100 bg-white shadow-sm">
      <div className="border-b border-red-100 px-4 py-3">
        <h2 className="text-base font-semibold tracking-normal text-slate-950">Nice List Leads</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
            <tr>
              <th className="px-4 py-3 font-semibold">Business</th>
              <th className="px-4 py-3 font-semibold">City</th>
              <th className="px-4 py-3 font-semibold">Website</th>
              <th className="px-4 py-3 font-semibold">Score</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Workshop</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {leads.map((lead) => (
              <tr key={lead.id} className="bg-white">
                <td className="px-4 py-3">
                  <Link className="font-medium text-sky-700 underline-offset-2 hover:underline" href={`/leads/${lead.id}`}>
                    {lead.business_name}
                  </Link>
                  <div className="mt-1 max-w-72 truncate text-xs text-slate-500">{lead.address ?? "No address"}</div>
                </td>
                <td className="px-4 py-3 text-slate-700">{lead.city}</td>
                <td className="px-4 py-3 text-slate-700">
                  {lead.website ? (
                    <a
                      className="font-medium text-sky-700 underline-offset-2 hover:underline"
                      href={lead.website}
                      target="_blank"
                      rel="noreferrer"
                    >
                      open
                    </a>
                  ) : (
                    "missing"
                  )}
                </td>
                <td className="px-4 py-3 text-slate-700">{formatScore(lead.website_score)}</td>
                <td className="px-4 py-3">
                  <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">
                    {formatStatus(lead.qualification_status)}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-700">
                  <span>{lead.worked_by_designer ? "Elves done" : "Elves waiting"}</span>
                  <span className="mx-2 text-slate-300">/</span>
                  <span>{lead.worked_by_pitcher ? "Pitcher done" : "Pitcher waiting"}</span>
                </td>
              </tr>
            ))}
            {leads.length === 0 && (
              <tr>
                <td className="px-4 py-10 text-center text-sm text-slate-500" colSpan={6}>
                  {error ?? "No shops on the nice list yet."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
