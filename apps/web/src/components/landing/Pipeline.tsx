"use client";

import { useState } from "react";

import type { PhaseStatus } from "@/components/landing/content";
import { useLandingCopy } from "@/components/landing/copy";
import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";
import { StatusPill } from "@/components/landing/StatusPill";
import { cn } from "@/lib/cn";

const LEGEND: PhaseStatus[] = ["done", "in-review", "blocked", "planned"];

const NODE_TONE: Record<PhaseStatus, string> = {
  done: "border-positive/50 bg-positive/15 text-positive",
  "in-review": "border-accent/50 bg-accent/15 text-accent",
  blocked: "border-warn/50 bg-warn/15 text-warn",
  planned: "border-border bg-surface-2 text-muted",
};

export function Pipeline() {
  const c = useLandingCopy();
  const steps = c.pipeline.steps;
  const [active, setActive] = useState<string>(steps[0].id);
  const step = steps.find((entry) => entry.id === active) ?? steps[0];

  return (
    <Section id="metodo">
      <SectionHeading
        eyebrow={c.pipeline.eyebrow}
        title={c.pipeline.title}
        lead={c.pipeline.lead}
      />

      <Reveal delay={0.05}>
        <ul className="mt-10 flex flex-wrap gap-x-6 gap-y-2">
          {LEGEND.map((status) => (
            <li key={status} className="flex items-center gap-2 text-xs text-muted">
              <span
                className={cn("h-2.5 w-2.5 rounded-full border", NODE_TONE[status])}
                aria-hidden
              />
              {c.pipeline.statusLabel[status]}
            </li>
          ))}
        </ul>
      </Reveal>

      <Reveal delay={0.1}>
        <ol className="mt-8 flex snap-x gap-2 overflow-x-auto pb-3 lg:grid lg:grid-cols-5 lg:overflow-visible">
          {steps.map((entry, index) => {
            const selected = entry.id === step.id;
            return (
              <li key={entry.id} className="snap-start">
                <button
                  type="button"
                  onClick={() => setActive(entry.id)}
                  aria-current={selected ? "step" : undefined}
                  className={cn(
                    "group flex h-full w-44 flex-col gap-2 rounded-md border p-4 text-left transition-colors lg:w-full",
                    selected
                      ? "border-accent/60 bg-surface"
                      : "border-border bg-surface/40 hover:border-border hover:bg-surface"
                  )}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border font-mono text-[11px]",
                        NODE_TONE[entry.status as PhaseStatus]
                      )}
                    >
                      {index + 1}
                    </span>
                    <span
                      className={cn(
                        "text-sm font-medium",
                        selected ? "text-fg" : "text-muted group-hover:text-fg"
                      )}
                    >
                      {entry.title}
                    </span>
                  </div>
                  <p className="text-xs leading-relaxed text-muted">{entry.what}</p>
                </button>
              </li>
            );
          })}
        </ol>
      </Reveal>

      <Reveal delay={0.15}>
        <div className="mt-4 rounded-card border border-border bg-surface p-6 md:p-8">
          <div className="flex flex-wrap items-center gap-3">
            <h3 className="text-lg font-semibold tracking-tight">{step.title}</h3>
            <StatusPill status={step.status as PhaseStatus} />
          </div>
          <p className="mt-3 max-w-3xl text-pretty leading-relaxed text-muted">{step.detail}</p>
        </div>
      </Reveal>
    </Section>
  );
}
