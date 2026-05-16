import type { ClawName } from "@/lib/types";

type ClawCardProps = {
  name: ClawName;
  title: string;
  focus: string;
  state: string;
  cadence: string;
  tone: "teal" | "amber" | "rose" | "violet";
};

const toneClasses: Record<ClawCardProps["tone"], string> = {
  teal: "border-teal-200 bg-teal-50 text-teal-900 ring-teal-100",
  amber: "border-amber-200 bg-amber-50 text-amber-950 ring-amber-100",
  rose: "border-rose-200 bg-rose-50 text-rose-950 ring-rose-100",
  violet: "border-violet-200 bg-violet-50 text-violet-950 ring-violet-100",
};

export function ClawCard({ name, title, focus, state, cadence, tone }: ClawCardProps) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">{name}</p>
          <h2 className="mt-1 text-lg font-semibold tracking-normal text-slate-950">{title}</h2>
        </div>
        <span className={`rounded-md border px-2 py-1 text-xs font-semibold ring-1 ${toneClasses[tone]}`}>
          {state}
        </span>
      </div>
      <p className="mt-3 min-h-16 text-sm leading-5 text-slate-600">{focus}</p>
      <div className="mt-4 flex items-center justify-between gap-3 border-t border-slate-100 pt-3 text-xs font-medium text-slate-500">
        <span>{cadence}</span>
        <span>MEMORY.md</span>
      </div>
    </section>
  );
}
