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
      <div className="border-b border-slate-200 px-4 py-3">
        <h2 className="text-base font-semibold tracking-normal text-slate-950">Live Activity</h2>
      </div>
      <div className="max-h-[560px] overflow-y-auto">
        {actions.map((action) => (
          <article key={action.id} className="border-b border-slate-100 px-4 py-3 last:border-b-0">
            <div className="flex items-center justify-between gap-4">
              <div className="flex min-w-0 items-center gap-2">
                <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${dotClass(action.claw_name)}`} />
                <span className="truncate text-xs font-semibold uppercase tracking-normal text-slate-500">
                  {action.claw_name}
                </span>
              </div>
              <time className="shrink-0 text-xs text-slate-400">{formatTime(action.started_at)}</time>
            </div>
            <p className="mt-2 text-sm leading-5 text-slate-800">{action.human_readable_log}</p>
            <p className="mt-1 text-xs text-slate-500">
              {action.action_type} / {action.status}
            </p>
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
