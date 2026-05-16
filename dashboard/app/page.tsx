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
          <div className="grid gap-0 lg:grid-cols-[1fr_360px]">
            <div className="p-6 sm:p-7">
              <p className="text-xs font-semibold uppercase tracking-normal text-red-700">{santaClawsBrand.eyebrow}</p>
              <h1 className="mt-2 text-4xl font-semibold tracking-normal text-slate-950 sm:text-5xl">
                {santaClawsBrand.product}
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-600">
                {santaClawsBrand.tagline}
              </p>
              <div className="mt-5 flex flex-wrap gap-2 text-xs font-semibold text-slate-700">
                <span className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2">shared memory</span>
                <span className="rounded-md border border-red-200 bg-red-50 px-3 py-2">live workshop logs</span>
                <span className="rounded-md border border-sky-200 bg-sky-50 px-3 py-2">Nemotron-powered</span>
              </div>
            </div>
            <div className="flex min-h-48 items-end bg-[radial-gradient(circle_at_25%_20%,#fee2e2,transparent_34%),linear-gradient(135deg,#0f172a,#164e63)] p-6 text-white">
              <div>
                <p className="text-xs font-semibold uppercase tracking-normal text-white/60">Tonight's route</p>
                <p className="mt-2 text-2xl font-semibold tracking-normal">Find shops, forge sites, deliver pitches.</p>
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
