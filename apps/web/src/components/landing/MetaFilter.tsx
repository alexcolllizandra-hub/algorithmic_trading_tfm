"use client";

// The real-data meta-labeling result (RQ3), read honestly: the ML filter
// improves the outcome through abstention, with chance-level predictive
// power. Numbers come straight from reports/meta_labeling_real via the
// landing export.

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
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

export function MetaFilter() {
  const { data, error } = useLandingExtra();
  const c = useLandingCopy();
  const intl = useIntlLocale();
  if (error) return null;
  const meta = data?.meta;

  const rows = meta
    ? [
        { label: c.mlfilter.barPrimary, value: meta.primary_total_return },
        { label: c.mlfilter.barMeta, value: meta.meta_total_return },
      ]
    : [];

  return (
    <Section id="ml">
      <SectionHeading
        eyebrow={c.mlfilter.eyebrow}
        title={c.mlfilter.title}
        lead={c.mlfilter.lead}
      />

      <div className="mt-14 grid gap-6 lg:grid-cols-[1fr_1.15fr]">
        <Reveal>
          <div className="rounded-card border border-border bg-surface p-6 md:p-7">
            {meta ? (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: 4 }}>
                  <CartesianGrid
                    stroke={LANDING_CHART.grid}
                    strokeDasharray="3 3"
                    vertical={false}
                  />
                  <XAxis dataKey="label" stroke={LANDING_CHART.axis} tick={{ fontSize: 12 }} />
                  <YAxis
                    stroke={LANDING_CHART.axis}
                    tick={{ fontSize: 11 }}
                    width={48}
                    tickFormatter={(v) => `${(Number(v) * 100).toFixed(0)}%`}
                    domain={[-0.36, 0.05]}
                  />
                  <ReferenceLine y={0} stroke={LANDING_CHART.reference} />
                  <Bar
                    dataKey="value"
                    isAnimationActive={false}
                    radius={[3, 3, 0, 0]}
                    maxBarSize={110}
                  >
                    {rows.map((row) => (
                      <Cell
                        key={row.label}
                        fill={row.value >= 0 ? LANDING_CHART.accent : "rgb(248 113 113)"}
                        fillOpacity={0.85}
                      />
                    ))}
                    <LabelList
                      dataKey="value"
                      position="top"
                      formatter={(v: number) => `${(v * 100).toFixed(1)}%`}
                      style={{ fill: LANDING_CHART.axis, fontSize: 12 }}
                    />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[260px] animate-pulse rounded-md bg-surface-2" aria-hidden />
            )}
            <p className="mt-4 text-xs leading-relaxed text-muted">
              {meta
                ? tpl(c.mlfilter.caption, {
                    family: meta.family,
                    symbol: meta.symbol.replace("USDT", ""),
                    n: meta.n_events.toLocaleString(intl),
                  })
                : ""}
            </p>
          </div>
        </Reveal>

        <Reveal delay={0.06}>
          <div className="flex h-full flex-col justify-center gap-4">
            {meta && (
              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-md border border-border bg-surface-2 p-4">
                  <p className="tabular text-2xl font-semibold tracking-tight">
                    {meta.median_roc_auc.toFixed(2)}
                  </p>
                  <p className="mt-1 text-xs leading-relaxed text-muted">{c.mlfilter.roc}</p>
                </div>
                <div className="rounded-md border border-border bg-surface-2 p-4">
                  <p className="tabular text-2xl font-semibold tracking-tight">
                    {`${(meta.abstention_rate * 100).toFixed(0)}%`}
                  </p>
                  <p className="mt-1 text-xs leading-relaxed text-muted">{c.mlfilter.abst}</p>
                </div>
                <div className="rounded-md border border-border bg-surface-2 p-4">
                  <p className="tabular text-2xl font-semibold tracking-tight">
                    {meta.folds_profitable} / {meta.n_folds}
                  </p>
                  <p className="mt-1 text-xs leading-relaxed text-muted">{c.mlfilter.folds}</p>
                </div>
              </div>
            )}
            <p className="leading-relaxed text-muted">{c.mlfilter.body}</p>
          </div>
        </Reveal>
      </div>
    </Section>
  );
}
