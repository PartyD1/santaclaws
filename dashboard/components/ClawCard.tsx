import Link from "next/link";
import type { ClawName } from "@/lib/types";
import type { SantaAgentMeta } from "@/lib/santa-branding";

type ClawCardProps = {
  name: ClawName;
  state: string;
  meta: SantaAgentMeta;
};

const toneClasses: Record<ClawCardProps["meta"]["tone"], string> = {
  emerald: "border-emerald-200 bg-emerald-50 text-emerald-900 ring-emerald-100",
  red: "border-red-200 bg-red-50 text-red-900 ring-red-100",
  gold: "border-amber-200 bg-amber-50 text-amber-950 ring-amber-100",
  frost: "border-sky-200 bg-sky-50 text-sky-900 ring-sky-100",
};

export function ClawCard({ name, state, meta }: ClawCardProps) {
  return (
    <Link href={`/claws/${name}`} className="block rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-red-200 hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-md border text-sm font-black ring-1 ${toneClasses[meta.tone]}`}>
            {meta.icon}
          </span>
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">{meta.role}</p>
            <h2 className="mt-1 text-lg font-semibold tracking-normal text-slate-950">{meta.title}</h2>
          </div>
        </div>
        <span className={`rounded-md border px-2 py-1 text-xs font-semibold ring-1 ${toneClasses[meta.tone]}`}>
          {state}
        </span>
      </div>
      <p className="mt-3 min-h-16 text-sm leading-5 text-slate-600">{meta.focus}</p>
      <div className="mt-4 flex items-center justify-between gap-3 border-t border-slate-100 pt-3 text-xs font-medium text-slate-500">
        <span>{meta.cadence}</span>
        <span>Open workshop</span>
      </div>
    </Link>
  );
}
