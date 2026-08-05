"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useChartColors } from "@/components/charts/theme";
import type { ConvergencePoint } from "@/lib/api-types";

const METHOD_COLOR: Record<string, "accent" | "alt"> = {
  random_search: "alt",
  genetic_algorithm: "accent",
};

export function ConvergenceChart({ series }: { series: Record<string, ConvergencePoint[]> }) {
  const c = useChartColors();
  const methods = Object.keys(series);
  // Merge to a wide table keyed by evaluation index.
  const maxLen = Math.max(0, ...methods.map((m) => series[m].length));
  const data = Array.from({ length: maxLen }, (_, i) => {
    const row: Record<string, number | null> = { evaluation: i + 1 };
    for (const m of methods) row[m] = series[m][i]?.best_fitness ?? null;
    return row;
  });

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
        <CartesianGrid stroke={c.grid} strokeDasharray="3 3" />
        <XAxis dataKey="evaluation" stroke={c.axis} tick={{ fontSize: 12 }} />
        <YAxis stroke={c.axis} tick={{ fontSize: 12 }} width={56} />
        <Tooltip
          contentStyle={{
            background: "rgb(var(--surface-2))",
            border: "1px solid rgb(var(--border))",
          }}
        />
        <Legend />
        {methods.map((m) => (
          <Line
            key={m}
            type="stepAfter"
            dataKey={m}
            name={m}
            stroke={METHOD_COLOR[m] === "alt" ? c.alt : c.accent}
            dot={false}
            strokeWidth={2}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
