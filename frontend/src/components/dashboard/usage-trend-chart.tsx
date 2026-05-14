"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { DashboardDTO } from "@/types/library";

type TrendPoint = DashboardDTO["usageTrend"][number];

export default function UsageTrendChart({
  ariaLabel,
  points,
}: {
  ariaLabel: string;
  points: TrendPoint[];
}) {
  return (
    <div
      className="h-64 rounded-2xl border border-white/10 bg-black/25 p-4"
      role="img"
      aria-label={ariaLabel}
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points} margin={{ bottom: 4, left: -26, right: 8, top: 10 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.07)" strokeDasharray="3 8" vertical={false} />
          <XAxis
            dataKey="day"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#78716c", fontSize: 11 }}
            dy={10}
          />
          <YAxis hide domain={[0, "dataMax + 5"]} />
          <Tooltip
            contentStyle={{
              background: "rgba(8, 8, 7, 0.94)",
              border: "1px solid rgba(214, 173, 69, 0.25)",
              borderRadius: "14px",
              color: "#d8c59a",
            }}
            cursor={{ stroke: "rgba(214, 173, 69, 0.22)", strokeWidth: 1 }}
            labelStyle={{ color: "#f9e9b3" }}
          />
          <Line
            type="monotone"
            dataKey="usage"
            name="usage"
            stroke="#d6ad45"
            strokeWidth={3}
            dot={{ fill: "#0b0b0b", r: 4, stroke: "#d6ad45", strokeWidth: 2 }}
            activeDot={{ fill: "#f9e9b3", r: 6, stroke: "#d6ad45", strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
