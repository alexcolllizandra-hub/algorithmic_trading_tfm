"use client";

// The thesis-summary picture, landing edition: the study's best (and
// rejected) strategy overlaid on the distribution of a thousand versions of
// itself with the positions rotated at random. Reproduces notebook 07's
// figure k03 from the same seed, via the landing_extra export.

import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";

import { LANDING_CHART } from "@/components/landing/charts/palette";
import { useLandingExtra } from "@/components/landing/charts/extra";
import { tpl, useLandingCopy } from "@/components/landing/copy";
import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";
import { useIntlLocale } from "@/lib/i18n";

export function NullDistribution() {
  const { data, error } = useLandingExtra();
  const c = useLandingCopy();
  const intl = useIntlLocale();
  if (error) return null;
  const nd = data?.null_distribution;

  return (
    <Section id="azar">
      <SectionHeading
        eyebrow={c.nullDist.eyebrow}
        title={c.nullDist.title}
        lead={c.nullDist.lead}
      />

      <Reveal>
        <div className="mt-14 rounded-card border border-border bg-surface p-6 md:p-7">
          {nd ? (
            <ResponsiveContainer width="100%" height={320}>
              <AreaChart data={nd.bins} margin={{ top: 8, right: 12, bottom: 24, left: 4 }}>
                <CartesianGrid stroke={LANDING_CHART.grid} strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="x"
                  type="number"
                  domain={["dataMin", "dataMax"]}
                  stroke={LANDING_CHART.axis}
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v) => `${(Number(v) * 100).toFixed(0)}%`}
                  label={{
                    value: c.nullDist.xAxisLabel,
                    position: "insideBottom",
                    offset: -14,
                    fill: LANDING_CHART.axis,
                    fontSize: 11,
                  }}
                />
                <YAxis hide domain={[0, 1.08]} />
                <ReferenceArea
                  x1={nd.band[0]}
                  x2={nd.band[1]}
                  fill={LANDING_CHART.reference}
                  fillOpacity={0.09}
                />
                <Area
                  type="step"
                  dataKey="d"
                  stroke={LANDING_CHART.axis}
                  strokeWidth={1.2}
                  fill={LANDING_CHART.reference}
                  fillOpacity={0.25}
                  isAnimationActive={false}
                />
                {nd.real_seeds.map((value, i) => (
                  <ReferenceLine
                    key={i}
                    x={value}
                    stroke={LANDING_CHART.accent}
                    strokeWidth={1.8}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[320px] animate-pulse rounded-md bg-surface-2" aria-hidden />
          )}
          <p className="mt-4 text-xs leading-relaxed text-muted">
            {nd
              ? tpl(c.nullDist.caption, {
                  family: nd.family,
                  symbol: nd.symbol.replace("USDT", ""),
                  rotations: nd.n_rotations.toLocaleString(intl),
                })
              : ""}
          </p>
        </div>
      </Reveal>

      <Reveal delay={0.08}>
        <div className="mt-10 grid gap-6 lg:grid-cols-[1fr_1.1fr] lg:gap-14">
          <div className="grid grid-cols-2 gap-3 self-start">
            <div className="rounded-md border border-border bg-surface-2 p-4">
              <p className="tabular text-2xl font-semibold tracking-tight">10 / 10</p>
              <p className="mt-1 text-xs leading-relaxed text-muted">{c.nullDist.statInside}</p>
            </div>
            <div className="rounded-md border border-border bg-surface-2 p-4">
              <p className="tabular text-2xl font-semibold tracking-tight">
                {intl.startsWith("es") ? "0,22 – 0,97" : "0.22 – 0.97"}
              </p>
              <p className="mt-1 text-xs leading-relaxed text-muted">
                {c.nullDist.statPercentiles}
              </p>
            </div>
          </div>
          <div className="flex flex-col justify-center">
            <p className="rule-label text-accent">{c.nullDist.simpleLabel}</p>
            <p className="mt-3 text-lg leading-relaxed">
              {c.nullDist.simpleLede}
              <strong className="font-semibold">{c.nullDist.simpleStrong}</strong>
            </p>
            <p className="mt-4 leading-relaxed text-muted">{c.nullDist.body}</p>
          </div>
        </div>
      </Reveal>
    </Section>
  );
}
