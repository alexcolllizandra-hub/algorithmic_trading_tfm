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

import { useChartColors } from "@/components/charts/theme";
import { useI18n } from "@/lib/i18n";
import type { StudyFamilyDetail } from "@/lib/api-types";
import { fmtDate, fmtNumber } from "@/lib/format";
import { seedEquitySeries } from "@/lib/study";

interface TooltipEntry {
  dataKey?: string | number;
  value?: number | string | null;
  color?: string;
}

function SeedTooltip({
  active,
  label,
  payload,
  averageKey,
}: {
  active?: boolean;
  label?: number | string;
  payload?: TooltipEntry[];
  averageKey: string;
}) {
  const t = useI18n();
  if (!active || !payload) return null;
  const entries = payload.filter((p) => p.value != null);
  if (entries.length === 0) return null;
  return (
    <div className="rounded-md border border-border bg-surface-2 px-3 py-2 text-xs text-fg shadow-lg">
      <p className="mb-1 font-medium">{fmtDate(new Date(Number(label)).toISOString())}</p>
      {entries.map((entry) => {
        const key = String(entry.dataKey ?? "");
        return (
          <p key={key} className="tabular">
            {key === averageKey ? t.study.chart.averageSeries : key.replace("seed_", "seed ")}:{" "}
            {fmtNumber(Number(entry.value), 4)}
          </p>
        );
      })}
    </div>
  );
}

/**
 * The seed-averaged equity curve over every individual seed's own curve.
 *
 * The dispersion between the thin lines is the point of the chart: one
 * hypothesis, ten arbitrary search seeds, and paths that disagree.
 */
export function SeedEquityChart({
  detail,
  height = 340,
}: {
  detail: StudyFamilyDetail;
  height?: number;
}) {
  const t = useI18n();
  const c = useChartColors();
  const { rows, seedKeys, averageKey } = seedEquitySeries(detail);

  return (
    <div className="space-y-3">
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid stroke={c.grid} strokeDasharray="3 3" />
          <XAxis
            dataKey="x"
            type="number"
            domain={["dataMin", "dataMax"]}
            scale="time"
            stroke={c.axis}
            tick={{ fontSize: 11 }}
            minTickGap={48}
            tickFormatter={(v) => fmtDate(new Date(Number(v)).toISOString())}
          />
          <YAxis
            stroke={c.axis}
            tick={{ fontSize: 11 }}
            width={56}
            domain={["auto", "auto"]}
            tickFormatter={(v) => fmtNumber(Number(v), 2)}
          />
          <Tooltip content={<SeedTooltip averageKey={averageKey} />} />
          {seedKeys.map((key) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              stroke={c.axis}
              strokeWidth={1}
              strokeOpacity={0.45}
              dot={false}
              connectNulls
              isAnimationActive={false}
            />
          ))}
          <Line
            type="monotone"
            dataKey={averageKey}
            stroke={c.accent}
            strokeWidth={2.5}
            dot={false}
            connectNulls
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>

      <div className="flex flex-wrap items-center gap-4 text-xs text-muted">
        <span className="inline-flex items-center gap-2">
          <span aria-hidden className="h-0.5 w-6 rounded" style={{ background: c.accent }} />
          {t.study.chart.averageSeries}
        </span>
        <span className="inline-flex items-center gap-2">
          <span
            aria-hidden
            className="h-0.5 w-6 rounded opacity-50"
            style={{ background: c.axis }}
          />
          {t.study.chart.seedSeries.replace("{n}", String(seedKeys.length))}
        </span>
      </div>
      <p className="text-xs text-muted">{t.study.chart.seedCaption}</p>
    </div>
  );
}
