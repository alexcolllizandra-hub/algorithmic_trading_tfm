"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useChartColors } from "@/components/charts/theme";
import type { EquityPoint } from "@/lib/api-types";
import { fmtDate } from "@/lib/format";

export function EquityChart({ points }: { points: EquityPoint[] }) {
  const c = useChartColors();
  const data = points.map((p) => ({
    t: p.open_time,
    equity: p.equity,
    drawdown: p.drawdown != null ? p.drawdown * 100 : null,
  }));

  return (
    <div className="space-y-4">
      <ResponsiveContainer width="100%" height={240}>
        <AreaChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <defs>
            <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={c.accent} stopOpacity={0.4} />
              <stop offset="100%" stopColor={c.accent} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={c.grid} strokeDasharray="3 3" />
          <XAxis
            dataKey="t"
            tickFormatter={fmtDate}
            stroke={c.axis}
            tick={{ fontSize: 11 }}
            minTickGap={40}
          />
          <YAxis stroke={c.axis} tick={{ fontSize: 11 }} width={56} domain={["auto", "auto"]} />
          <Tooltip
            labelFormatter={(v) => fmtDate(String(v))}
            contentStyle={{
              background: "rgb(var(--surface-2))",
              border: "1px solid rgb(var(--border))",
            }}
          />
          <Area
            type="monotone"
            dataKey="equity"
            stroke={c.accent}
            fill="url(#eq)"
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>

      <ResponsiveContainer width="100%" height={140}>
        <AreaChart data={data} margin={{ top: 4, right: 16, bottom: 8, left: 0 }}>
          <defs>
            <linearGradient id="dd" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={c.negative} stopOpacity={0} />
              <stop offset="100%" stopColor={c.negative} stopOpacity={0.4} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={c.grid} strokeDasharray="3 3" />
          <XAxis
            dataKey="t"
            tickFormatter={fmtDate}
            stroke={c.axis}
            tick={{ fontSize: 11 }}
            minTickGap={40}
          />
          <YAxis stroke={c.axis} tick={{ fontSize: 11 }} width={56} unit="%" />
          <Tooltip
            labelFormatter={(v) => fmtDate(String(v))}
            contentStyle={{
              background: "rgb(var(--surface-2))",
              border: "1px solid rgb(var(--border))",
            }}
          />
          <Area
            type="monotone"
            dataKey="drawdown"
            stroke={c.negative}
            fill="url(#dd)"
            strokeWidth={1.5}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
