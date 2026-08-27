"use client";

// Live EDA charts for the research panel, computed in the browser from the
// same static exports the landing uses. Colours come from the design-system
// CSS variables so every chart follows the panel's light/dark theme — these
// replace the former matplotlib-PNG gallery as the page's primary content.

import { Fragment, useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ComposedChart,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useI18n, useIntlLocale } from "@/lib/i18n";
import type { DistributionItem, MarketSeries } from "@/lib/site-data";
import { fmtInt, fmtNumber } from "@/lib/format";

export const PANEL_CHART = {
  grid: "var(--border)",
  axis: "var(--muted)",
  accent: "var(--accent)",
  negative: "rgb(248 113 113)",
  holdout: "rgb(251 191 36)",
} as const;

const TOOLTIP_STYLE = {
  background: "var(--surface-2)",
  border: "1px solid var(--border)",
  borderRadius: 6,
  fontSize: 12,
} as const;

function yearTicks(points: { t: string }[]): string[] {
  const seen = new Set<string>();
  const ticks: string[] = [];
  for (const point of points) {
    const year = point.t.slice(0, 4);
    if (!seen.has(year)) {
      seen.add(year);
      ticks.push(point.t);
    }
  }
  return ticks;
}

/** Explanation footer: "what it shows / what it implies", two short lines. */
export function ChartReading({ what, why }: { what: string; why: string }) {
  return (
    <div className="mt-4 space-y-1.5 border-t border-border pt-3">
      <p className="text-xs leading-relaxed text-muted">{what}</p>
      <p className="text-xs leading-relaxed text-muted">{why}</p>
    </div>
  );
}

export function EdaPriceChart({ series }: { series: MarketSeries }) {
  const t = useI18n();
  const holdoutStart = useMemo(
    () => series.price.find((point) => point.p === "holdout")?.t ?? null,
    [series]
  );
  const last = series.price[series.price.length - 1]?.t;
  const ticks = useMemo(() => yearTicks(series.price), [series]);

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={series.price} margin={{ top: 6, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid stroke={PANEL_CHART.grid} strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="t"
          ticks={ticks}
          tickFormatter={(v: string) => v.slice(0, 4)}
          stroke={PANEL_CHART.axis}
          tick={{ fontSize: 11 }}
        />
        <YAxis
          scale="log"
          domain={["auto", "auto"]}
          stroke={PANEL_CHART.axis}
          tick={{ fontSize: 11 }}
          width={64}
          tickFormatter={(v) => Number(v).toLocaleString()}
        />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(value: number) => [Number(value).toLocaleString(), series.symbol]}
        />
        {holdoutStart && last && (
          <ReferenceArea
            x1={holdoutStart}
            x2={last}
            fill={PANEL_CHART.holdout}
            fillOpacity={0.08}
            label={{
              value: t.eda.holdoutLabel,
              position: "insideTopRight",
              fill: PANEL_CHART.holdout,
              fontSize: 10,
            }}
          />
        )}
        <Line
          dataKey="c"
          dot={false}
          stroke={PANEL_CHART.accent}
          strokeWidth={1.5}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function EdaVolatilityChart({ series }: { series: MarketSeries }) {
  const points = series.volatility;
  const t = useI18n();
  const median = useMemo(() => {
    const values = points.map((point) => point.v).sort((a, b) => a - b);
    return values.length ? values[Math.floor(values.length / 2)] : 0;
  }, [points]);
  const ticks = useMemo(() => yearTicks(points), [points]);

  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={points} margin={{ top: 6, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid stroke={PANEL_CHART.grid} strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="t"
          ticks={ticks}
          tickFormatter={(v: string) => v.slice(0, 4)}
          stroke={PANEL_CHART.axis}
          tick={{ fontSize: 11 }}
        />
        <YAxis
          stroke={PANEL_CHART.axis}
          tick={{ fontSize: 11 }}
          width={52}
          tickFormatter={(v) => `${(Number(v) * 100).toFixed(0)}%`}
        />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(value: number) => [`${(Number(value) * 100).toFixed(1)}%`, ""]}
        />
        <ReferenceLine
          y={median}
          stroke={PANEL_CHART.axis}
          strokeDasharray="4 3"
          label={{
            value: t.eda.medianLabel,
            position: "insideTopLeft",
            fill: PANEL_CHART.axis,
            fontSize: 10,
          }}
        />
        <Area
          dataKey="v"
          stroke={PANEL_CHART.accent}
          strokeWidth={1.3}
          fill={PANEL_CHART.accent}
          fillOpacity={0.14}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function EdaDistributionChart({ item }: { item: DistributionItem }) {
  const t = useI18n();
  // Log axis cannot take zeros: drop empty bins to null so recharts skips them.
  const rows = useMemo(
    () =>
      item.histogram.bins.map((bin) => ({
        x: bin.x,
        observed: bin.observed > 0 ? bin.observed : null,
        normal: bin.normal > 0 ? bin.normal : null,
      })),
    [item]
  );

  return (
    <>
      <div className="mb-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">
        <span className="flex items-center gap-2">
          <span
            className="inline-block h-2.5 w-2.5 rounded-sm"
            style={{ background: PANEL_CHART.accent }}
            aria-hidden
          />
          {t.eda.distObserved}
        </span>
        <span className="flex items-center gap-2">
          <span
            className="inline-block h-0.5 w-5 rounded border-t border-dashed"
            style={{ borderColor: PANEL_CHART.axis }}
            aria-hidden
          />
          {t.eda.distNormal}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={rows} margin={{ top: 6, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={PANEL_CHART.grid} strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="x"
            type="number"
            domain={["dataMin", "dataMax"]}
            stroke={PANEL_CHART.axis}
            tick={{ fontSize: 11 }}
            tickFormatter={(v) => `${(Number(v) * 100).toFixed(1)}%`}
          />
          <YAxis
            scale="log"
            domain={["auto", "auto"]}
            stroke={PANEL_CHART.axis}
            tick={{ fontSize: 10 }}
            width={44}
            tickFormatter={(v) => Number(v).toExponential(0)}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            labelFormatter={(v) => `${(Number(v) * 100).toFixed(2)}%`}
          />
          <Area
            dataKey="observed"
            stroke={PANEL_CHART.accent}
            strokeWidth={1.2}
            fill={PANEL_CHART.accent}
            fillOpacity={0.2}
            isAnimationActive={false}
            connectNulls
          />
          <Line
            dataKey="normal"
            dot={false}
            stroke={PANEL_CHART.axis}
            strokeWidth={1.4}
            strokeDasharray="5 3"
            isAnimationActive={false}
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>
    </>
  );
}

export function EdaSigmaTable({ item }: { item: DistributionItem }) {
  const t = useI18n();
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
          <th scope="col" className="py-2 font-medium">
            {t.eda.tailsMove}
          </th>
          <th scope="col" className="py-2 text-right font-medium">
            {t.eda.tailsExpected}
          </th>
          <th scope="col" className="py-2 text-right font-medium">
            {t.eda.tailsObserved}
          </th>
        </tr>
      </thead>
      <tbody className="divide-y divide-border">
        {item.sigma_events.map((event) => (
          <tr key={event.sigma}>
            <th scope="row" className="py-2 text-left font-normal">
              {t.eda.tailsOver} {event.sigma}σ
            </th>
            <td className="tabular py-2 text-right text-muted">
              {event.expected_normal < 0.01
                ? event.expected_normal.toExponential(0)
                : fmtNumber(event.expected_normal, 2)}
            </td>
            <td className="tabular py-2 text-right font-semibold text-negative">
              {fmtInt(event.observed)}
            </td>
          </tr>
        ))}
      </tbody>
      <tfoot>
        <tr>
          <td colSpan={3} className="pt-3 text-xs text-muted">
            {t.eda.tailsFooterPrefix} {fmtInt(item.stats.n)} {t.eda.tailsFooterSuffix}
          </td>
        </tr>
      </tfoot>
    </table>
  );
}

/** 24×7 hour-by-weekday heatmap; theme-safe accent alpha scale. */
export function EdaSeasonalityHeatmap({
  cells,
  days,
}: {
  cells: { w: number; h: number; v: number }[];
  days: string[];
}) {
  const { grid, max } = useMemo(() => {
    const grid = new Map<string, number>();
    let max = 0;
    for (const cell of cells) {
      grid.set(`${cell.w}-${cell.h}`, cell.v);
      max = Math.max(max, cell.v);
    }
    return { grid, max };
  }, [cells]);

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[560px]">
        <div className="grid grid-cols-[2.4rem_repeat(24,1fr)] gap-px">
          <div />
          {Array.from({ length: 24 }, (_, h) => (
            <div key={h} className="pb-1 text-center text-[9px] text-muted">
              {h % 3 === 0 ? h : ""}
            </div>
          ))}
          {days.map((label, d) => (
            <Fragment key={label}>
              <div className="flex items-center pr-2 text-right text-[10px] text-muted">
                {label}
              </div>
              {Array.from({ length: 24 }, (_, h) => {
                const value = grid.get(`${d + 1}-${h}`) ?? 0;
                const intensity = max > 0 ? value / max : 0;
                return (
                  <div
                    key={`${label}-${h}`}
                    title={`${label} ${String(h).padStart(2, "0")}:00 UTC · ${value.toFixed(1)} bps`}
                    className="aspect-square min-h-[13px] rounded-[2px]"
                    style={{
                      background: `rgb(45 212 191 / ${(0.07 + intensity * 0.85).toFixed(3)})`,
                    }}
                  />
                );
              })}
            </Fragment>
          ))}
        </div>
      </div>
    </div>
  );
}

export function EdaUnderwaterChart({ points }: { points: { t: number; dd: number }[] }) {
  const intl = useIntlLocale();
  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={points} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid stroke={PANEL_CHART.grid} strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="t"
          type="number"
          domain={["dataMin", "dataMax"]}
          tickFormatter={(v) =>
            new Date(Number(v) * 1000).toLocaleDateString(intl, { year: "numeric" })
          }
          stroke={PANEL_CHART.axis}
          tick={{ fontSize: 11 }}
        />
        <YAxis
          stroke={PANEL_CHART.axis}
          tick={{ fontSize: 11 }}
          width={44}
          tickFormatter={(v) => `${(Number(v) * 100).toFixed(0)}%`}
          domain={[-0.85, 0]}
        />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(value: number) => [`${(Number(value) * 100).toFixed(1)}%`, ""]}
          labelFormatter={(v) => new Date(Number(v) * 1000).toISOString().slice(0, 10)}
        />
        <Area
          dataKey="dd"
          stroke={PANEL_CHART.negative}
          strokeWidth={1.1}
          fill={PANEL_CHART.negative}
          fillOpacity={0.2}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function EdaFundingChart({ points }: { points: { t: number; r: number }[] }) {
  const intl = useIntlLocale();
  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={points} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid stroke={PANEL_CHART.grid} strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="t"
          type="number"
          domain={["dataMin", "dataMax"]}
          tickFormatter={(v) =>
            new Date(Number(v) * 1000).toLocaleDateString(intl, { year: "numeric" })
          }
          stroke={PANEL_CHART.axis}
          tick={{ fontSize: 11 }}
        />
        <YAxis
          stroke={PANEL_CHART.axis}
          tick={{ fontSize: 11 }}
          width={56}
          tickFormatter={(v) => `${(Number(v) * 100).toFixed(2)}%`}
        />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(value: number) => [`${(Number(value) * 100).toFixed(4)}%`, ""]}
          labelFormatter={(v) => new Date(Number(v) * 1000).toISOString().slice(0, 10)}
        />
        <ReferenceLine y={0} stroke={PANEL_CHART.axis} strokeDasharray="4 3" />
        <Area
          dataKey="r"
          stroke={PANEL_CHART.accent}
          strokeWidth={1.1}
          fill={PANEL_CHART.accent}
          fillOpacity={0.16}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
