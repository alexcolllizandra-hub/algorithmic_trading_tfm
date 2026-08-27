"use client";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useChartColors } from "@/components/charts/theme";
import { useI18n } from "@/lib/i18n";
import type { StudyMonteCarlo } from "@/lib/api-types";
import { fmtInt, fmtNumber } from "@/lib/format";
import { fanDomain, monteCarloRows, type FanRow } from "@/lib/study";

function FanTooltip({
  active,
  label,
  payload,
}: {
  active?: boolean;
  label?: number | string;
  payload?: { payload?: FanRow }[];
}) {
  const t = useI18n();
  const row = payload?.[0]?.payload;
  if (!active || !row) return null;
  const lines: [string, number | null][] = [
    [t.study.fan.observedSeries, row.observed],
    ["p95", row.p95],
    ["p75", row.p75],
    ["p50", row.p50],
    ["p25", row.p25],
    ["p05", row.p05],
  ];
  return (
    <div className="rounded-md border border-border bg-surface-2 px-3 py-2 text-xs text-fg shadow-lg">
      <p className="mb-1 font-medium">
        {t.study.fan.barLabel} {fmtInt(Number(label))}
      </p>
      {lines.map(([name, value]) => (
        <p key={name} className="tabular">
          {name}: {fmtNumber(value, 4)}
        </p>
      ))}
    </div>
  );
}

/**
 * Resampling fan: p05–p95 and p25–p75 bands, the median path and the observed
 * path. Bands are drawn as two stacked areas (an invisible lower bound plus the
 * band height), which forces an explicit y-domain so the axis is not dragged to
 * zero by the stack baseline.
 */
export function MonteCarloFan({ mc, height = 300 }: { mc: StudyMonteCarlo; height?: number }) {
  const t = useI18n();
  const c = useChartColors();
  const rows = monteCarloRows(mc);
  const [low, high] = fanDomain(rows);

  return (
    <div className="space-y-3">
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={rows} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid stroke={c.grid} strokeDasharray="3 3" />
          <XAxis
            dataKey="x"
            type="number"
            domain={["dataMin", "dataMax"]}
            stroke={c.axis}
            tick={{ fontSize: 11 }}
            minTickGap={48}
            tickFormatter={(v) => fmtInt(Number(v))}
          />
          <YAxis
            stroke={c.axis}
            tick={{ fontSize: 11 }}
            width={56}
            domain={[low, high]}
            allowDataOverflow
            tickFormatter={(v) => fmtNumber(Number(v), 2)}
          />
          <Tooltip content={<FanTooltip />} />
          <Area
            dataKey="p05"
            stackId="outer"
            stroke="none"
            fill="none"
            fillOpacity={0}
            isAnimationActive={false}
          />
          <Area
            dataKey="span0595"
            stackId="outer"
            stroke="none"
            fill={c.axis}
            fillOpacity={0.18}
            isAnimationActive={false}
          />
          <Area
            dataKey="p25"
            stackId="inner"
            stroke="none"
            fill="none"
            fillOpacity={0}
            isAnimationActive={false}
          />
          <Area
            dataKey="span2575"
            stackId="inner"
            stroke="none"
            fill={c.axis}
            fillOpacity={0.3}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="p50"
            stroke={c.axis}
            strokeWidth={1.5}
            strokeDasharray="4 3"
            dot={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="observed"
            stroke={c.accent}
            strokeWidth={2.5}
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>

      <div className="flex flex-wrap items-center gap-4 text-xs text-muted">
        <span className="inline-flex items-center gap-2">
          <span aria-hidden className="h-0.5 w-6 rounded" style={{ background: c.accent }} />
          {t.study.fan.observedSeries}
        </span>
        <span className="inline-flex items-center gap-2">
          <span
            aria-hidden
            className="h-0.5 w-6 rounded opacity-70"
            style={{ background: c.axis }}
          />
          {t.study.fan.medianSeries}
        </span>
        <span className="inline-flex items-center gap-2">
          <span aria-hidden className="h-3 w-6 rounded opacity-30" style={{ background: c.axis }} />
          {t.study.fan.innerBand}
        </span>
        <span className="inline-flex items-center gap-2">
          <span aria-hidden className="h-3 w-6 rounded opacity-15" style={{ background: c.axis }} />
          {t.study.fan.outerBand}
        </span>
      </div>
    </div>
  );
}
