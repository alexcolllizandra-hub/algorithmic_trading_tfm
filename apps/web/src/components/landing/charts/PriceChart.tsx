"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { TooltipShell } from "@/components/landing/charts/ChartFrame";
import { LANDING_CHART } from "@/components/landing/charts/palette";
import { fmtUsd } from "@/lib/format";
import { holdoutBoundary, type PricePoint } from "@/lib/site-data";

export function PriceChart({ points, color }: { points: PricePoint[]; color: string }) {
  const boundary = holdoutBoundary(points);
  const last = points.at(-1);

  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="price-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.28} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>

        <CartesianGrid stroke={LANDING_CHART.grid} strokeDasharray="2 4" vertical={false} />
        <XAxis
          dataKey="t"
          tick={{ fill: LANDING_CHART.axis, fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: LANDING_CHART.grid }}
          minTickGap={48}
          tickFormatter={(value: string) => value.slice(0, 7)}
        />
        <YAxis
          scale="log"
          domain={["auto", "auto"]}
          tick={{ fill: LANDING_CHART.axis, fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          width={64}
          tickFormatter={(value: number) => `${Math.round(value / 1000)}k`}
        />

        {boundary && last && (
          <ReferenceArea
            x1={boundary}
            x2={last.t}
            fill={LANDING_CHART.holdoutSoft}
            stroke={LANDING_CHART.holdout}
            strokeOpacity={0.35}
            strokeDasharray="3 3"
            label={{
              value: "holdout congelado",
              position: "insideTopRight",
              fill: LANDING_CHART.holdout,
              fontSize: 10,
            }}
          />
        )}

        <Tooltip
          cursor={{ stroke: LANDING_CHART.axis, strokeDasharray: "3 3" }}
          content={({ active, payload, label }) => {
            if (!active || !payload?.length) return null;
            const point = payload[0].payload as PricePoint;
            return (
              <TooltipShell
                label={String(label)}
                rows={[
                  { key: "Cierre", value: fmtUsd(point.c, 0), color },
                  {
                    key: "Partición",
                    value: point.p === "holdout" ? "holdout" : "desarrollo",
                  },
                ]}
              />
            );
          }}
        />

        <Area
          type="monotone"
          dataKey="c"
          stroke={color}
          strokeWidth={1.6}
          fill="url(#price-fill)"
          isAnimationActive={false}
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
