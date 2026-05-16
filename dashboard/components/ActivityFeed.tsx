"use client";

import { useEffect, useState } from "react";
import { mergeActions, subscribeToActions, unsubscribeFromActions } from "@/lib/realtime";
import { fetchRecentActions } from "@/lib/supabase";
import type { ActionRow, ClawName } from "@/lib/types";

const clawDotClasses: Record<string, string> = {
  scout: "bg-teal-500",
  designer: "bg-amber-500",
  pitcher: "bg-rose-500",
  closer: "bg-violet-500",
};

const statusClasses: Record<string, string> = {
  succeeded: "bg-emerald-50 text-emerald-700",
  failed: "bg-rose-50 text-rose-700",
  skipped: "bg-slate-100 text-slate-600",
  started: "bg-sky-50 text-sky-700",
};

function formatTime(value: string | null) {
  if (!value) {
    return "-";
  }
  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function dotClass(claw: ClawName) {
  return clawDotClasses[String(claw).toLowerCase()] ?? "bg-slate-400";
}

function statusClass(status: string) {
  return statusClasses[status.toLowerCase()] ?? "bg-slate-100 text-slate-600";
}

export function ActivityFeed() {
  const [actions, setActions] = useState<ActionRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadActions() {
      try {
        const rows = await fetchRecentActions();
        if (!cancelled) {
          setActions((current) => mergeActions(current, rows));
          setError(null);
        }
      } catch (exc) {
        if (!cancelled) {
          setError(exc instanceof Error ? exc.message : "Could not load activity.");
        }
      }
    }

    void loadActions();
    const channel = subscribeToActions((action) => {
      setActions((current) => mergeActions(current, [action]));
    });
    const interval = window.setInterval(loadActions, 5000);

    return () => {
      cancelled = true;
      unsubscribeFromActions(channel);
      window.clearInterval(interval);
    };
  }, []);

  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
        <h2 className="text-base font-semibold tracking-normal text-slate-950">Live Activity</h2>
        <span className="text-xs font-medium text-slate-500">{actions.length} rows</span>
      </div>
      <div className="max-h-[560px] overflow-y-auto">
        {actions.map((action) => (
          <article key={action.id} className="border-b border-slate-100 px-4 py-3.5 last:border-b-0">
            <div className="flex items-center justify-between gap-4">
              <div className="flex min-w-0 items-center gap-2">
                <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${dotClass(action.claw_name)}`} />
                <span className="truncate text-xs font-semibold uppercase tracking-normal text-slate-500">
                  {action.claw_name}
                </span>
              </div>
              <time className="shrink-0 text-xs text-slate-400">{formatTime(action.started_at)}</time>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-800">{action.human_readable_log}</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600">
                {action.action_type}
              </span>
              <span className={`rounded-md px-2 py-1 text-xs font-semibold ${statusClass(action.status)}`}>
                {action.status}
              </span>
            </div>
          </article>
        ))}
        {actions.length === 0 && (
          <div className="px-4 py-10 text-center text-sm text-slate-500">
            {error ?? "No actions yet."}
          </div>
        )}
      </div>
    </section>
  );
}
