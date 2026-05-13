"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Archive, BookOpen, Bot, Clock3, Gauge, Heart, History, Library, Search, Settings, Sparkles } from "lucide-react";
import { motion } from "framer-motion";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useLibraryStore } from "@/store/library-store";

const exploreItems = [
  { label: "카테고리", href: "/library", icon: Library },
  { label: "추천 아카이브", href: "/dashboard#recommended", icon: Sparkles },
  { label: "최근에 가져간 스킬", href: "/dashboard#recent", icon: Clock3 },
  { label: "즐겨찾기", href: "/library?view=favorites", icon: Heart },
  { label: "내 기록", href: "/dashboard#usage", icon: History },
];

const settingsItems = [
  { label: "에이전트", href: "/agents", icon: Bot },
  { label: "라이브러리 설정", href: "/settings#library", icon: BookOpen },
  { label: "라리언 설정", href: "/settings", icon: Settings },
];

function isActive(pathname: string, href: string) {
  const cleanHref = href.split("?")[0].split("#")[0];
  if (cleanHref === "/dashboard") return pathname === "/dashboard";
  if (cleanHref === "/library") return pathname.startsWith("/library");
  return pathname === cleanHref;
}

export function Sidebar() {
  const pathname = usePathname();
  const collapsed = useLibraryStore((state) => state.sidebarCollapsed);
  const setCollapsed = useLibraryStore((state) => state.setSidebarCollapsed);

  const renderLink = (item: { label: string; href: string; icon: typeof Archive }) => {
    const Icon = item.icon;
    return (
      <Link
        key={item.label}
        href={item.href}
        className={cn(
          "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition",
          isActive(pathname, item.href)
            ? "border border-gold-300/20 bg-gold-300/10 text-gold-100"
            : "text-stone-400 hover:bg-white/[0.04] hover:text-parchment",
        )}
      >
        <Icon className="h-4 w-4 shrink-0" />
        {!collapsed && <span>{item.label}</span>}
      </Link>
    );
  };

  return (
    <motion.aside
      animate={{ width: collapsed ? 82 : 250 }}
      transition={{ duration: 0.2 }}
      className="sticky top-0 hidden h-screen shrink-0 border-r border-white/10 bg-[#080807]/95 p-4 text-stone-300 lg:block"
    >
      <div className="flex h-full flex-col gap-5">
        <div className="flex items-center gap-3 border-b border-white/10 pb-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-gold-300/30 bg-gold-300/10 text-gold-100">
            <Archive className="h-5 w-5" />
          </div>
          {!collapsed && (
            <div>
              <p className="font-serif text-base tracking-[0.22em] text-gold-100">ALEXANDRIA</p>
              <p className="text-[10px] uppercase tracking-[0.34em] text-bronze">Hermes</p>
            </div>
          )}
        </div>

        <Link
          href="/library"
          className={cn(
            "flex items-center gap-3 rounded-lg px-3 py-3 text-sm transition",
            pathname.startsWith("/library")
              ? "border border-gold-300/20 bg-gold-300/10 text-gold-100"
              : "bg-white/[0.04] text-parchment hover:bg-white/[0.07]",
          )}
        >
          <BookOpen className="h-4 w-4" />
          {!collapsed && <span>서재로 가기</span>}
        </Link>

        <nav className="flex flex-1 flex-col gap-5 overflow-y-auto pr-1">
          <div className="space-y-1">
            {renderLink({ label: "대시보드", href: "/dashboard", icon: Gauge })}
          </div>

          <div className="space-y-2">
            {!collapsed && <p className="px-3 text-xs font-medium text-stone-500">탐색</p>}
            <div className="space-y-1">{exploreItems.map(renderLink)}</div>
          </div>

          <div className="space-y-2">
            {!collapsed && <p className="px-3 text-xs font-medium text-stone-500">설정</p>}
            <div className="space-y-1">{settingsItems.map(renderLink)}</div>
          </div>
        </nav>

        <div className="rounded-2xl border border-white/10 bg-black/25 p-3">
          {!collapsed ? (
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-full border border-gold-300/30 bg-gold-300/10" />
                <div>
                  <p className="text-xs text-stone-500">현재 에이전트</p>
                  <p className="font-serif text-lg text-parchment">Hermes</p>
                </div>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setCollapsed(true)} aria-label="사이드바 접기">
                <Search className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <Button variant="ghost" size="icon" onClick={() => setCollapsed(false)} aria-label="사이드바 펼치기">
              <Bot className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </motion.aside>
  );
}
