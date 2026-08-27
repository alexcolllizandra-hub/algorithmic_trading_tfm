"use client";

// Every hypothesis the study tested, drawn together. The chart is the
// denominator made visible: publishing only the best curve and hiding the
// other fourteen is exactly the selection bias the study measures.

import { useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { LANDING_CHART } from "@/components/landing/charts/palette";
import { useLandingExtra } from "@/components/landing/charts/extra";
import { useLandingCopy, type LandingCopy } from "@/components/landing/copy";
import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";

function ZooTooltip({
  active,
  payload,
  copy,
}: {
  active?: boolean;
  payload?: { dataKey?: string; value?: number }[];
  copy: LandingCopy["zoo"];
}) {
  if (!active || !payload?.length) return null;
  const sorted = [...payload].sort((a, b) => (b.value ?? 0) - (a.value ?? 0));
  return (
    <div className="rounded-md border border-border bg-surface-2 px-3 py-2 text-xs">
      <p className="font-medium">
        {sorted.length} {copy.tooltipFamilies}
      </p>
      <p className="tabular mt-0.5 text-muted">
        {copy.tooltipBest} {Number(sorted[0]?.value).toFixed(2)}× · {copy.tooltipWorst}{" "}
        {Number(sorted[sorted.length - 1]?.value).toFixed(2)}×
      </p>
    </div>
  );
}

export function FamilyZoo() {
  const { data, error } = useLandingExtra();
  const c = useLandingCopy();

  const { rows, stats } = useMemo(() => {
    if (!data) return { rows: [], stats: null };
    const families = data.families;
    const length = Math.max(...families.map((f) => f.curve.length));
    const merged = Array.from({ length }, (_, i) => {
      const row: Record<string, number> = { i };
      for (const f of families) {
        row[f.family] = f.curve[Math.min(i, f.curve.length - 1)];
      }
      return row;
    });
    const finals = families.map((f) => ({
      family: f.family,
      value: f.curve[f.curve.length - 1],
    }));
    const sorted = [...finals].sort((a, b) => a.value - b.value);
    return {
      rows: merged,
      stats: {
        n: families.length,
        worst: sorted[0],
        best: sorted[sorted.length - 1],
        positive: finals.filter((f) => f.value > 1).length,
      },
    };
  }, [data]);

  if (error) return null;

  const lineStyle = (family: string) => {
    if (stats && family === stats.best.family) {
      return { stroke: LANDING_CHART.accent, strokeOpacity: 1, strokeWidth: 2 };
    }
    if (stats && family === stats.worst.family) {
      return { stroke: LANDING_CHART.holdout, strokeOpacity: 0.95, strokeWidth: 2 };
    }
    return { stroke: LANDING_CHART.reference, strokeOpacity: 0.3, strokeWidth: 1.2 };
  };

  return (
    <Section id="familias">
      <SectionHeading eyebrow={c.zoo.eyebrow} title={c.zoo.title} lead={c.zoo.lead} />

      <Reveal>
        <div className="mt-14 rounded-card border border-border bg-surface p-6 md:p-7">
          {data && stats ? (
            <>
              <div className="mb-4 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-xs text-muted">
                <span className="flex items-center gap-2">
                  <span
                    className="inline-block h-0.5 w-5 rounded"
                    style={{ background: LANDING_CHART.accent }}
                    aria-hidden
                  />
                  {c.zoo.bestLabel} · {stats.best.family}
                </span>
                <span className="flex items-center gap-2">
                  <span
                    className="inline-block h-0.5 w-5 rounded"
                    style={{ background: LANDING_CHART.holdout }}
                    aria-hidden
                  />
                  {c.zoo.worstLabel} · {stats.worst.family}
                </span>
                <span className="flex items-center gap-2">
                  <span
                    className="inline-block h-0.5 w-5 rounded opacity-40"
                    style={{ background: LANDING_CHART.reference }}
                    aria-hidden
                  />
                  {stats.n - 2} {c.zoo.othersLabel}
                </span>
              </div>
              <ResponsiveContainer width="100%" height={340}>
                <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 8, left: 4 }}>
                  <CartesianGrid
                    stroke={LANDING_CHART.grid}
                    strokeDasharray="3 3"
                    vertical={false}
                  />
                  <XAxis dataKey="i" hide />
                  <YAxis
                    stroke={LANDING_CHART.axis}
                    tick={{ fontSize: 11 }}
                    width={44}
                    tickFormatter={(v) => `${Number(v).toFixed(1)}×`}
                    domain={["auto", "auto"]}
                  />
                  <Tooltip content={<ZooTooltip copy={c.zoo} />} />
                  <ReferenceLine
                    y={1}
                    stroke={LANDING_CHART.reference}
                    strokeDasharray="4 3"
                    label={{
                      value: c.zoo.startLine,
                      position: "insideBottomLeft",
                      fill: LANDING_CHART.axis,
                      fontSize: 10,
                    }}
                  />
                  {data.families.map((f) => (
                    <Line
                      key={f.family}
                      type="monotone"
                      dataKey={f.family}
                      dot={false}
                      isAnimationActive={false}
                      {...lineStyle(f.family)}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </>
          ) : (
            <div className="h-[340px] animate-pulse rounded-md bg-surface-2" aria-hidden />
          )}
          <p className="mt-4 text-xs leading-relaxed text-muted">{c.zoo.caption}</p>
        </div>
      </Reveal>

      {stats && (
        <Reveal delay={0.05}>
          <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { v: String(stats.n), l: c.zoo.stats.n },
              { v: `${stats.positive}/${stats.n}`, l: c.zoo.stats.positive },
              {
                v: `${stats.best.value.toFixed(2)}×`,
                l: `${c.zoo.stats.best} (${stats.best.family})`,
              },
              {
                v: `${stats.worst.value.toFixed(2)}×`,
                l: `${c.zoo.stats.worst} (${stats.worst.family})`,
              },
            ].map((s) => (
              <div key={s.l} className="rounded-md border border-border bg-surface-2 p-4">
                <p className="tabular text-2xl font-semibold tracking-tight">{s.v}</p>
                <p className="mt-1 text-xs leading-relaxed text-muted">{s.l}</p>
              </div>
            ))}
          </div>
        </Reveal>
      )}

      <Reveal delay={0.1}>
        <p className="mt-8 max-w-3xl leading-relaxed text-muted">
          {c.zoo.closing}{" "}
          <a href="/estrategias" className="font-medium text-accent hover:underline">
            {c.zoo.exploreLink}
          </a>
        </p>
      </Reveal>
    </Section>
  );
}
