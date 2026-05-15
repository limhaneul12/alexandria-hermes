"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import {
  Archive,
  BookOpen,
  Bot,
  Clock3,
  ClipboardCheck,
  FolderTree,
  Gauge,
  Home,
  Library,
  PlusSquare,
  Search,
  Settings,
  Sparkles,
  Star,
  ScrollText,
  type LucideIcon,
} from "lucide-react";

import { t, type TranslationKey } from "@/lib/i18n";
import { useLibraryStore } from "@/store/library-store";

type NavItem = { labelKey: TranslationKey; href: string; icon: LucideIcon; active?: "exact" | "library" | "type-skill" | "type-prompt" | "settings" | "librarians" | "contexts" | "rag" | "capture" };
type NavSection = { titleKey: TranslationKey | "libraryStatic"; items: NavItem[] };

const sections: NavSection[] = [
  {
    titleKey: "libraryStatic",
    items: [
      { labelKey: "home", href: "/dashboard", icon: Home, active: "exact" },
      { labelKey: "explore", href: "/library", icon: Search, active: "library" },
      { labelKey: "categories", href: "/library#categories", icon: FolderTree },
      { labelKey: "recent", href: "/library?sort=recent", icon: Clock3 },
      { labelKey: "favorites", href: "/library?sort=popular", icon: Star },
    ],
  },
  {
    titleKey: "mySpace",
    items: [
      { labelKey: "myLibrary", href: "/library", icon: Library, active: "library" },
      { labelKey: "mySkills", href: "/library?type=SKILL", icon: BookOpen, active: "type-skill" },
      { labelKey: "myPrompts", href: "/library?type=PROMPT", icon: Archive, active: "type-prompt" },
    ],
  },
  {
    titleKey: "createSection",
    items: [
      { labelKey: "createSkill", href: "/library?create=skill", icon: PlusSquare },
      { labelKey: "createPrompt", href: "/library?create=prompt", icon: PlusSquare },
    ],
  },
  {
    titleKey: "aiLibrarian",
    items: [
      { labelKey: "librarian", href: "/settings/librarians", icon: Bot, active: "librarians" },
      { labelKey: "contextVault", href: "/contexts", icon: ScrollText, active: "contexts" },
      { labelKey: "ragInspector", href: "/rag-inspector", icon: Gauge, active: "rag" },
      { labelKey: "captureReview", href: "/capture-review", icon: ClipboardCheck, active: "capture" },
      { labelKey: "recommendations", href: "/dashboard#archive-philosophy", icon: Sparkles },
    ],
  },
  {
    titleKey: "settings",
    items: [
      { labelKey: "settings", href: "/settings", icon: Settings, active: "settings" },
      { labelKey: "userGuide", href: "/dashboard", icon: BookOpen, active: "exact" },
    ],
  },
];

function isActive(pathname: string, params: URLSearchParams, active?: string) {
  if (!active) return false;
  if (active === "exact") return pathname === "/dashboard" || pathname === "/";
  if (active === "settings") return pathname === "/settings";
  if (active === "librarians") return pathname === "/settings/librarians";
  if (active === "contexts") return pathname.startsWith("/contexts");
  if (active === "rag") return pathname === "/rag-inspector";
  if (active === "capture") return pathname === "/capture-review";
  if (!pathname.startsWith("/library")) return false;
  if (active === "type-skill") return params.get("type") === "SKILL";
  if (active === "type-prompt") return params.get("type") === "PROMPT";
  if (active === "library") return !params.get("type") && !params.get("create");
  return false;
}

export function Sidebar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const language = useLibraryStore((state) => state.language);
  const collapsed = useLibraryStore((state) => state.sidebarCollapsed);
  return (
    <aside className={`fixed inset-y-0 left-0 z-40 hidden overflow-y-auto border-r border-white/15 bg-[#050505] text-white transition-[width] lg:block ${collapsed ? "w-[72px]" : "w-[240px]"}`}>
      <div className={`flex h-[74px] items-center gap-3 border-b border-white/15 ${collapsed ? "justify-center px-0" : "px-7"}`}>
        <Archive className="h-8 w-8 text-white/70" aria-hidden="true" />
        {!collapsed ? (
          <div className="font-serif text-lg font-bold uppercase leading-5 tracking-[0.13em]" translate="no">
            <p>Alexandria</p>
            <p>Archive</p>
          </div>
        ) : null}
      </div>
      <nav className={`space-y-5 py-6 ${collapsed ? "px-3" : "px-6"}`}>
        {sections.map((section) => (
          <section key={section.titleKey} className="border-b border-white/10 pb-4 last:border-b-0">
            {!collapsed ? (
              <p className="mb-3 text-[11px] font-bold uppercase tracking-[0.2em] text-white/66">
                {section.titleKey === "libraryStatic" ? t(language, "library") : t(language, section.titleKey)}
              </p>
            ) : null}
            <div className="space-y-1">
              {section.items.map((item) => {
                const Icon = item.icon;
                const active = isActive(pathname, searchParams, item.active);
                const label = t(language, item.labelKey);
                const className = `group flex h-8 items-center gap-3 border-l text-[13px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/25 ${collapsed ? "justify-center px-0" : "pl-3 pr-2"} ${
                  active ? "border-white bg-transparent text-white" : "border-transparent text-white/70 hover:border-white/30 hover:bg-transparent hover:text-white"
                }`;
                const content = (
                  <>
                    <Icon className="h-4 w-4" aria-hidden="true" />
                    {!collapsed ? label : null}
                  </>
                );
                return (
                  <Link
                    key={`${section.titleKey}-${item.labelKey}`}
                    href={item.href}
                    title={collapsed ? label : undefined}
                    className={className}
                  >
                    {content}
                  </Link>
                );
              })}
            </div>
          </section>
        ))}
        {!collapsed ? (
          <Image
            src="/librarian-reference.png"
            alt="Librarian reading in the archive"
            width={482}
            height={512}
            className="h-auto w-full object-cover grayscale"
            priority
          />
        ) : null}
      </nav>
    </aside>
  );
}
