"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Archive,
  Bot,
  Clock3,
  Compass,
  Database,
  Gauge,
  Heart,
  History,
  Library,
  Search,
  Settings,
  SlidersHorizontal,
  Sparkles,
} from "lucide-react";
import { motion } from "framer-motion";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useLibraryStore } from "@/store/library-store";

const navItems = [
  { label: "Dashboard", href: "/dashboard", icon: Gauge },
  { label: "Search", href: "/library", icon: Search },
  { label: "Categories", href: "/library/computer-science", icon: Library },
  { label: "Recommended Archives", href: "/dashboard#recommended", icon: Sparkles },
  { label: "Recently Used Skills", href: "/dashboard#recent", icon: Clock3 },
  { label: "Favorites", href: "/library?view=favorites", icon: Heart },
  { label: "My History", href: "/dashboard#usage", icon: History },
  { label: "Agents", href: "/agents", icon: Bot },
  { label: "Settings", href: "/settings", icon: Settings },
  { label: "Library Settings", href: "/settings#library", icon: SlidersHorizontal },
];

export function Sidebar() {
  const pathname = usePathname();
  const collapsed = useLibraryStore((state) => state.sidebarCollapsed);
  const setCollapsed = useLibraryStore((state) => state.setSidebarCollapsed);

  return (
    <motion.aside
      animate={{ width: collapsed ? 88 : 288 }}
      transition={{ duration: 0.2 }}
      className="sticky top-0 hidden h-screen shrink-0 border-r border-white/10 bg-[#090807]/95 p-4 text-stone-300 lg:block"
    >
      <div className="flex h-full flex-col gap-5">
        <div className="flex items-center gap-3 border-b border-white/10 pb-5">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-gold-300/30 bg-gold-300/10 text-gold-100">
            <Archive className="h-5 w-5" />
          </div>
          {!collapsed && (
            <div>
              <p className="font-serif text-lg tracking-[0.22em] text-gold-100">ALEXANDRIA</p>
              <p className="text-xs uppercase tracking-[0.34em] text-bronze">Hermes</p>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between gap-2">
          {!collapsed && <p className="text-xs uppercase tracking-[0.28em] text-stone-500">Grand Archive</p>}
          <Button variant="ghost" size="icon" onClick={() => setCollapsed(!collapsed)} aria-label="Toggle sidebar">
            <Compass className="h-4 w-4" />
          </Button>
        </div>

        <nav className="flex flex-1 flex-col gap-1 overflow-y-auto pr-1">
          {navItems.map((item) => {
            const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href.split("?")[0].split("#")[0]));
            const Icon = item.icon;
            return (
              <Link
                key={item.label}
                href={item.href}
                className={cn(
                  "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition",
                  active
                    ? "border border-gold-300/25 bg-gold-300/10 text-gold-100"
                    : "text-stone-400 hover:bg-white/[0.04] hover:text-parchment",
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        <div className="rounded-2xl border border-gold-300/20 bg-gradient-to-br from-gold-300/10 to-transparent p-4">
          <div className="mb-3 flex items-center gap-2 text-gold-100">
            <Bot className="h-4 w-4" />
            {!collapsed && <span className="text-xs uppercase tracking-[0.22em]">Active Agent</span>}
          </div>
          {!collapsed && (
            <div className="space-y-2">
              <p className="font-serif text-xl text-parchment">Claude 3.5</p>
              <p className="text-sm text-stone-400">Hermes Librarian</p>
              <div className="flex items-center gap-2 text-xs text-gold-200">
                <Database className="h-3.5 w-3.5" />
                Archive sync ready
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.aside>
  );
}
