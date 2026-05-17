import { ActivityFeed } from "@/components/ActivityFeed";
import { ClawCard } from "@/components/ClawCard";
import { LeadsTable } from "@/components/LeadsTable";
import { MetricsBar } from "@/components/MetricsBar";
import { santaAgent, santaClawsBrand } from "@/lib/santa-branding";

const claws = [
  {
    name: "scout",
    state: "Active",
  },
  {
    name: "designer",
    state: "Active",
  },
  {
    name: "pitcher",
    state: "Active",
  },
  {
    name: "closer",
    state: "Active",
  },
] as const;

export default function Page() {
  return (
    <main className="min-h-screen px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="overflow-hidden rounded-lg border border-red-100 bg-white shadow-sm">
          <div className="p-6 sm:p-7">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-xs font-semibold uppercase tracking-normal text-red-700">{santaClawsBrand.eyebrow}</p>
              <span className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-800">
                Live Supabase feed
              </span>
            </div>
            <h1 className="mt-2 text-4xl font-semibold tracking-normal text-slate-950 sm:text-5xl">
              {santaClawsBrand.product}
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-600">
              {santaClawsBrand.tagline}
            </p>
            <div className="mt-6 grid gap-3 text-sm sm:grid-cols-3">
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                <p className="font-semibold text-slate-950">Shared memory</p>
                <p className="mt-1 text-xs leading-5 text-slate-500">Supabase queues, logs, and agent memory.</p>
              </div>
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                <p className="font-semibold text-slate-950">Demo control</p>
                <p className="mt-1 text-xs leading-5 text-slate-500">Run claws from Discord or terminal.</p>
              </div>
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                <p className="font-semibold text-slate-950">Live outputs</p>
                <p className="mt-1 text-xs leading-5 text-slate-500">Leads, Vercel sites, pitches, and replies.</p>
              </div>
            </div>
          </div>
        </header>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {claws.map((claw) => (
            <ClawCard key={claw.name} name={claw.name} state={claw.state} meta={santaAgent(claw.name)} />
          ))}
        </section>

        <MetricsBar />

        <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_430px]">
          <LeadsTable />
          <ActivityFeed />
        </section>
      </div>
    </main>
  );
}
