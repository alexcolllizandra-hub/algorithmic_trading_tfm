"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { TooltipShell } from "@/components/landing/charts/ChartFrame";
import { LANDING_CHART } from "@/components/landing/charts/palette";
import { fmtPercent } from "@/lib/format";
import { holdoutBoundary, type VolatilityPoint } from "@/lib/site-data";

export function VolatilityChart({
  points,
  color,
  median,
}: {
  points: VolatilityPoint[];
  color: string;
  median: number;
}) {
  const boundary = holdoutBoundary(points);
  const last = points.at(-1);

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
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
          tick={{ fill: LANDING_CHART.axis, fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          width={64}
          tickFormatter={(value: number) => `${Math.round(value * 100)}%`}
        />

        {boundary && last && (
          <ReferenceArea
            x1={boundary}
            x2={last.t}
            fill={LANDING_CHART.holdoutSoft}
            stroke={LANDING_CHART.holdout}
            strokeOpacity={0.35}
            strokeDasharray="3 3"
          />
        )}

        <ReferenceLine
          y={median}
          stroke={LANDING_CHART.reference}
          strokeDasharray="4 4"
          strokeOpacity={0.6}
          label={{
            value: `mediana ${fmtPercent(median, 0)}`,
            position: "insideBottomRight",
            fill: LANDING_CHART.axis,
            fontSize: 10,
          }}
        />

        <Tooltip
          cursor={{ stroke: LANDING_CHART.axis, strokeDasharray: "3 3" }}
          content={({ active, payload, label }) => {
            if (!active || !payload?.length) return null;
            const point = payload[0].payload as VolatilityPoint;
            return (
              <TooltipShell
                label={String(label)}
                rows={[
                  { key: "Volatilidad anual", value: fmtPercent(point.v, 1), color },
                  {
                    key: "Partición",
                    value: point.p === "holdout" ? "holdout" : "desarrollo",
                  },
                ]}
              />
            );
          }}
        />

        <Line
          type="monotone"
          dataKey="v"
          stroke={color}
          strokeWidth={1.4}
          isAnimationActive={false}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
