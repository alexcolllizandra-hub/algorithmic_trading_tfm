"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useChartColors } from "@/components/charts/theme";
import type { MethodComparison } from "@/lib/api-types";
import { useRb } from "@/lib/i18n/runBrowser";
import { fmtRatio } from "@/lib/format";

export function ComparisonBars({ methods }: { methods: MethodComparison[] }) {
  const c = useChartColors();
  const rb = useRb();
  const data = methods.map((m) => ({
    method: m.method === "genetic_algorithm" ? "GA" : "Random Search",
    sharpe: m.mean_test_sharpe ?? 0,
  }));
  // Bars grow from zero, so the domain must contain zero: recharts' automatic
  // [dataMin, dataMax] on an all-negative series leaves every bar outside the
  // plotting area and the chart renders empty.
  const values = data.map((d) => d.sharpe);
  const lo = Math.min(0, ...values);
  const hi = Math.max(0, ...values);
  const pad = (hi - lo) * 0.1 || 0.1;
  const domain: [number, number] = [lo === 0 ? 0 : lo - pad, hi === 0 ? 0 : hi + pad];
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 16, right: 16, bottom: 8, left: 0 }}>
        <CartesianGrid stroke={c.grid} strokeDasharray="3 3" />
        <XAxis dataKey="method" stroke={c.axis} tick={{ fontSize: 12 }} />
        <YAxis
          stroke={c.axis}
          tick={{ fontSize: 12 }}
          width={56}
          domain={domain}
          tickFormatter={(v: number) => fmtRatio(v)}
        />
        <ReferenceLine y={0} stroke={c.axis} />
        <Tooltip
          contentStyle={{
            background: "rgb(var(--surface-2))",
            border: "1px solid rgb(var(--border))",
          }}
        />
        <Bar dataKey="sharpe" name={rb.meanOosSharpe} radius={[3, 3, 0, 0]} maxBarSize={140}>
          <LabelList
            dataKey="sharpe"
            position="insideBottom"
            formatter={(v: number) => fmtRatio(v)}
            fill="#ffffff"
          />
          {data.map((d, i) => (
            <Cell key={i} fill={d.sharpe >= 0 ? c.positive : c.negative} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
