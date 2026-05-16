import type { RealtimeChannel } from "@supabase/supabase-js";
import { getSupabaseClient } from "./supabase";
import type { ActionRow } from "./types";

export function mergeActions(current: ActionRow[], incoming: ActionRow[], limit = 50) {
  const byId = new Map<string, ActionRow>();
  for (const action of [...incoming, ...current]) {
    byId.set(action.id, action);
  }

  return Array.from(byId.values())
    .sort((a, b) => {
      const aTime = a.started_at ? new Date(a.started_at).getTime() : 0;
      const bTime = b.started_at ? new Date(b.started_at).getTime() : 0;
      return bTime - aTime;
    })
    .slice(0, limit);
}

export function subscribeToActions(onInsert: (action: ActionRow) => void) {
  const supabase = getSupabaseClient();
  if (!supabase) {
    return null;
  }

  const channel = supabase
    .channel("actions-feed")
    .on(
      "postgres_changes",
      { event: "INSERT", schema: "public", table: "actions" },
      (payload) => onInsert(payload.new as ActionRow),
    )
    .subscribe();

  return channel;
}

export function unsubscribeFromActions(channel: RealtimeChannel | null) {
  const supabase = getSupabaseClient();
  if (!supabase || !channel) {
    return;
  }
  void supabase.removeChannel(channel);
}
