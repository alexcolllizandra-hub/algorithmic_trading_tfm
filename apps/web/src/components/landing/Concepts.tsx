"use client";

import { useLandingCopy } from "@/components/landing/copy";
import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";

// The measured-evidence anchor for the concepts that have one, keyed by index
// in the copy dictionary (market efficiency → the cost-erosion section).
const EVIDENCE_HREF: Record<number, string> = { 1: "#costes" };

export function Concepts() {
  const c = useLandingCopy();

  return (
    <Section id="conceptos">
      <SectionHeading
        eyebrow={c.concepts.eyebrow}
        title={c.concepts.title}
        lead={c.concepts.lead}
      />

      <div className="mt-14 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {c.concepts.items.map((concept, index) => (
          <Reveal key={concept.title} delay={index * 0.05}>
            <article className="flex h-full flex-col rounded-card border border-border bg-surface p-7 transition-colors hover:border-accent/40">
              <h3 className="text-lg font-semibold tracking-tight">{concept.title}</h3>

              <p className="mt-4 text-sm leading-relaxed text-muted">{concept.technical}</p>

              <div className="mt-5 rounded-md border border-border bg-surface-2 p-4">
                <p className="rule-label mb-2 text-accent">{c.concepts.everydayLabel}</p>
                <p className="text-sm leading-relaxed text-fg/90">{concept.everyday}</p>
              </div>

              <p className="mt-auto pt-5 text-sm font-medium text-fg">{concept.punchline}</p>

              {EVIDENCE_HREF[index] && (
                <a
                  href={EVIDENCE_HREF[index]}
                  className="mt-3 inline-flex items-center gap-1.5 text-sm text-accent underline-offset-4 hover:underline"
                >
                  {c.concepts.seeMeasured}
                  <span aria-hidden>{"↓"}</span>
                </a>
              )}
            </article>
          </Reveal>
        ))}
      </div>
    </Section>
  );
}
