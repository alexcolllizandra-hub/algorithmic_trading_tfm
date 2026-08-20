"use client";

// Four cuts through the study's best (and rejected) family: the seed fan,
// the histogram of every search evaluation, the per-fold test returns, and
// random search vs the genetic algorithm on identical budgets. All values
// come from committed run artifacts via the landing export (plus the
// strategy-explorer export for the per-seed curves).

import { useMemo } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ErrorBar,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { LANDING_CHART } from "@/components/landing/charts/palette";
import { useLandingExtra, useSeedFan } from "@/components/landing/charts/extra";
import { tpl, useLandingCopy } from "@/components/landing/copy";
import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";
import { useIntlLocale } from "@/lib/i18n";

function Panel({
  label,
  caption,
  children,
}: {
  label: string;
  caption: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-card border border-border bg-surface p-6 md:p-7">
      <p className="rule-label mb-4 text-accent">{label}</p>
      {children}
      <p className="mt-4 text-xs leading-relaxed text-muted">{caption}</p>
    </div>
  );
}

function SeedFanChart() {
  const { data } = useSeedFan();
  const c = useLandingCopy();

  const { rows, seedKeys, bhFinal } = useMemo(() => {
    const asset = data?.per_asset?.BTCUSDT;
    if (!asset) return { rows: [], seedKeys: [] as string[], bhFinal: null };
    const length = asset.average_curve.length;
    const rows = Array.from({ length }, (_, i) => {
      const row: Record<string, number> = { i, avg: asset.average_curve[i] };
      for (const seed of asset.seeds) {
        row[`s${seed.seed}`] = seed.curve[Math.min(i, seed.curve.length - 1)];
      }
      return row;
    });
    return {
      rows,
      seedKeys: asset.seeds.map((seed) => `s${seed.seed}`),
      bhFinal: asset.buy_and_hold?.total_return ?? null,
    };
  }, [data]);

  if (!rows.length) {
    return <div className="h-[260px] animate-pulse rounded-md bg-surface-2" aria-hidden />;
  }
  return (
    <>
      <div className="mb-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">
        <span className="flex items-center gap-2">
          <span
            className="inline-block h-0.5 w-5 rounded"
            style={{ background: LANDING_CHART.accent }}
            aria-hidden
          />
          {c.anatomy.fanAvg}
        </span>
        {bhFinal != null && (
          <span>
            {c.anatomy.fanBh}: ×{(1 + bhFinal).toFixed(2)}
          </span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={rows} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={LANDING_CHART.grid} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="i" hide />
          <YAxis
            stroke={LANDING_CHART.axis}
            tick={{ fontSize: 11 }}
            width={44}
            tickFormatter={(v) => `${Number(v).toFixed(1)}×`}
            domain={["auto", "auto"]}
          />
          <ReferenceLine y={1} stroke={LANDING_CHART.reference} strokeDasharray="4 3" />
          {seedKeys.map((key) => (
            <Line
              key={key}
              dataKey={key}
              dot={false}
              stroke={LANDING_CHART.reference}
              strokeOpacity={0.35}
              strokeWidth={1}
              isAnimationActive={false}
            />
          ))}
          <Line
            dataKey="avg"
            dot={false}
            stroke={LANDING_CHART.accent}
            strokeWidth={2.2}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </>
  );
}

export function SearchAnatomy() {
  const { data, error } = useLandingExtra();
  const c = useLandingCopy();
  const intl = useIntlLocale();
  if (error) return null;
  const mountain = data?.mountain;
  const folds = data?.folds;
  const rsga = data?.rs_ga;

  const foldRows =
    folds?.folds.map((f) => ({
      label: f.test_start.slice(0, 7),
      mean: f.mean,
      err: [f.mean - f.min, f.max - f.mean],
    })) ?? [];

  const rsgaRows =
    rsga?.families.map((f) => ({
      family: f.family.replace(/_/g, " "),
      rs: f.rs,
      ga: f.ga,
    })) ?? [];

  return (
    <Section id="anatomia">
      <SectionHeading eyebrow={c.anatomy.eyebrow} title={c.anatomy.title} lead={c.anatomy.lead} />

      <div className="mt-14 grid gap-6 lg:grid-cols-2">
        <Reveal>
          <Panel label={c.anatomy.fanTitle} caption={c.anatomy.fanCaption}>
            <SeedFanChart />
          </Panel>
        </Reveal>

        <Reveal delay={0.05}>
          <Panel
            label={c.anatomy.mountainTitle}
            caption={
              mountain
                ? tpl(c.anatomy.mountainCaption, {
                    n: mountain.n_evaluations.toLocaleString(intl),
                  })
                : ""
            }
          >
            {mountain ? (
              <>
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={mountain.bins} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                    <CartesianGrid
                      stroke={LANDING_CHART.grid}
                      strokeDasharray="3 3"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="x"
                      type="number"
                      domain={["dataMin", "dataMax"]}
                      stroke={LANDING_CHART.axis}
                      tick={{ fontSize: 11 }}
                    />
                    <YAxis hide domain={[0, 1.08]} />
                    <ReferenceLine x={0} stroke={LANDING_CHART.reference} strokeDasharray="4 3" />
                    <ReferenceLine
                      x={mountain.best}
                      stroke={LANDING_CHART.holdout}
                      strokeWidth={1.6}
                    />
                    <Area
                      type="step"
                      dataKey="d"
                      stroke={LANDING_CHART.axis}
                      strokeWidth={1.1}
                      fill={LANDING_CHART.reference}
                      fillOpacity={0.25}
                      isAnimationActive={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
                <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {[
                    {
                      v: mountain.n_evaluations.toLocaleString(intl),
                      l: c.anatomy.mountainStats.n,
                    },
                    {
                      v: `${(mountain.share_positive * 100).toFixed(0)}%`,
                      l: c.anatomy.mountainStats.positive,
                    },
                    { v: mountain.median.toFixed(2), l: c.anatomy.mountainStats.median },
                    {
                      v: `${(mountain.share_failed * 100).toFixed(0)}%`,
                      l: c.anatomy.mountainStats.failed,
                    },
                  ].map((s) => (
                    <div key={s.l} className="rounded-md border border-border bg-surface-2 p-3">
                      <p className="tabular text-base font-semibold">{s.v}</p>
                      <p className="mt-0.5 text-[10px] leading-snug text-muted">{s.l}</p>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="h-[260px] animate-pulse rounded-md bg-surface-2" aria-hidden />
            )}
          </Panel>
        </Reveal>

        <Reveal delay={0.1}>
          <Panel label={c.anatomy.foldsTitle} caption={c.anatomy.foldsCaption}>
            {folds ? (
              <>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={foldRows} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                    <CartesianGrid
                      stroke={LANDING_CHART.grid}
                      strokeDasharray="3 3"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="label"
                      stroke={LANDING_CHART.axis}
                      tick={{ fontSize: 9 }}
                      interval={1}
                    />
                    <YAxis
                      stroke={LANDING_CHART.axis}
                      tick={{ fontSize: 11 }}
                      width={44}
                      tickFormatter={(v) => `${(Number(v) * 100).toFixed(0)}%`}
                    />
                    <Tooltip
                      formatter={(value: number) => `${(Number(value) * 100).toFixed(1)}%`}
                      contentStyle={{
                        background: LANDING_CHART.surface,
                        border: `1px solid ${LANDING_CHART.border}`,
                      }}
                      cursor={{ fill: "rgb(255 255 255 / 0.03)" }}
                    />
                    <ReferenceLine y={0} stroke={LANDING_CHART.reference} />
                    <Bar dataKey="mean" isAnimationActive={false} radius={[2, 2, 0, 0]}>
                      {foldRows.map((row) => (
                        <Cell
                          key={row.label}
                          fill={row.mean >= 0 ? LANDING_CHART.accent : "rgb(248 113 113)"}
                          fillOpacity={0.85}
                        />
                      ))}
                      <ErrorBar
                        dataKey="err"
                        stroke={LANDING_CHART.axis}
                        strokeWidth={1}
                        width={3}
                      />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <div className="rounded-md border border-border bg-surface-2 p-3">
                    <p className="tabular text-base font-semibold">{folds.n_positive} / 15</p>
                    <p className="mt-0.5 text-[10px] leading-snug text-muted">
                      {c.anatomy.foldsStat1}
                    </p>
                  </div>
                  <div className="rounded-md border border-border bg-surface-2 p-3">
                    <p className="tabular text-base font-semibold">
                      {folds.top2_share_of_gains != null
                        ? `${(folds.top2_share_of_gains * 100).toFixed(0)}%`
                        : "—"}
                    </p>
                    <p className="mt-0.5 text-[10px] leading-snug text-muted">
                      {c.anatomy.foldsStat2}
                    </p>
                  </div>
                </div>
              </>
            ) : (
              <div className="h-[260px] animate-pulse rounded-md bg-surface-2" aria-hidden />
            )}
          </Panel>
        </Reveal>

        <Reveal delay={0.15}>
          <Panel label={c.anatomy.rsgaTitle} caption={c.anatomy.rsgaCaption}>
            {rsga ? (
              <>
                <div className="mb-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">
                  <span className="flex items-center gap-2">
                    <span
                      className="inline-block h-2.5 w-2.5 rounded-sm"
                      style={{ background: LANDING_CHART.accent }}
                      aria-hidden
                    />
                    {c.anatomy.rs}
                  </span>
                  <span className="flex items-center gap-2">
                    <span
                      className="inline-block h-2.5 w-2.5 rounded-sm"
                      style={{ background: LANDING_CHART.secondary }}
                      aria-hidden
                    />
                    {c.anatomy.ga}
                  </span>
                </div>
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart
                    data={rsgaRows}
                    layout="vertical"
                    margin={{ top: 4, right: 12, bottom: 0, left: 8 }}
                    barGap={2}
                  >
                    <CartesianGrid
                      stroke={LANDING_CHART.grid}
                      strokeDasharray="3 3"
                      horizontal={false}
                    />
                    <XAxis
                      type="number"
                      stroke={LANDING_CHART.axis}
                      tick={{ fontSize: 11 }}
                      domain={["auto", 0.2]}
                    />
                    <YAxis
                      type="category"
                      dataKey="family"
                      stroke={LANDING_CHART.axis}
                      tick={{ fontSize: 10 }}
                      width={130}
                    />
                    <Tooltip
                      formatter={(value: number) => Number(value).toFixed(2)}
                      contentStyle={{
                        background: LANDING_CHART.surface,
                        border: `1px solid ${LANDING_CHART.border}`,
                      }}
                      cursor={{ fill: "rgb(255 255 255 / 0.03)" }}
                    />
                    <ReferenceLine x={0} stroke={LANDING_CHART.reference} />
                    <Bar
                      dataKey="rs"
                      name={c.anatomy.rs}
                      fill={LANDING_CHART.accent}
                      isAnimationActive={false}
                      radius={[0, 2, 2, 0]}
                    />
                    <Bar
                      dataKey="ga"
                      name={c.anatomy.ga}
                      fill={LANDING_CHART.secondary}
                      fillOpacity={0.8}
                      isAnimationActive={false}
                      radius={[0, 2, 2, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </>
            ) : (
              <div className="h-[260px] animate-pulse rounded-md bg-surface-2" aria-hidden />
            )}
          </Panel>
        </Reveal>
      </div>
    </Section>
  );
}
