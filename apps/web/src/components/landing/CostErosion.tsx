"use client";

// Market efficiency, tested with the study's own numbers. Both series ship in
// evidence.json; this section renders them.

import {
  breakEvenBps,
  CostErosionChart,
  TurnoverWedgeChart,
} from "@/components/landing/charts/CostErosion";
import { LANDING_CHART } from "@/components/landing/charts/palette";
import { useLandingCopy } from "@/components/landing/copy";
import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";
import { formatSharpe, useEvidence } from "@/lib/evidence";

function Panel({
  label,
  title,
  caption,
  children,
}: {
  label: string;
  title: string;
  caption: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-card border border-border bg-surface p-6 md:p-7">
      <p className="rule-label text-accent">{label}</p>
      <h3 className="mt-2.5 text-lg font-semibold tracking-tight">{title}</h3>
      <div className="mt-6">{children}</div>
      <p className="mt-4 text-xs leading-relaxed text-muted">{caption}</p>
    </div>
  );
}

export function CostErosion() {
  const { data, error } = useEvidence();
  const c = useLandingCopy();

  if (error) return null;

  const crossing = data ? breakEvenBps(data.cost_sensitivity) : null;
  const buyAndHold = data?.turnover.buy_and_hold_sharpe ?? null;

  return (
    <Section id="costes">
      <SectionHeading eyebrow={c.costs.eyebrow} title={c.costs.title} lead={c.costs.lead} />

      <div className="mt-14 grid gap-6 lg:grid-cols-2">
        <Reveal>
          <Panel
            label={c.costs.panels.erosionLabel}
            title={c.costs.panels.erosionTitle}
            caption={c.costs.panels.erosionCaption}
          >
            {data ? (
              <CostErosionChart rows={data.cost_sensitivity} />
            ) : (
              <div className="h-[280px] animate-pulse rounded-md bg-surface-2" aria-hidden />
            )}
          </Panel>
        </Reveal>

        <Reveal delay={0.05}>
          <Panel
            label={c.costs.panels.wedgeLabel}
            title={c.costs.panels.wedgeTitle}
            caption={c.costs.panels.wedgeCaption}
          >
            {data ? (
              <TurnoverWedgeChart grid={data.turnover.grid} />
            ) : (
              <div className="h-[280px] animate-pulse rounded-md bg-surface-2" aria-hidden />
            )}
          </Panel>
        </Reveal>
      </div>

      {data && (
        <Reveal delay={0.1}>
          <div className="mt-10 grid gap-6 lg:grid-cols-[1fr_1.15fr] lg:gap-14">
            <div className="grid grid-cols-2 gap-3 self-start">
              <div className="rounded-md border border-border bg-surface-2 p-4">
                <p className="tabular text-2xl font-semibold tracking-tight text-negative">
                  {crossing != null ? `${crossing.toFixed(0)} bps` : "—"}
                </p>
                <p className="mt-1 text-xs leading-relaxed text-muted">{c.costs.statCrossing}</p>
              </div>
              <div className="rounded-md border border-border bg-surface-2 p-4">
                <p className="tabular text-2xl font-semibold tracking-tight text-accent">
                  {formatSharpe(buyAndHold)}
                </p>
                <p className="mt-1 text-xs leading-relaxed text-muted">{c.costs.statBuyHold}</p>
              </div>
            </div>

            <div className="flex flex-col justify-center">
              <p className="rule-label text-accent">{c.costs.simpleLabel}</p>
              <p className="mt-3 text-lg leading-relaxed">
                {c.costs.simpleLede}
                <strong className="font-semibold">{c.costs.simpleStrong}</strong>
              </p>
              <p className="mt-4 leading-relaxed text-muted">
                {c.costs.body1Prefix}
                {crossing != null
                  ? `${crossing.toFixed(0)} ${c.costs.bpsUnit}`
                  : c.costs.body1Fallback}
                {c.costs.body1Suffix}
              </p>
              <p className="mt-4 leading-relaxed text-muted">
                {c.costs.body2}
                <span className="font-medium" style={{ color: LANDING_CHART.accent }}>
                  {c.costs.body2Accent}
                </span>
              </p>
            </div>
          </div>
        </Reveal>
      )}
    </Section>
  );
}
