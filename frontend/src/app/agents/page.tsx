"use client";

import { useQuery } from "@tanstack/react-query";
import { Bot, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { fetchAgents } from "@/lib/api";
import { t } from "@/lib/i18n";
import { useLibraryStore } from "@/store/library-store";

export default function AgentsPage() {
  const language = useLibraryStore((state) => state.language);
  const agentsQuery = useQuery({ queryKey: ["agents"], queryFn: fetchAgents });

  return (
    <div className="space-y-7">
      <section className="rounded-3xl border border-gold-300/20 bg-[radial-gradient(circle_at_15%_10%,rgba(214,173,69,0.18),transparent_28%),linear-gradient(135deg,rgba(22,22,22,0.95),rgba(9,8,7,0.98))] p-8 shadow-gold">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs uppercase tracking-[0.34em] text-bronze">{t(language, "agents")}</p>
            <h2 className="mt-3 font-serif text-5xl text-gold-50">{t(language, "agentsTitle")}</h2>
            <p className="mt-4 text-base leading-7 text-stone-300">
              {t(language, "agentsDescription")}
            </p>
          </div>
          <div className="rounded-2xl border border-gold-300/20 bg-black/30 p-5 text-sm text-stone-400">
            <div className="flex items-center gap-2 text-gold-100">
              <ShieldCheck className="h-4 w-4" /> {t(language, "agentsReady")}
            </div>
            <p className="mt-2">{t(language, "agentsReadyDescription")}</p>
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        {agentsQuery.isLoading ? (
          <Card className="p-5 xl:col-span-3">
            <p className="text-sm text-stone-400">{t(language, "loadingAgents")}</p>
          </Card>
        ) : agentsQuery.isError ? (
          <Card className="p-5 xl:col-span-3">
            <p className="text-sm text-red-300">{t(language, "agentsLoadFailed")}</p>
          </Card>
        ) : agentsQuery.data?.length ? (
          agentsQuery.data.map((agent) => (
            <Card key={agent.id} className="p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-gold-300/25 bg-gold-300/10 text-gold-100">
                    <Bot className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="font-serif text-2xl text-gold-100">{agent.name}</h3>
                    <p className="text-sm text-stone-400">{agent.provider}</p>
                  </div>
                </div>
                <Badge>{t(language, "agentsReady")}</Badge>
              </div>
              <p className="mt-5 text-sm leading-6 text-stone-300">
                {agent.description ?? t(language, "agentDescriptionFallback")}
              </p>
              <div className="mt-5 flex flex-wrap gap-2">
                {agent.capabilities.map((capability) => (
                  <span key={capability} className="rounded-full bg-white/[0.05] px-2.5 py-1 text-xs text-stone-300">
                    {capability}
                  </span>
                ))}
              </div>
            </Card>
          ))
        ) : (
          <Card className="p-5 xl:col-span-3">
            <p className="text-sm text-stone-400">{t(language, "noAgents")}</p>
          </Card>
        )}
      </section>
    </div>
  );
}
