"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { BookOpen, Clock3, Flame, ScrollText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { formatRelative } from "@/lib/utils";
import type { SkillCardDTO } from "@/types/library";

export function SkillCard({ skill, view = "grid" }: { skill: SkillCardDTO; view?: "grid" | "list" }) {
  const href = `/library/${skill.category.slug}/${skill.id}`;
  return (
    <motion.div whileHover={{ y: -4 }} transition={{ duration: 0.18 }}>
      <Link href={href}>
        <Card className={view === "list" ? "p-4" : "book-cover group min-h-[280px] p-5"}>
          <div className={view === "list" ? "flex flex-col gap-4 md:flex-row md:items-center md:justify-between" : "flex h-full flex-col"}>
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-3">
                <Badge>{skill.type}</Badge>
                <span className="flex items-center gap-1 text-xs text-stone-500">
                  <Flame className="h-3.5 w-3.5 text-gold-300" /> {skill.usageCount}
                </span>
              </div>
              <div>
                <h3 className="font-serif text-2xl leading-tight text-gold-100">{skill.title}</h3>
                <p className="mt-2 line-clamp-3 text-sm leading-6 text-stone-400">{skill.description}</p>
              </div>
            </div>
            <div className="mt-6 flex flex-wrap gap-2">
              {skill.tags.slice(0, 3).map((tag) => (
                <span key={tag} className="rounded-full bg-white/[0.05] px-2 py-1 text-xs text-stone-300">
                  {tag}
                </span>
              ))}
            </div>
            <div className="mt-auto flex items-center justify-between border-t border-white/10 pt-4 text-xs text-stone-500">
              <span className="flex items-center gap-1.5">
                <Clock3 className="h-3.5 w-3.5" /> {formatRelative(skill.lastAccessedAt)}
              </span>
              <span className="flex items-center gap-1.5">
                {skill.type === "WORKFLOW" ? <ScrollText className="h-3.5 w-3.5" /> : <BookOpen className="h-3.5 w-3.5" />}
                {skill.category.name}
              </span>
            </div>
          </div>
        </Card>
      </Link>
    </motion.div>
  );
}
