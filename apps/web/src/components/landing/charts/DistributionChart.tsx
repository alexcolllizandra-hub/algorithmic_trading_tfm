"use client";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { TooltipShell } from "@/components/landing/charts/ChartFrame";
import { LANDING_CHART } from "@/components/landing/charts/palette";
import { fmtNumber } from "@/lib/format";
import type { DistributionItem } from "@/lib/site-data";

/**
 * Observed return density against the Gaussian with the same mean and standard
 * deviation. The vertical axis is logarithmic on purpose: on a linear axis both
 * curves collapse onto the same spike and the entire point — that the tails are
 * orders of magnitude heavier — becomes invisible.
 */
export function DistributionChart({
  distribution,
  color,
}: {
  distribution: DistributionItem;
  color: string;
}) {
  const { mean, std } = distribution.histogram;
  // A log axis cannot draw a zero, and the Gaussian curve underflows long
  // before the observed one does — which is precisely the finding, so the
  // dashed line is allowed to simply stop.
  const data = distribution.histogram.bins.map((bin) => ({
    x: bin.x * 100,
    observed: bin.observed > 0 ? bin.observed : null,
    normal: bin.normal > 1e-3 ? bin.normal : null,
  }));

  const lowerTail = (mean - 3 * std) * 100;
  const upperTail = (mean + 3 * std) * 100;
  const domainMin = data[0]?.x ?? -1;
  const domainMax = data.at(-1)?.x ?? 1;

  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="observed-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.25} />
            <stop offset="100%" stopColor={color} stopOpacity={0.02} />
          </linearGradient>
        </defs>

        <CartesianGrid stroke={LANDING_CHART.grid} strokeDasharray="2 4" vertical={false} />

        <ReferenceArea
          x1={domainMin}
          x2={lowerTail}
          fill={LANDING_CHART.holdoutSoft}
          fillOpacity={1}
        />
        <ReferenceArea
          x1={upperTail}
          x2={domainMax}
          fill={LANDING_CHART.holdoutSoft}
          fillOpacity={1}
        />

        <XAxis
          dataKey="x"
          type="number"
          domain={[domainMin, domainMax]}
          tick={{ fill: LANDING_CHART.axis, fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: LANDING_CHART.grid }}
          tickFormatter={(value: number) => `${value.toFixed(1)}%`}
        />
        <YAxis
          scale="log"
          domain={["auto", "auto"]}
          tick={{ fill: LANDING_CHART.axis, fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          width={52}
          tickFormatter={(value: number) =>
            value >= 1 ? String(Math.round(value)) : value.toFixed(2)
          }
        />

        <Tooltip
          cursor={{ stroke: LANDING_CHART.axis, strokeDasharray: "3 3" }}
          content={({ active, payload, label }) => {
            if (!active || !payload?.length) return null;
            const point = payload[0].payload as {
              observed: number | null;
              normal: number | null;
            };
            return (
              <TooltipShell
                label={`Retorno horario ${Number(label).toFixed(2)}%`}
                rows={[
                  {
                    key: "Observado",
                    value: point.observed == null ? "—" : fmtNumber(point.observed, 2),
                    color,
                  },
                  {
                    key: "Normal teórica",
                    value: point.normal == null ? "—" : fmtNumber(point.normal, 2),
                    color: LANDING_CHART.reference,
                  },
                ]}
              />
            );
          }}
        />

        <Area
          type="stepAfter"
          dataKey="observed"
          stroke={color}
          strokeWidth={1.4}
          fill="url(#observed-fill)"
          isAnimationActive={false}
          dot={false}
          connectNulls={false}
          name="Observado"
        />
        <Line
          type="monotone"
          dataKey="normal"
          stroke={LANDING_CHART.reference}
          strokeWidth={1.4}
          strokeDasharray="4 3"
          isAnimationActive={false}
          dot={false}
          connectNulls={false}
          name="Normal"
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
