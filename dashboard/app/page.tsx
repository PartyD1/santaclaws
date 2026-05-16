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
    cadence: "60 second heartbeat",
    tone: "teal",
  },
  {
    name: "designer",
    title: "Designer Claw",
    focus: "Builds Tailwind mockups, critiques them, and publishes the chosen site.",
    state: "Active",
    cadence: "60 second heartbeat",
    tone: "amber",
  },
  {
    name: "pitcher",
    title: "Pitcher Claw",
    focus: "Drafts outreach after Designer ships a mockup for the business.",
    state: "Next",
    cadence: "60 second heartbeat",
    tone: "rose",
  },
  {
    name: "closer",
    title: "Closer Claw",
    focus: "Handles interested replies, proposes meeting times, and books follow-up.",
    state: "Next",
    cadence: "30 second heartbeat",
    tone: "violet",
  },
] as const;

export default function Page() {
  return (
    <main className="min-h-screen px-4 py-5 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-5">
        <header className="flex flex-col justify-between gap-3 border-b border-slate-200 pb-5 md:flex-row md:items-end">
          <div>
            <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">NemoClaw Command</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-normal text-slate-950">
              Mainstreet Dashboard
            </h1>
          </div>
          <p className="max-w-xl text-sm leading-6 text-slate-600">
            Four Nemotron-powered claws coordinating through Supabase shared memory.
          </p>
        </header>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {claws.map((claw) => (
            <ClawCard key={claw.name} {...claw} />
          ))}
        </section>

        <MetricsBar />

        <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
          <LeadsTable />
          <ActivityFeed />
        </section>
      </div>
    </main>
  );
}
