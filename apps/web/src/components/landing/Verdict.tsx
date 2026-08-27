"use client";

import { tpl, useLandingCopy } from "@/components/landing/copy";
import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";
import { TEST_COUNT_LABEL, formatPct, useEvidence } from "@/lib/evidence";
import { useIntlLocale } from "@/lib/i18n";

/** A PBO meter: 0 = selection works, 0.5 = coin flip, 1 = systematically wrong. */
function PboMeter({ value, splits }: { value: number; splits: number }) {
  const c = useLandingCopy();
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return (
    <div>
      <div className="relative h-9 overflow-hidden rounded-md bg-surface-2">
        <div
          className="h-full bg-negative/80 transition-all"
          style={{ width: `${pct}%` }}
          aria-hidden
        />
        <div className="absolute inset-y-0 left-1/2 w-0.5 -translate-x-1/2 bg-fg" aria-hidden />
        <span className="tabular absolute inset-y-0 left-3 flex items-center text-sm font-semibold text-fg">
          {value.toFixed(3)}
        </span>
      </div>
      <div className="mt-2 flex justify-between text-[11px] text-muted">
        <span>{c.verdict.pbo.meterLow}</span>
        <span className="font-medium text-fg">{c.verdict.pbo.meterMid}</span>
        <span>{c.verdict.pbo.meterHigh}</span>
      </div>
      <p className="mt-3 text-xs leading-relaxed text-muted">
        {tpl(c.verdict.pbo.meterCaption, { splits })}
      </p>
    </div>
  );
}

export function Verdict() {
  const { data, error } = useEvidence();
  const c = useLandingCopy();
  const intl = useIntlLocale();

  return (
    <Section id="resultado">
      <SectionHeading
        eyebrow={c.verdict.eyebrow}
        title={
          data
            ? tpl(c.verdict.titleWithData, { n: data.study.n_families })
            : c.verdict.titleFallback
        }
        lead={c.verdict.lead}
      />

      {error && (
        <p className="mt-10 text-sm text-muted">
          {c.verdict.loadError}{" "}
          <code className="font-mono text-xs text-accent">
            uv run python scripts/export_web_evidence.py
          </code>
        </p>
      )}

      {!data && !error && (
        <div className="mt-14 h-72 animate-pulse rounded-card bg-surface" aria-hidden />
      )}

      {data && (
        <>
          <Reveal>
            <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[
                { v: String(data.study.n_families), l: c.verdict.stats.families },
                {
                  v: data.study.n_configurations.toLocaleString(intl),
                  l: c.verdict.stats.configs,
                },
                { v: String(data.study.holm_rejected), l: c.verdict.stats.survive },
                {
                  v: data.study.smallest_raw_p.toFixed(2),
                  l: tpl(c.verdict.stats.pValue, { alpha: data.study.alpha }),
                },
              ].map((s) => (
                <div key={s.l} className="rounded-card border border-border bg-surface p-6">
                  <p className="tabular text-3xl font-semibold tracking-tight text-fg">{s.v}</p>
                  <p className="mt-2 text-sm leading-relaxed text-muted">{s.l}</p>
                </div>
              ))}
            </div>
          </Reveal>

          <div className="mt-10 grid gap-6 lg:grid-cols-2">
            <Reveal delay={0.05}>
              <article className="h-full rounded-card border border-border bg-surface p-6 md:p-8">
                <p className="rule-label text-accent">{c.verdict.pbo.label}</p>
                <h3 className="mt-3 text-xl font-semibold tracking-tight">{c.verdict.pbo.title}</h3>
                <div className="mt-6">
                  <PboMeter value={data.study.pbo} splits={data.study.pbo_splits} />
                </div>
                <p className="mt-5 text-sm leading-relaxed text-muted">{c.verdict.pbo.body}</p>
              </article>
            </Reveal>

            <Reveal delay={0.1}>
              <article className="h-full rounded-card border border-border bg-surface p-6 md:p-8">
                <p className="rule-label text-accent">{c.verdict.sensitivity.label}</p>
                <h3 className="mt-3 text-xl font-semibold tracking-tight">
                  {c.verdict.sensitivity.title}
                </h3>
                <p className="mt-4 text-sm leading-relaxed text-muted">
                  {c.verdict.sensitivity.body}
                </p>
                <ul className="mt-6 space-y-3.5">
                  {(() => {
                    const maxLog = Math.max(
                      ...data.study.sensitivity.map((row) => Math.log10(Math.max(10, row.n_tests)))
                    );
                    return data.study.sensitivity.map((row) => {
                      const width = (Math.log10(Math.max(10, row.n_tests)) / maxLog) * 100;
                      return (
                        <li key={row.definition} className="text-sm">
                          <div className="flex items-baseline justify-between gap-3">
                            <span className="text-muted">
                              {TEST_COUNT_LABEL[row.definition] ?? row.definition}
                            </span>
                            <span className="tabular shrink-0 font-mono text-xs">
                              {row.n_tests.toLocaleString(intl)} {c.verdict.sensitivity.testsUnit}
                            </span>
                            <span
                              className={
                                row.any_survive
                                  ? "shrink-0 text-xs text-warn"
                                  : "shrink-0 text-xs text-muted"
                              }
                            >
                              {row.any_survive
                                ? c.verdict.sensitivity.someSurvive
                                : c.verdict.sensitivity.noneSurvive}
                            </span>
                          </div>
                          {/* Log-scaled bar: the denominator spans 13 to ~5·10^5. */}
                          <div className="mt-1.5 h-1.5 rounded-full bg-surface-2">
                            <div
                              className="h-1.5 rounded-full bg-negative/70"
                              style={{ width: `${width}%` }}
                            />
                          </div>
                        </li>
                      );
                    });
                  })()}
                </ul>
              </article>
            </Reveal>
          </div>

          <Reveal delay={0.1}>
            <div className="mt-10 overflow-hidden rounded-card border border-border bg-surface">
              <div className="border-b border-border px-6 py-5">
                <h3 className="text-lg font-semibold tracking-tight">{c.verdict.table.title}</h3>
                <p className="mt-1.5 text-sm text-muted">{c.verdict.table.subtitle}</p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-muted">
                      <th className="px-6 py-3 font-medium">{c.verdict.table.family}</th>
                      <th className="px-6 py-3 font-medium">{c.verdict.table.asset}</th>
                      <th className="px-6 py-3 text-right font-medium">{c.verdict.table.ret}</th>
                      <th className="px-6 py-3 text-right font-medium">{c.verdict.table.sharpe}</th>
                      <th className="px-6 py-3 text-right font-medium">{c.verdict.table.pValue}</th>
                      <th className="px-6 py-3 text-right font-medium">
                        {c.verdict.table.verdict}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...data.study.families]
                      .sort((a, b) => a.p_value - b.p_value)
                      .map((f) => (
                        <tr
                          key={`${f.family}-${f.symbol}`}
                          className="border-b border-border/50 last:border-0"
                        >
                          <td className="px-6 py-3 font-medium">{f.family}</td>
                          <td className="px-6 py-3 text-muted">{f.symbol.replace(/USDT$/, "")}</td>
                          <td
                            className={`tabular px-6 py-3 text-right ${
                              f.total_return >= 0 ? "text-positive" : "text-negative"
                            }`}
                          >
                            {formatPct(f.total_return, 1)}
                          </td>
                          <td className="tabular px-6 py-3 text-right text-muted">
                            {f.sharpe.toFixed(2)}
                          </td>
                          <td className="tabular px-6 py-3 text-right text-muted">
                            {f.p_value.toFixed(3)}
                          </td>
                          <td className="px-6 py-3 text-right">
                            <span className="rounded border border-negative/30 bg-negative/10 px-2 py-0.5 text-xs text-negative">
                              {c.verdict.table.rejected}
                            </span>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          </Reveal>

          <Reveal delay={0.1}>
            <div className="mt-10 rounded-card border border-warn/30 bg-warn/5 p-6 md:p-8">
              <p className="rule-label text-warn">{c.verdict.holdout.label}</p>
              <h3 className="mt-3 text-xl font-semibold tracking-tight">
                {c.verdict.holdout.title}
              </h3>
              <p className="mt-4 max-w-3xl leading-relaxed text-muted">{c.verdict.holdout.p1}</p>
              <p className="mt-4 max-w-3xl leading-relaxed text-muted">
                {c.verdict.holdout.p2Prefix}
                <strong className="font-medium text-fg">{c.verdict.holdout.p2Strong}</strong>
                {c.verdict.holdout.p2Suffix}
              </p>
              <p className="mt-5 font-mono text-xs text-warn">
                {c.verdict.holdout.statePrefix} {data.holdout_state} ·{" "}
                {c.verdict.holdout.commitPrefix} {data.study.source_commit.slice(0, 12)}
              </p>
            </div>
          </Reveal>
        </>
      )}
    </Section>
  );
}
