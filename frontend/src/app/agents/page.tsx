import { Bot, BrainCircuit, CheckCircle2, Clock3, Database, ScrollText, ShieldCheck, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const agents = [
  {
    name: "Claude 3.5",
    role: "Hermes Librarian",
    status: "Active",
    focus: "Archive retrieval, skill matching, and workflow recall",
    tools: ["Semantic search", "Usage history", "Capability routing"],
  },
  {
    name: "Alexandria Core",
    role: "Knowledge Steward",
    status: "Standby",
    focus: "Curates new documents and links them to shelves",
    tools: ["Taxonomy", "Version notes", "Governance"],
  },
  {
    name: "Operations Scribe",
    role: "Workflow Archivist",
    status: "Standby",
    focus: "Turns incident runbooks into reusable agent procedures",
    tools: ["Runbooks", "Retries", "Recovery"],
  },
];

const queue = [
  "Index new FastAPI router rules into capability shelves",
  "Review cursor pagination policy for scroll-heavy archive views",
  "Promote Redis recovery workflow to recommended archives",
];

export default function AgentsPage() {
  return (
    <div className="space-y-7">
      <section className="rounded-3xl border border-gold-300/20 bg-[radial-gradient(circle_at_15%_10%,rgba(214,173,69,0.18),transparent_28%),linear-gradient(135deg,rgba(22,22,22,0.95),rgba(9,8,7,0.98))] p-8 shadow-gold">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs uppercase tracking-[0.34em] text-bronze">Agents</p>
            <h2 className="mt-3 font-serif text-5xl text-gold-50">Librarian operators for the grand archive.</h2>
            <p className="mt-4 text-base leading-7 text-stone-300">
              Monitor active AI agents, their archive roles, and the operational queues that keep capabilities discoverable and reusable.
            </p>
          </div>
          <div className="rounded-2xl border border-gold-300/20 bg-black/30 p-5 text-sm text-stone-400">
            <div className="flex items-center gap-2 text-gold-100">
              <ShieldCheck className="h-4 w-4" /> Governance ready
            </div>
            <p className="mt-2">Versioned skill reads · tagged workflows · local SQLite source of truth</p>
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        {agents.map((agent) => (
          <Card key={agent.name} className="p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-gold-300/25 bg-gold-300/10 text-gold-100">
                  <Bot className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-serif text-2xl text-gold-100">{agent.name}</h3>
                  <p className="text-sm text-stone-400">{agent.role}</p>
                </div>
              </div>
              <Badge className={agent.status === "Active" ? "bg-emerald-500/10 text-emerald-200" : undefined}>{agent.status}</Badge>
            </div>
            <p className="mt-5 text-sm leading-6 text-stone-300">{agent.focus}</p>
            <div className="mt-5 flex flex-wrap gap-2">
              {agent.tools.map((tool) => (
                <span key={tool} className="rounded-full bg-white/[0.05] px-2.5 py-1 text-xs text-stone-300">
                  {tool}
                </span>
              ))}
            </div>
          </Card>
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><BrainCircuit className="h-5 w-5" /> Capability Queue</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {queue.map((item, index) => (
              <div key={item} className="flex gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-4">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gold-300/10 text-xs text-gold-100">{index + 1}</span>
                <p className="text-sm leading-6 text-stone-300">{item}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Sparkles className="h-5 w-5" /> Operating Signals</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2">
            {[
              { icon: Database, label: "Archive sync", value: "SQLite + Prisma" },
              { icon: ScrollText, label: "Latest artifact", value: "Capability intake" },
              { icon: Clock3, label: "Cadence", value: "Daily review" },
              { icon: CheckCircle2, label: "Policy", value: "Versioned reads" },
            ].map((signal) => {
              const Icon = signal.icon;
              return (
                <div key={signal.label} className="rounded-xl border border-white/10 bg-black/25 p-4">
                  <Icon className="h-5 w-5 text-gold-300" />
                  <p className="mt-3 text-xs uppercase tracking-[0.22em] text-stone-500">{signal.label}</p>
                  <p className="mt-1 font-serif text-xl text-parchment">{signal.value}</p>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
