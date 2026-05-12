"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Archive, BookOpen, Sparkles } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { fetchDashboard } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SkillCard } from "@/components/library/skill-card";

export function DashboardClient() {
  const { data, isLoading } = useQuery({ queryKey: ["dashboard"], queryFn: fetchDashboard });

  if (isLoading || !data) {
    return <div className="rounded-2xl border border-white/10 p-10 text-stone-400">Opening the archive...</div>;
  }

  return (
    <div className="space-y-8">
      <section className="overflow-hidden rounded-3xl border border-gold-300/20 bg-[radial-gradient(circle_at_20%_20%,rgba(214,173,69,0.20),transparent_30%),linear-gradient(135deg,rgba(30,26,18,0.95),rgba(10,10,10,0.98))] p-8 shadow-gold">
        <div className="max-w-4xl space-y-4">
          <p className="text-xs uppercase tracking-[0.34em] text-gold-300">Grand Archive</p>
          <h2 className="font-serif text-5xl leading-none text-gold-50 md:text-7xl">AI capability memory, curated for agents.</h2>
          <p className="max-w-2xl text-base leading-7 text-stone-300">
            A luxurious operating library for reusable skills, workflows, and engineering knowledge. Built for agent teams that need recall, governance, and repeatable execution.
          </p>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {data.stats.map((stat, index) => (
          <motion.div key={stat.label} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.04 }}>
            <Card className="p-5">
              <p className="text-sm text-stone-500">{stat.label}</p>
              <p className="mt-3 font-serif text-4xl text-gold-100">{stat.value}</p>
              <p className="mt-2 text-xs text-stone-500">{stat.hint}</p>
            </Card>
          </motion.div>
        ))}
      </section>

      <section id="recent" className="space-y-4">
        <div className="flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-gold-300" />
          <h3 className="font-serif text-3xl text-parchment">Recently Used Skills</h3>
        </div>
        <div className="grid gap-4 xl:grid-cols-3 2xl:grid-cols-5">
          {data.recentlyUsed.map((skill) => (
            <SkillCard key={skill.id} skill={skill} />
          ))}
        </div>
      </section>

      <section id="recommended" className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Sparkles className="h-5 w-5" /> Recommended Archives</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2">
            {data.recommendations.map((item) => (
              <div key={item.id} className="rounded-xl border border-white/10 bg-black/20 p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-serif text-lg text-gold-100">{item.title}</p>
                  <span className="rounded-full bg-gold-300/10 px-2 py-1 text-xs text-gold-100">{item.type}</span>
                </div>
                <p className="mt-2 text-sm leading-6 text-stone-400">{item.description}</p>
                <p className="mt-3 text-xs text-stone-500">{item.usageCount} archive citations</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <div id="usage" className="grid gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Category Activity</CardTitle>
            </CardHeader>
            <CardContent className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.categoryActivity}>
                  <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
                  <XAxis dataKey="name" stroke="#8f8a7c" fontSize={11} />
                  <YAxis stroke="#8f8a7c" fontSize={11} />
                  <Tooltip contentStyle={{ background: "#111", border: "1px solid rgba(214,173,69,.25)", color: "#d8c59a" }} />
                  <Bar dataKey="value" fill="#d6ad45" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>7-Day Usage Trend</CardTitle>
            </CardHeader>
            <CardContent className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.usageTrend}>
                  <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
                  <XAxis dataKey="day" stroke="#8f8a7c" fontSize={11} />
                  <YAxis stroke="#8f8a7c" fontSize={11} />
                  <Tooltip contentStyle={{ background: "#111", border: "1px solid rgba(214,173,69,.25)", color: "#d8c59a" }} />
                  <Line type="monotone" dataKey="usage" stroke="#d6ad45" strokeWidth={3} dot={{ fill: "#d6ad45" }} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>
      </section>

      <div className="flex items-center gap-2 text-sm text-stone-500">
        <Archive className="h-4 w-4" /> Steam Library for AI capabilities · Notion-style operational knowledge · Internal AI platform memory.
      </div>
    </div>
  );
}
