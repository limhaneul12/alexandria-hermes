"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Archive,
  BookOpen,
  Bot,
  Code2,
  Home,
  Library,
  ScrollText,
  Settings,
  type LucideIcon,
} from "lucide-react";

import { t, type Language, type TranslationKey } from "@/lib/i18n";
import { useLibraryStore } from "@/store/library-store";

type ActiveTarget =
  | "dashboard"
  | "library"
  | "skills"
  | "prompts"
  | "librarian-chat"
  | "librarians"
  | "settings"
  | "contexts"
  | "memory-compacts";

type NavItem = { labelKey: TranslationKey; href: string; icon: LucideIcon; active: ActiveTarget };
type NavSection = { titleKey: TranslationKey | "libraryStatic" | "memoryStatic"; items: NavItem[] };

const sections: NavSection[] = [
  {
    titleKey: "libraryStatic",
    items: [
      { labelKey: "home", href: "/dashboard", icon: Home, active: "dashboard" },
      { labelKey: "myLibrary", href: "/library", icon: Library, active: "library" },
      { labelKey: "mySkills", href: "/library/skills", icon: Code2, active: "skills" },
      { labelKey: "myPrompts", href: "/library/prompts", icon: Archive, active: "prompts" },
    ],
  },
  {
    titleKey: "memoryStatic",
    items: [
      { labelKey: "contextVault", href: "/contexts", icon: ScrollText, active: "contexts" },
      { labelKey: "memoryCompacts", href: "/memory-compacts", icon: BookOpen, active: "memory-compacts" },
    ],
  },
  {
    titleKey: "aiLibrarian",
    items: [
      { labelKey: "librarianChat", href: "/librarian/chat", icon: Bot, active: "librarian-chat" },
      { labelKey: "librarianSettings", href: "/settings/librarians", icon: Settings, active: "librarians" },
    ],
  },
  {
    titleKey: "settings",
    items: [
      { labelKey: "settings", href: "/settings", icon: Settings, active: "settings" },
      { labelKey: "userGuide", href: "/dashboard", icon: BookOpen, active: "dashboard" },
    ],
  },
];

function sectionTitle(language: Language, key: NavSection["titleKey"]) {
  if (key === "libraryStatic") return t(language, "library");
  if (key === "memoryStatic") return "장기기억";
  return t(language, key);
}

function isActive(pathname: string, active: ActiveTarget) {
  if (active === "dashboard") return pathname === "/dashboard" || pathname === "/";
  if (active === "library") return pathname === "/library" || /^\/library\/[^/]+$/.test(pathname);
  if (active === "skills") return pathname === "/library/skills";
  if (active === "prompts") return pathname === "/library/prompts";
  if (active === "librarian-chat") return pathname === "/librarian/chat";
  if (active === "settings") return pathname === "/settings";
  if (active === "librarians") return pathname === "/settings/librarians";
  if (active === "contexts") return pathname.startsWith("/contexts");
  if (active === "memory-compacts") return pathname.startsWith("/memory-compacts");
  return false;
}

export function Sidebar() {
  const pathname = usePathname();
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
                {sectionTitle(language, section.titleKey)}
              </p>
            ) : null}
            <div className="space-y-1">
              {section.items.map((item) => {
                const Icon = item.icon;
                const active = isActive(pathname, item.active);
                const label = t(language, item.labelKey);
                const className = `group flex h-8 items-center gap-3 border-l text-[13px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/25 ${collapsed ? "justify-center px-0" : "pl-3 pr-2"} ${
                  active ? "border-white bg-transparent text-white" : "border-transparent text-white/70 hover:border-white/30 hover:bg-transparent hover:text-white"
                }`;
                return (
                  <Link key={`${section.titleKey}-${item.labelKey}`} href={item.href} title={collapsed ? label : undefined} className={className}>
                    <Icon className="h-4 w-4" aria-hidden="true" />
                    {!collapsed ? label : null}
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
