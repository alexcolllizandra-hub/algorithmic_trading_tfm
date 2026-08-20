"use client";

import type { PhaseStatus } from "@/components/landing/content";
import { useLandingCopy } from "@/components/landing/copy";
import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";
import { StatusPill } from "@/components/landing/StatusPill";

const STEP_TONE: Record<string, string> = {
  done: "bg-positive",
  "in-review": "bg-accent",
  blocked: "bg-warn",
  planned: "bg-border",
};

/** Horizontal metro line: one node per phase, coloured by real status. */
function PhaseStepper() {
  const c = useLandingCopy();
  const phases = c.roadmap.phases;
  const count = (status: string) => phases.filter((p) => p.status === status).length;

  return (
    <div className="mt-10 rounded-card border border-border bg-surface p-6 md:p-7">
      <div role="img" aria-label={c.roadmap.stepperAria} className="flex items-center">
        {phases.map((phase, index) => (
          <div key={phase.id} className="flex min-w-0 flex-1 items-center last:flex-none">
            <div className="flex min-w-0 flex-col items-center gap-2">
              <span
                className={`h-3.5 w-3.5 shrink-0 rounded-full ring-4 ring-bg ${
                  STEP_TONE[phase.status] ?? "bg-border"
                }`}
                title={`${phase.period} · ${phase.title}`}
              />
              <span className="hidden max-w-[7.5rem] truncate text-center text-[10px] leading-tight text-muted md:block">
                {phase.period}
              </span>
            </div>
            {index < phases.length - 1 && (
              <span
                className={`mx-1 mt-[7px] h-px flex-1 self-start md:mt-[7px] ${
                  phase.status === "done" ? "bg-positive/50" : "bg-border"
                }`}
                aria-hidden
              />
            )}
          </div>
        ))}
      </div>
      <div className="mt-5 flex flex-wrap gap-x-6 gap-y-1.5 text-xs text-muted">
        <span className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-positive" aria-hidden />
          {count("done")} {c.roadmap.stepperDone}
        </span>
        <span className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-accent" aria-hidden />
          {count("in-review")} {c.roadmap.stepperReview}
        </span>
        <span className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-border" aria-hidden />
          {count("planned")} {c.roadmap.stepperPlanned}
        </span>
      </div>
    </div>
  );
}

export function Roadmap() {
  const c = useLandingCopy();

  return (
    <Section id="estado">
      <SectionHeading eyebrow={c.roadmap.eyebrow} title={c.roadmap.title} lead={c.roadmap.lead} />

      <Reveal delay={0.03}>
        <PhaseStepper />
      </Reveal>

      <ol className="mt-14 space-y-px">
        {c.roadmap.phases.map((phase, index) => (
          <Reveal key={phase.id} delay={Math.min(index * 0.04, 0.2)}>
            <li className="relative grid gap-3 border-l border-border py-7 pl-8 md:grid-cols-[13rem_1fr] md:gap-8 md:pl-10">
              <span className="absolute left-0 top-9 h-px w-5 bg-border md:w-7" aria-hidden />
              <span
                className="absolute left-[-4.5px] top-[calc(2.25rem-4px)] h-2 w-2 rounded-full bg-border ring-4 ring-bg"
                aria-hidden
              />

              <div>
                <p className="rule-label text-accent">{phase.period}</p>
                <div className="mt-2">
                  <StatusPill status={phase.status as PhaseStatus} />
                </div>
              </div>

              <div className="min-w-0">
                <h3 className="text-lg font-semibold tracking-tight">{phase.title}</h3>
                <p className="mt-2 max-w-2xl text-pretty leading-relaxed text-muted">
                  {phase.summary}
                </p>
                {phase.source && (
                  <p className="mt-3 font-mono text-xs text-muted/70">{phase.source}</p>
                )}
              </div>
            </li>
          </Reveal>
        ))}
      </ol>
    </Section>
  );
}
