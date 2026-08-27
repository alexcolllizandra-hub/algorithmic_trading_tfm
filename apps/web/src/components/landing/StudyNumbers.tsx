"use client";

// The whole study as eight counters. Sources: evidence.json (closure
// families, configurations, denominator sensitivity, survivors) and the
// landing export's totals/null blocks (runs, candles, registered families,
// rotations). Nothing hard-coded.

import { useLandingExtra } from "@/components/landing/charts/extra";
import { useLandingCopy } from "@/components/landing/copy";
import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";
import { useEvidence } from "@/lib/evidence";
import { useIntlLocale } from "@/lib/i18n";

export function StudyNumbers() {
  const { data: extra } = useLandingExtra();
  const { data: evidence } = useEvidence();
  const c = useLandingCopy();
  const intl = useIntlLocale();

  if (!extra?.totals || !evidence) return null;

  const maxTests = Math.max(...evidence.study.sensitivity.map((row) => row.n_tests));
  const tiles = [
    { v: extra.totals.bars_total.toLocaleString(intl), l: c.numbers.bars },
    { v: extra.totals.runs_total.toLocaleString(intl), l: c.numbers.runs },
    { v: String(extra.totals.families_registered), l: c.numbers.familiesRegistered },
    { v: String(evidence.study.n_families), l: c.numbers.familiesClosure },
    { v: extra.mountain.n_evaluations.toLocaleString(intl), l: c.numbers.configs },
    { v: extra.null_distribution.n_rotations.toLocaleString(intl), l: c.numbers.rotations },
    { v: maxTests.toLocaleString(intl), l: c.numbers.maxTests },
    { v: String(evidence.study.holm_rejected), l: c.numbers.promoted, accent: true },
  ];

  return (
    <Section id="cifras">
      <SectionHeading eyebrow={c.numbers.eyebrow} title={c.numbers.title} lead={c.numbers.lead} />

      <Reveal>
        <div className="mt-14 grid grid-cols-2 gap-3 md:grid-cols-4">
          {tiles.map((tile) => (
            <div
              key={tile.l}
              className={`rounded-card border p-6 ${
                tile.accent ? "border-accent/40 bg-accent/5" : "border-border bg-surface"
              }`}
            >
              <p
                className={`tabular text-3xl font-semibold tracking-tight ${
                  tile.accent ? "text-accent" : "text-fg"
                }`}
              >
                {tile.v}
              </p>
              <p className="mt-2 text-sm leading-snug text-muted">{tile.l}</p>
            </div>
          ))}
        </div>
      </Reveal>
    </Section>
  );
}
