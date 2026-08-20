"use client";

// Three structural properties of the market, measured on the study's own
// datasets: hour×weekday volatility seasonality, the buy-and-hold underwater
// curve, and the funding-rate series (the cost almost nobody models).

import { Fragment, useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { LANDING_CHART } from "@/components/landing/charts/palette";
import { useLandingExtra } from "@/components/landing/charts/extra";
import { tpl, useLandingCopy } from "@/components/landing/copy";
import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";
import { useIntlLocale } from "@/lib/i18n";

const yearTick = (locale: string) => (unixSeconds: number) =>
  new Date(unixSeconds * 1000).toLocaleDateString(locale, { year: "numeric" });

/** 24×7 CSS-grid heatmap; no chart library needed. */
function SeasonalityHeatmap({
  cells,
  days,
  unit,
}: {
  cells: { w: number; h: number; v: number }[];
  days: string[];
  unit: string;
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
                    title={`${label} ${String(h).padStart(2, "0")}:00 UTC · ${value.toFixed(1)} ${unit}`}
                    className="aspect-square min-h-[13px] rounded-[2px]"
                    style={{
                      background: `rgb(45 212 191 / ${(0.06 + intensity * 0.88).toFixed(3)})`,
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

export function MarketStructure() {
  const { data, error } = useLandingExtra();
  const c = useLandingCopy();
  const intl = useIntlLocale();
  if (error) return null;
  const ms = data?.market_structure;

  return (
    <Section id="estructura">
      <SectionHeading
        eyebrow={c.structure.eyebrow}
        title={c.structure.title}
        lead={c.structure.lead}
      />

      <Reveal>
        <div className="mt-14 rounded-card border border-border bg-surface p-6 md:p-7">
          <p className="rule-label mb-4 text-accent">{c.structure.seasonTitle}</p>
          {ms ? (
            <SeasonalityHeatmap
              cells={ms.seasonality}
              days={[...c.structure.days]}
              unit={c.structure.seasonUnit}
            />
          ) : (
            <div className="h-40 animate-pulse rounded-md bg-surface-2" aria-hidden />
          )}
          <p className="mt-4 text-xs leading-relaxed text-muted">{c.structure.seasonCaption}</p>
        </div>
      </Reveal>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Reveal delay={0.05}>
          <div className="rounded-card border border-border bg-surface p-6 md:p-7">
            <p className="rule-label mb-4 text-accent">{c.structure.underwaterTitle}</p>
            {ms ? (
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={ms.underwater} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid
                    stroke={LANDING_CHART.grid}
                    strokeDasharray="3 3"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="t"
                    type="number"
                    domain={["dataMin", "dataMax"]}
                    tickFormatter={yearTick(intl)}
                    stroke={LANDING_CHART.axis}
                    tick={{ fontSize: 11 }}
                  />
                  <YAxis
                    stroke={LANDING_CHART.axis}
                    tick={{ fontSize: 11 }}
                    width={44}
                    tickFormatter={(v) => `${(Number(v) * 100).toFixed(0)}%`}
                    domain={[-0.85, 0]}
                  />
                  <Tooltip
                    formatter={(value: number) => `${(Number(value) * 100).toFixed(1)}%`}
                    labelFormatter={(v) => new Date(Number(v) * 1000).toISOString().slice(0, 10)}
                    contentStyle={{
                      background: LANDING_CHART.surface,
                      border: `1px solid ${LANDING_CHART.border}`,
                    }}
                  />
                  <Area
                    dataKey="dd"
                    stroke="rgb(248 113 113)"
                    strokeWidth={1.2}
                    fill="rgb(248 113 113)"
                    fillOpacity={0.22}
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[220px] animate-pulse rounded-md bg-surface-2" aria-hidden />
            )}
            <p className="mt-4 text-xs leading-relaxed text-muted">
              {c.structure.underwaterCaption}
            </p>
            {ms && (
              <div className="mt-4 grid grid-cols-3 gap-3">
                {[
                  {
                    v: `${(ms.underwater_stats.share_below_peak * 100).toFixed(1)}%`,
                    l: c.structure.uwShare,
                  },
                  {
                    v: `${(ms.underwater_stats.max_drawdown * 100).toFixed(0)}%`,
                    l: c.structure.uwMaxDd,
                  },
                  {
                    v: ms.underwater_stats.longest_underwater_days.toLocaleString(intl),
                    l: c.structure.uwLongest,
                  },
                ].map((s) => (
                  <div key={s.l} className="rounded-md border border-border bg-surface-2 p-3">
                    <p className="tabular text-lg font-semibold">{s.v}</p>
                    <p className="mt-0.5 text-[11px] leading-snug text-muted">{s.l}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="rounded-card border border-border bg-surface p-6 md:p-7">
            <p className="rule-label mb-4 text-accent">{c.structure.fundingTitle}</p>
            {ms ? (
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={ms.funding} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid
                    stroke={LANDING_CHART.grid}
                    strokeDasharray="3 3"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="t"
                    type="number"
                    domain={["dataMin", "dataMax"]}
                    tickFormatter={yearTick(intl)}
                    stroke={LANDING_CHART.axis}
                    tick={{ fontSize: 11 }}
                  />
                  <YAxis
                    stroke={LANDING_CHART.axis}
                    tick={{ fontSize: 11 }}
                    width={52}
                    tickFormatter={(v) => `${(Number(v) * 100).toFixed(2)}%`}
                  />
                  <Tooltip
                    formatter={(value: number) => `${(Number(value) * 100).toFixed(4)}%`}
                    labelFormatter={(v) => new Date(Number(v) * 1000).toISOString().slice(0, 10)}
                    contentStyle={{
                      background: LANDING_CHART.surface,
                      border: `1px solid ${LANDING_CHART.border}`,
                    }}
                  />
                  <ReferenceLine y={0} stroke={LANDING_CHART.reference} strokeDasharray="4 3" />
                  <Area
                    dataKey="r"
                    stroke={LANDING_CHART.accent}
                    strokeWidth={1.2}
                    fill={LANDING_CHART.accent}
                    fillOpacity={0.18}
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[220px] animate-pulse rounded-md bg-surface-2" aria-hidden />
            )}
            <p className="mt-4 text-xs leading-relaxed text-muted">
              {ms
                ? tpl(c.structure.fundingCaption, {
                    n: ms.funding_stats.n_events.toLocaleString(intl),
                  })
                : ""}
            </p>
            {ms && (
              <div className="mt-4 grid grid-cols-2 gap-3">
                <div className="rounded-md border border-border bg-surface-2 p-3">
                  <p className="tabular text-lg font-semibold text-negative">
                    {`${(ms.funding_stats.annualised_mean * 100).toFixed(1)}%`}
                  </p>
                  <p className="mt-0.5 text-[11px] leading-snug text-muted">
                    {c.structure.fundingMean}
                  </p>
                </div>
                <div className="rounded-md border border-border bg-surface-2 p-3">
                  <p className="tabular text-lg font-semibold">
                    {`${(ms.funding_stats.share_positive * 100).toFixed(1)}%`}
                  </p>
                  <p className="mt-0.5 text-[11px] leading-snug text-muted">
                    {c.structure.fundingPositive}
                  </p>
                </div>
              </div>
            )}
          </div>
        </Reveal>
      </div>
    </Section>
  );
}
