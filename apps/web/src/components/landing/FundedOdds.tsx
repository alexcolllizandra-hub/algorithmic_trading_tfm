"use client";

// Funded-account evaluations, priced honestly: the study's best (rejected)
// strategy against a fair coin with the same trade timing and costs, under
// the published rules of two real crypto prop firms. Numbers from notebook
// 07's table; rule sources and retrieval date live in the export.
//
// Two small-multiple panels (phase 1 / both phases) instead of one crowded
// grouped chart: each panel compares only the two arms that answer its
// question.

import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { LANDING_CHART } from "@/components/landing/charts/palette";
import { useLandingExtra } from "@/components/landing/charts/extra";
import { tpl, useLandingCopy, type LandingCopy } from "@/components/landing/copy";
import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";
import { useIntlLocale } from "@/lib/i18n";

const FIRM_LABEL: Record<string, string> = {
  breakout_1step_classic: "Breakout · 1-step",
  hyrotrader_2step: "HyroTrader · 2-step",
};

function OddsTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { name?: string; value?: number }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border border-border bg-surface-2 px-3 py-2 text-xs">
      <p className="font-medium">{label}</p>
      {payload.map((entry) => (
        <p key={entry.name} className="tabular mt-0.5 text-muted">
          {entry.name}: {((entry.value ?? 0) * 100).toFixed(1)}%
        </p>
      ))}
    </div>
  );
}

function OddsPanel({
  title,
  rows,
  max,
  copy,
}: {
  title: string;
  rows: { firm: string; strategy: number; coin: number }[];
  max: number;
  copy: LandingCopy["funded"];
}) {
  return (
    <div className="rounded-md border border-border bg-surface-2/50 p-4">
      <p className="rule-label mb-3 text-muted">{title}</p>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={rows} margin={{ top: 18, right: 8, bottom: 0, left: 0 }} barGap={6}>
          <CartesianGrid stroke={LANDING_CHART.grid} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="firm" stroke={LANDING_CHART.axis} tick={{ fontSize: 11 }} />
          <YAxis
            stroke={LANDING_CHART.axis}
            tick={{ fontSize: 11 }}
            width={40}
            tickFormatter={(v) => `${(Number(v) * 100).toFixed(0)}%`}
            domain={[0, max]}
          />
          <Tooltip content={<OddsTooltip />} cursor={{ fill: "rgb(255 255 255 / 0.03)" }} />
          <Bar
            dataKey="strategy"
            name={copy.armStrategy}
            fill={LANDING_CHART.accent}
            isAnimationActive={false}
            radius={[3, 3, 0, 0]}
          >
            <LabelList
              dataKey="strategy"
              position="top"
              formatter={(v: number) => `${(v * 100).toFixed(1)}%`}
              style={{ fill: LANDING_CHART.accent, fontSize: 11 }}
            />
          </Bar>
          <Bar
            dataKey="coin"
            name={copy.armCoin}
            fill={LANDING_CHART.reference}
            fillOpacity={0.6}
            isAnimationActive={false}
            radius={[3, 3, 0, 0]}
          >
            <LabelList
              dataKey="coin"
              position="top"
              formatter={(v: number) => `${(v * 100).toFixed(1)}%`}
              style={{ fill: LANDING_CHART.axis, fontSize: 11 }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function FundedOdds() {
  const { data, error } = useLandingExtra();
  const c = useLandingCopy();
  const intl = useIntlLocale();
  if (error) return null;
  const funded = data?.funded;

  const phase1 =
    funded?.firms.map((firm) => ({
      firm: FIRM_LABEL[firm.id] ?? firm.id,
      strategy: firm.strategy_phase1,
      coin: firm.coin_flip_phase1,
    })) ?? [];
  const both =
    funded?.firms.map((firm) => ({
      firm: FIRM_LABEL[firm.id] ?? firm.id,
      strategy: firm.strategy_both,
      coin: firm.coin_flip_both,
    })) ?? [];

  return (
    <Section id="fondeadas">
      <SectionHeading eyebrow={c.funded.eyebrow} title={c.funded.title} lead={c.funded.lead} />

      <div className="mt-14 grid gap-6 lg:grid-cols-[1.25fr_1fr]">
        <Reveal>
          <div className="rounded-card border border-border bg-surface p-6 md:p-7">
            {funded ? (
              <>
                <div className="mb-4 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-xs text-muted">
                  <span className="flex items-center gap-2">
                    <span
                      className="inline-block h-2.5 w-2.5 rounded-sm"
                      style={{ background: LANDING_CHART.accent }}
                      aria-hidden
                    />
                    {c.funded.armStrategy}
                  </span>
                  <span className="flex items-center gap-2">
                    <span
                      className="inline-block h-2.5 w-2.5 rounded-sm opacity-60"
                      style={{ background: LANDING_CHART.reference }}
                      aria-hidden
                    />
                    {c.funded.armCoin}
                  </span>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <OddsPanel
                    title={c.funded.phase1Title}
                    rows={phase1}
                    max={0.22}
                    copy={c.funded}
                  />
                  <OddsPanel title={c.funded.bothTitle} rows={both} max={0.22} copy={c.funded} />
                </div>
              </>
            ) : (
              <div className="h-[280px] animate-pulse rounded-md bg-surface-2" aria-hidden />
            )}
            <p className="mt-4 text-xs leading-relaxed text-muted">
              {funded ? tpl(c.funded.caption, { paths: funded.n_paths.toLocaleString(intl) }) : ""}
            </p>
          </div>
        </Reveal>

        <Reveal delay={0.06}>
          <div className="flex h-full flex-col justify-center rounded-card border border-border bg-surface p-6 md:p-8">
            <p className="rule-label text-accent">{c.funded.simpleLabel}</p>
            <p className="mt-3 text-lg leading-relaxed">
              {c.funded.simpleLede}
              <strong className="font-semibold">{c.funded.simpleStrong}</strong>
            </p>
            <p className="mt-4 leading-relaxed text-muted">{c.funded.body}</p>
            <p className="mt-4 text-sm leading-relaxed text-muted">{c.funded.footnote}</p>
          </div>
        </Reveal>
      </div>
    </Section>
  );
}
