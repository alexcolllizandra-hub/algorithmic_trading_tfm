"use client";

import { OptimismScatter } from "@/components/landing/charts/OptimismScatter";
import { LANDING_CHART } from "@/components/landing/charts/palette";
import { useLandingCopy, type LandingCopy } from "@/components/landing/copy";
import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";
import { formatPct, formatSharpe, useEvidence } from "@/lib/evidence";

function Stat({
  value,
  label,
  tone = "default",
}: {
  value: string;
  label: string;
  tone?: "default" | "bad";
}) {
  return (
    <div className="rounded-md border border-border bg-surface-2 p-4">
      <p
        className={`tabular text-2xl font-semibold tracking-tight ${
          tone === "bad" ? "text-negative" : "text-accent"
        }`}
      >
        {value}
      </p>
      <p className="mt-1 text-xs leading-relaxed text-muted">{label}</p>
    </div>
  );
}

/** The leaked-feature experiment, as a bar per variant. */
function LeakageBars({
  rows,
  copy,
}: {
  rows: { variant: string; sharpe: number | null }[];
  copy: LandingCopy["overfitting"]["leak"]["variants"];
}) {
  const labelled: Record<string, string> = {
    "causal (trailing)": copy.causal,
    "leaky (centred)": copy.leaky,
    "leaky, orientation flipped": copy.flipped,
    "buy and hold": copy.buyAndHold,
  };
  const values = rows.map((r) => Math.abs(r.sharpe ?? 0));
  const max = Math.max(...values, 1);

  return (
    <ul className="space-y-3">
      {rows.map((row) => {
        const value = row.sharpe ?? 0;
        const leaks = row.variant.startsWith("leaky");
        const width = (Math.abs(value) / max) * 100;
        return (
          <li key={row.variant}>
            <div className="flex items-baseline justify-between gap-3 text-sm">
              <span className={leaks ? "text-negative" : "text-fg"}>
                {labelled[row.variant] ?? row.variant}
              </span>
              <span className="tabular font-mono text-xs text-muted">{formatSharpe(value)}</span>
            </div>
            <div className="mt-1.5 h-2 rounded-full bg-surface-2">
              <div
                className="h-2 rounded-full transition-all"
                style={{
                  width: `${width}%`,
                  background: leaks ? "rgb(248 113 113)" : LANDING_CHART.accent,
                }}
              />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export function Overfitting() {
  const { data, error } = useEvidence();
  const c = useLandingCopy();

  return (
    <Section id="sesgo">
      <SectionHeading
        eyebrow={c.overfitting.eyebrow}
        title={c.overfitting.title}
        lead={c.overfitting.lead}
      />

      <div className="mt-14 grid gap-10 lg:grid-cols-[1.05fr_1fr] lg:gap-14">
        <Reveal>
          <div className="rounded-card border border-border bg-surface p-6 md:p-8">
            {error && (
              <p className="text-sm text-muted">
                {c.overfitting.loadErrorPrefix}{" "}
                <code className="font-mono text-xs text-accent">
                  uv run python scripts/export_web_evidence.py
                </code>
                .
              </p>
            )}
            {!data && !error && (
              <div className="h-[380px] animate-pulse rounded-md bg-surface-2" aria-hidden />
            )}
            {data && (
              <OptimismScatter
                points={data.optimism.points}
                slope={data.optimism.slope}
                meanVal={data.optimism.mean_val}
                meanTest={data.optimism.mean_test}
              />
            )}
          </div>
        </Reveal>

        <div className="flex flex-col justify-center">
          <Reveal delay={0.05}>
            <p className="rule-label text-accent">{c.overfitting.simpleLabel}</p>
            <p className="mt-3 text-lg leading-relaxed">
              {c.overfitting.simpleLede}
              <strong className="font-semibold">{c.overfitting.simpleStrong}</strong>{" "}
              {c.overfitting.simpleAfter}
            </p>
            <p className="mt-4 leading-relaxed text-muted">{c.overfitting.scatterBody}</p>
          </Reveal>

          {data && (
            <Reveal delay={0.1}>
              <div className="mt-8 grid grid-cols-2 gap-3">
                <Stat
                  value={formatSharpe(data.optimism.mean_val)}
                  label={c.overfitting.stats.selected}
                />
                <Stat
                  value={formatSharpe(data.optimism.mean_test)}
                  label={c.overfitting.stats.after}
                  tone="bad"
                />
                <Stat
                  value={formatPct(data.optimism.share_underperforming)}
                  label={c.overfitting.stats.worsened}
                  tone="bad"
                />
                <Stat
                  value={`${(data.optimism.slope * 100).toFixed(0)}%`}
                  label={c.overfitting.stats.survives}
                  tone="bad"
                />
              </div>
            </Reveal>
          )}
        </div>
      </div>

      {/* The second failure mode: look-ahead leakage. */}
      <Reveal delay={0.1}>
        <div className="mt-16 grid gap-10 rounded-card border border-border bg-surface p-6 md:p-8 lg:grid-cols-[1fr_1.05fr] lg:gap-14">
          <div>
            <p className="rule-label text-accent">{c.overfitting.leak.label}</p>
            <h3 className="mt-3 text-2xl font-semibold tracking-tight">
              {c.overfitting.leak.title}
            </h3>
            <p className="mt-4 leading-relaxed text-muted">{c.overfitting.leak.p1}</p>
            <p className="mt-4 leading-relaxed text-muted">{c.overfitting.leak.p2}</p>
          </div>

          <div className="flex flex-col justify-center">
            {data && data.leakage.length > 0 ? (
              <>
                <LeakageBars rows={data.leakage} copy={c.overfitting.leak.variants} />
                <p className="mt-5 text-xs leading-relaxed text-muted">
                  {c.overfitting.leak.caption}
                </p>
              </>
            ) : (
              <div className="h-40 animate-pulse rounded-md bg-surface-2" aria-hidden />
            )}
          </div>
        </div>
      </Reveal>
    </Section>
  );
}
