"use client";

import { useLandingCopy } from "@/components/landing/copy";
import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";

export function PlainExplanation() {
  const c = useLandingCopy();

  return (
    <Section id="marco">
      <SectionHeading eyebrow={c.plain.eyebrow} title={c.plain.title} lead={c.plain.lead} />

      <div className="mt-14 grid gap-px overflow-hidden rounded-card border border-border bg-border md:grid-cols-3">
        {c.plain.steps.map((step, index) => (
          <Reveal key={step.n} delay={index * 0.08} className="bg-bg">
            <article className="flex h-full flex-col gap-4 p-7 md:p-8">
              <span className="rule-label text-accent">{step.n}</span>
              <h3 className="text-xl font-semibold tracking-tight">{step.title}</h3>
              <p className="text-pretty leading-relaxed text-muted">{step.body}</p>
            </article>
          </Reveal>
        ))}
      </div>

      <Reveal delay={0.1}>
        <blockquote className="mt-12 border-l-2 border-accent pl-6 text-lg leading-relaxed text-fg md:text-xl">
          {c.plain.quote}
          <footer className="mt-3 text-sm text-muted">{c.plain.quoteFooter}</footer>
        </blockquote>
      </Reveal>
    </Section>
  );
}
