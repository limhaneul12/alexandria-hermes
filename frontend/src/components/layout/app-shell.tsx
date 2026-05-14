"use client";

import { Suspense } from "react";

import { useLibraryStore } from "@/store/library-store";

import { Sidebar } from "@/components/layout/sidebar";
import { TopHeader } from "@/components/layout/top-header";

export function AppShell({ children }: { children: React.ReactNode }) {
  const collapsed = useLibraryStore((state) => state.sidebarCollapsed);
  return (
    <div className="archive-app-shell min-h-screen bg-[#050505] text-[#111]">
      <Suspense fallback={null}><Sidebar /></Suspense>
      <div className={`min-h-screen transition-[padding] ${collapsed ? "lg:pl-[72px]" : "lg:pl-[240px]"}`}>
        <Suspense fallback={null}><TopHeader /></Suspense>
        <main className="archive-main min-h-[calc(100vh-74px)] bg-[#f6f3ec]">{children}</main>
      </div>
    </div>
  );
}
