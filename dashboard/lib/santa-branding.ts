import type { ClawName } from "./types";

export const santaClawsBrand = {
  product: "Santa Claws",
  eyebrow: "NemoClaw North Pole Ops",
  tagline: "A festive autonomous sales workshop for finding, redesigning, pitching, and closing local businesses.",
};

export const santaAgentMeta: Record<
  string,
  {
    title: string;
    shortName: string;
    role: string;
    icon: string;
    cadence: string;
    cadenceSeconds: number;
    focus: string;
    accent: string;
    tone: "emerald" | "red" | "gold" | "frost";
  }
> = {
  scout: {
    title: "Rudolph Scout",
    shortName: "Rudolph",
    role: "Lead Finder",
    icon: "R",
    cadence: "60s sleigh sweep",
    cadenceSeconds: 60,
    focus: "Guides the sleigh toward promising local businesses, scores websites, and adds qualified shops to the nice list.",
    accent: "bg-red-500",
    tone: "red",
  },
  designer: {
    title: "Workshop Elves",
    shortName: "Elves",
    role: "Mockup Forge",
    icon: "E",
    cadence: "60s workshop cycle",
    cadenceSeconds: 60,
    focus: "Crafts premium website mockups, critiques the build, and publishes the best present-ready design.",
    accent: "bg-emerald-500",
    tone: "emerald",
  },
  pitcher: {
    title: "Snowball Pitcher",
    shortName: "Pitcher",
    role: "Outreach Courier",
    icon: "S",
    cadence: "60s delivery route",
    cadenceSeconds: 60,
    focus: "Wraps personalized email angles, picks the strongest pitch, and queues it for approval.",
    accent: "bg-sky-400",
    tone: "frost",
  },
  closer: {
    title: "Cookie Closer",
    shortName: "Closer",
    role: "Reply Handler",
    icon: "C",
    cadence: "30s cocoa check",
    cadenceSeconds: 30,
    focus: "Handles warm replies, proposes meeting times, drafts follow-ups, and books the next stop.",
    accent: "bg-amber-500",
    tone: "gold",
  },
};

export type SantaAgentMeta = (typeof santaAgentMeta)[string];

export function santaAgent(clawName: ClawName | string) {
  return santaAgentMeta[String(clawName)] ?? {
    title: `${String(clawName)} Claw`,
    shortName: String(clawName),
    role: "Workshop Agent",
    icon: "SC",
    cadence: "60s heartbeat",
    cadenceSeconds: 60,
    focus: "Santa Claws runtime worker.",
    accent: "bg-slate-500",
    tone: "frost" as const,
  };
}
