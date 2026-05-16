import { ActivityFeed } from "@/components/ActivityFeed";
import { ClawCard } from "@/components/ClawCard";
import { LeadsTable } from "@/components/LeadsTable";
import { MetricsBar } from "@/components/MetricsBar";

const claws = [
  {
    name: "scout",
    title: "Scout Claw",
    focus: "Finds local businesses, scores websites, and qualifies leads for mockups.",
    state: "Active",
    cadence: "60s heartbeat",
    tone: "teal",
  },
  {
    name: "designer",
    title: "Designer Claw",
    focus: "Builds three Tailwind mockups, critiques them, and publishes the winner.",
    state: "Active",
    cadence: "60s heartbeat",
    tone: "amber",
  },
  {
    name: "pitcher",
    title: "Pitcher Claw",
    focus: "Drafts four email angles, critiques them, and queues the best outreach.",
    state: "Active",
    cadence: "60s heartbeat",
    tone: "rose",
  },
  {
    name: "closer",
    title: "Closer Claw",
    focus: "Handles interested replies, proposes meeting times, and books follow-up.",
    state: "Active",
    cadence: "30s heartbeat",
    tone: "violet",
  },
] as const;

export default function Page() {
  return (
    <main className="min-h-screen px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="flex flex-col justify-between gap-4 border-b border-slate-200 pb-6 md:flex-row md:items-end">
          <div>
            <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">NemoClaw Command</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-normal text-slate-950">
              Mainstreet Dashboard
            </h1>
          </div>
          <p className="max-w-xl text-sm leading-6 text-slate-600">
            Four Nemotron-powered claws coordinating through Supabase shared memory and action logs.
          </p>
        </header>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {claws.map((claw) => (
            <ClawCard key={claw.name} {...claw} />
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
