"use client";

import { useQuery } from "@tanstack/react-query";
import {
  BookOpen,
  Bot,
  Code2,
  Compass,
  Download,
  Feather,
  Library,
  RefreshCw,
  ScrollText,
  Search,
  Share2,
  Star,
} from "lucide-react";
import Link from "next/link";

import { fetchDashboard } from "@/lib/api";
import { t, tx, type Language, type TranslationKey } from "@/lib/i18n";
import { openLibrarianAsk } from "@/lib/librarian/ask-events";
import { useLibraryStore } from "@/store/library-store";
import type { DashboardDTO } from "@/types/library";

const principles = [
  { titleKey: "principleCollectTitle", bodyKey: "principleCollectBody", icon: Library },
  { titleKey: "principleUnderstandTitle", bodyKey: "principleUnderstandBody", icon: BookOpen },
  { titleKey: "principleApplyTitle", bodyKey: "principleApplyBody", icon: Code2 },
  { titleKey: "principleConnectTitle", bodyKey: "principleConnectBody", icon: Share2 },
  { titleKey: "principleEvolveTitle", bodyKey: "principleEvolveBody", icon: RefreshCw },
] as const;

const gettingStarted = [
  { titleKey: "gettingStartedExploreTitle", bodyKey: "gettingStartedExploreBody", icon: Compass },
  { titleKey: "gettingStartedLearnTitle", bodyKey: "gettingStartedLearnBody", icon: BookOpen },
  { titleKey: "gettingStartedUseTitle", bodyKey: "gettingStartedUseBody", icon: Download },
  { titleKey: "gettingStartedConnectTitle", bodyKey: "gettingStartedConnectBody", icon: Share2 },
  { titleKey: "gettingStartedKeepTitle", bodyKey: "gettingStartedKeepBody", icon: Star },
] as const;

const coreConcepts = [
  {
    titleKey: "coreConceptSkillTitle",
    bodyKey: "coreConceptSkillBody",
    examples: ["FastAPI DI", "RAG Pipeline", "Web Search"],
    icon: Code2,
  },
  {
    titleKey: "coreConceptPromptTitle",
    bodyKey: "coreConceptPromptBody",
    examples: ["Code Review", "Planning", "Research"],
    icon: ScrollText,
  },
] as const;

const relatedGuides = [
  "guideCreateSkill",
  "guideRegisterPrompt",
  "guideLibrarianProvider",
  "guideAgentIntegration",
] as const satisfies readonly TranslationKey[];

const rightRailLinks = [
  ["01", "archivePhilosophy", "#archive-philosophy"],
  ["02", "gettingStarted", "#getting-started"],
  ["03", "coreConcepts", "#core-concepts"],
  ["04", "keyFeatures", "/library"],
  ["05", "librarianRecommendations", "/settings/librarians"],
  ["06", "settingsProviders", "/settings"],
] as const satisfies readonly [string, TranslationKey, string][];

function formatCompact(language: Language, value: number) {
  return new Intl.NumberFormat(language === "ko" ? "ko-KR" : "en-US", {
    maximumFractionDigits: 1,
    notation: value >= 10000 ? "compact" : "standard",
  }).format(value);
}

function formatRecentAccess(language: Language, value?: string | null) {
  if (!value) return t(language, "notAccessed");
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return t(language, "recentRecord");
  const diff = Date.now() - date.getTime();
  const hours = Math.max(1, Math.round(diff / 36e5));
  if (hours < 24) return tx(language, "hoursAgo", { count: hours });
  return tx(language, "daysAgo", { count: Math.round(hours / 24) });
}

function StatLine({ language, data }: { language: Language; data?: DashboardDTO }) {
  const stats = data?.stats.slice(0, 4) ?? [];
  if (stats.length === 0) return null;
  return (
    <div className="archive-paper-card mt-8 grid gap-0 overflow-hidden md:grid-cols-4">
      {stats.map((stat) => (
        <div key={stat.label} className="border-b border-[#d8d3c7] p-4 last:border-b-0 md:border-b-0 md:border-r md:last:border-r-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#68635a]">{stat.label}</p>
          <p className="mt-2 font-serif text-3xl text-[#111111]">{formatCompact(language, stat.value)}</p>
          <p className="mt-1 line-clamp-2 text-xs leading-5 text-[#6f6a60]">{stat.hint}</p>
        </div>
      ))}
    </div>
  );
}

export function DashboardClient() {
  const language = useLibraryStore((state) => state.language);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["dashboard"],
    queryFn: fetchDashboard,
  });

  return (
    <div className="archive-document-page archive-document-grid min-h-[calc(100vh-74px)]">
      <article className="min-w-0 px-8 py-10 md:px-14 xl:px-16">
        <section className="relative overflow-hidden border-b border-[#cfc8b8] pb-10">
          <div className="relative z-10 max-w-3xl">
            <p className="text-xs font-bold uppercase tracking-[0.22em] text-[#161616]">{t(language, "guideKicker")}</p>
            <h1 className="mt-5 font-serif text-6xl leading-none tracking-[-0.04em] text-[#070707] md:text-7xl xl:text-8xl">
              {t(language, "guideTitle")}
            </h1>
            <p className="mt-6 max-w-2xl font-serif text-xl leading-8 text-[#191919]">
              {t(language, "guideDescription")}
            </p>
          </div>
          <div className="archive-line-art pointer-events-none absolute right-0 top-0 hidden h-56 w-[430px] lg:block" aria-hidden>
            <div className="absolute bottom-10 right-28 h-16 w-44 border-b border-[#1a1a1a]/35" />
            <BookOpen className="absolute bottom-10 right-28 h-24 w-24 stroke-[1.2] text-[#111111]" />
            <Library className="absolute bottom-20 right-6 h-28 w-28 stroke-[1] text-[#111111]" />
            <Feather className="absolute right-56 top-6 h-20 w-20 rotate-[-18deg] stroke-[1] text-[#111111]" />
          </div>
          {isLoading ? <p className="mt-8 text-sm text-[#6f6a60]">{t(language, "loadingDashboard")}</p> : null}
          {isError ? <p className="mt-8 text-sm text-[#8f5037]">{t(language, "dashboardLoadFailed")}</p> : null}
          <StatLine language={language} data={data} />
        </section>

        <section id="archive-philosophy" className="archive-guide-section grid gap-8 xl:grid-cols-[minmax(0,1fr)_minmax(560px,680px)]">
          <div>
            <h2><span>01</span> {t(language, "archivePhilosophy")}</h2>
            <p className="mt-6 max-w-xl text-sm leading-7 text-[#25211c]">
              {t(language, "archivePhilosophyBody")} {t(language, "archiveGoalIntro")}
            </p>
            <blockquote className="mt-8 border-l border-[#a39b8d] pl-6 font-serif text-2xl leading-9 text-[#151515]">
              {t(language, "archiveGoalQuote")}
            </blockquote>
          </div>
          <div className="archive-paper-card p-6">
            <p className="mb-6 text-center text-xs font-bold uppercase tracking-[0.16em] text-[#1b1b1b]">{t(language, "fivePrinciples")}</p>
            <div className="grid overflow-hidden rounded-sm border border-[#d8d3c7] bg-[#d8d3c7] sm:grid-cols-2 xl:grid-cols-5">
              {principles.map(({ titleKey, bodyKey, icon: Icon }) => (
                <div key={titleKey} className="flex min-h-[168px] flex-col items-center bg-[#fbfaf6] px-4 py-5 text-center">
                  <Icon className="h-8 w-8 shrink-0 stroke-[1.3] text-[#111111]" />
                  <p className="mt-4 text-sm font-bold text-[#111111]">{t(language, titleKey)}</p>
                  <p className="mt-2 text-xs leading-5 text-[#514c44]">{t(language, bodyKey)}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="getting-started" className="archive-guide-section">
          <h2><span>02</span> {t(language, "gettingStarted")}</h2>
          <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            {gettingStarted.map(({ titleKey, bodyKey, icon: Icon }, index) => (
              <Link key={titleKey} href={index === 0 ? "/library" : "/library?sort=recent"} className="archive-paper-card group relative min-h-52 p-6 text-center transition-colors hover:bg-white/80">
                <span className="absolute left-3 top-3 rounded border border-[#bfb6a8] bg-[#f3f0e8] px-1.5 text-sm text-[#111111]">{index + 1}</span>
                <Icon className="mx-auto mt-5 h-12 w-12 stroke-[1.2] text-[#111111]" />
                <h3 className="mt-5 font-serif text-xl text-[#111111]">{t(language, titleKey)}</h3>
                <p className="mt-3 text-sm leading-6 text-[#36322d]">{t(language, bodyKey)}</p>
              </Link>
            ))}
          </div>
        </section>

        <section id="core-concepts" className="archive-guide-section pb-16">
          <h2><span>03</span> {t(language, "coreConcepts")}</h2>
          <div className="mt-6 grid gap-4 xl:grid-cols-2">
            {coreConcepts.map(({ titleKey, bodyKey, examples, icon: Icon }) => (
              <div key={titleKey} className="archive-paper-card grid grid-cols-[64px_minmax(0,1fr)] gap-4 p-6">
                <Icon className="h-10 w-10 stroke-[1.3] text-[#111111]" />
                <div>
                  <h3 className="font-serif text-2xl text-[#111111]">{t(language, titleKey)}</h3>
                  <p className="mt-2 text-sm leading-6 text-[#36322d]">{t(language, bodyKey)}</p>
                  <p className="mt-5 text-xs font-bold uppercase tracking-[0.18em] text-[#514c44]">{t(language, "examples")}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {examples.map((example) => <span key={example} className="rounded border border-[#cfc8b8] px-2 py-1 text-xs text-[#28241f]">{example}</span>)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      </article>

      <aside className="archive-right-rail hidden px-8 py-12 xl:block">
        <div className="sticky top-24 space-y-9">
          <div>
            <p className="mb-4 text-xs font-bold uppercase tracking-[0.18em] text-[#605a50]">{t(language, "onThisPage")}</p>
            <nav className="space-y-2 text-sm text-[#111111]">
              {rightRailLinks.map(([number, labelKey, href], index) => (
                <Link key={labelKey} href={href} className={`flex gap-3 rounded px-3 py-2 ${index === 0 ? "bg-[#e4e0d7] font-semibold" : "hover:bg-[#e9e4da]"}`}>
                  <span>{number}</span><span>{t(language, labelKey)}</span>
                </Link>
              ))}
            </nav>
          </div>

          <div className="border-t border-[#d8d3c7] pt-6">
            <p className="mb-4 text-xs font-bold uppercase tracking-[0.18em] text-[#605a50]">{t(language, "needHelp")}</p>
            <div className="archive-paper-card p-5">
              <div className="flex gap-4">
                <Bot className="h-9 w-9 text-[#111111]" />
                <div>
                  <p className="font-bold text-[#111111]">{t(language, "askLibrarian")}</p>
                  <p className="mt-1 text-sm text-[#514c44]">{t(language, "helpFromLibrarian")}</p>
                  <button
                    type="button"
                    onClick={() => openLibrarianAsk()}
                    className="mt-4 inline-flex items-center gap-2 rounded border border-[#bdb4a5] px-4 py-2 text-sm font-semibold text-[#111111] hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-black/15"
                  >
                    {t(language, "askQuestion")} <Search className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="border-t border-[#d8d3c7] pt-6">
            <p className="mb-4 text-xs font-bold uppercase tracking-[0.18em] text-[#605a50]">{t(language, "relatedGuides")}</p>
            <div className="space-y-3">
              {relatedGuides.map((guide) => (
                <Link key={guide} href="/library" className="flex items-center justify-between text-sm text-[#111111] hover:underline">
                  <span className="flex items-center gap-2"><ScrollText className="h-4 w-4" />{t(language, guide)}</span>
                  <span>›</span>
                </Link>
              ))}
            </div>
          </div>

          {data?.recentlyUsed?.[0] ? (
            <div className="archive-paper-card p-5">
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#605a50]">{t(language, "latestReading")}</p>
              <p className="mt-3 font-serif text-xl text-[#111111]">{data.recentlyUsed[0].title}</p>
              <p className="mt-2 text-sm text-[#514c44]">{formatRecentAccess(language, data.recentlyUsed[0].lastAccessedAt)}</p>
            </div>
          ) : null}
        </div>
      </aside>
    </div>
  );
}
