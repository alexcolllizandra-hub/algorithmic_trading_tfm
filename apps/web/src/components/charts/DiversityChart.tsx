"use client";

import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useChartColors } from "@/components/charts/theme";
import type { GaGenerationDiversity } from "@/lib/api-types";

export function DiversityChart({ data }: { data: GaGenerationDiversity[] }) {
  const c = useChartColors();
  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
        <CartesianGrid stroke={c.grid} strokeDasharray="3 3" />
        <XAxis dataKey="generation" stroke={c.axis} tick={{ fontSize: 12 }} />
        <YAxis stroke={c.axis} tick={{ fontSize: 12 }} domain={[0, 1]} width={48} />
        <Tooltip
          contentStyle={{
            background: "rgb(var(--surface-2))",
            border: "1px solid rgb(var(--border))",
          }}
        />
        <Legend />
        <Bar
          dataKey="param_diversity"
          name="param diversity"
          fill={c.accent}
          radius={[3, 3, 0, 0]}
        />
        <Line
          dataKey="unique_ratio"
          name="unique ratio"
          stroke={c.alt}
          strokeWidth={2}
          dot={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
