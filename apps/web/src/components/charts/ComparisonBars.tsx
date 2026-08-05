"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useChartColors } from "@/components/charts/theme";
import type { MethodComparison } from "@/lib/api-types";
import { fmtRatio } from "@/lib/format";

export function ComparisonBars({ methods }: { methods: MethodComparison[] }) {
  const c = useChartColors();
  const data = methods.map((m) => ({
    method: m.method === "genetic_algorithm" ? "GA" : "Random Search",
    sharpe: m.mean_test_sharpe ?? 0,
  }));
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 16, right: 16, bottom: 8, left: 0 }}>
        <CartesianGrid stroke={c.grid} strokeDasharray="3 3" />
        <XAxis dataKey="method" stroke={c.axis} tick={{ fontSize: 12 }} />
        <YAxis stroke={c.axis} tick={{ fontSize: 12 }} width={56} />
        <Tooltip
          contentStyle={{
            background: "rgb(var(--surface-2))",
            border: "1px solid rgb(var(--border))",
          }}
        />
        <Bar dataKey="sharpe" name="mean OOS test Sharpe" radius={[3, 3, 0, 0]}>
          <LabelList dataKey="sharpe" position="top" formatter={(v: number) => fmtRatio(v)} />
          {data.map((d, i) => (
            <Cell key={i} fill={d.sharpe >= 0 ? c.positive : c.negative} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
