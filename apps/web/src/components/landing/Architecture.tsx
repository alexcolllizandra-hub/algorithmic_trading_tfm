"use client";

import { useState } from "react";

import { useLandingCopy } from "@/components/landing/copy";
import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";
import { cn } from "@/lib/cn";

export function Architecture() {
  const c = useLandingCopy();
  const layers = c.architecture.layers;
  const [active, setActive] = useState(layers[0].id);
  const layer = layers.find((l) => l.id === active) ?? layers[0];

  return (
    <Section id="arquitectura">
      <SectionHeading
        eyebrow={c.architecture.eyebrow}
        title={c.architecture.title}
        lead={c.architecture.lead}
      />

      <div className="mt-14 grid gap-8 lg:grid-cols-[280px_1fr] lg:gap-12">
        {/* The stack. Vertical on desktop so the flow reads top to bottom. */}
        <Reveal>
          <ol className="relative space-y-2">
            {layers.map((l, index) => {
              const isActive = l.id === active;
              return (
                <li key={l.id}>
                  <button
                    type="button"
                    onClick={() => setActive(l.id)}
                    aria-current={isActive ? "step" : undefined}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-md border px-4 py-3 text-left transition-colors",
                      isActive
                        ? "border-accent/60 bg-surface-2 text-fg"
                        : "border-border bg-surface text-muted hover:border-accent/30 hover:text-fg"
                    )}
                  >
                    <span
                      className={cn(
                        "tabular flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-xs font-semibold",
                        isActive ? "bg-accent text-accent-fg" : "bg-surface-2 text-muted"
                      )}
                      aria-hidden
                    >
                      {index + 1}
                    </span>
                    <span className="text-sm font-medium">{l.name}</span>
                    <span className="ml-auto text-muted" aria-hidden>
                      {isActive ? "▸" : ""}
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
        </Reveal>

        <Reveal delay={0.05}>
          <article className="flex h-full flex-col rounded-card border border-border bg-surface p-6 md:p-8">
            <p className="rule-label text-accent">{layer.role}</p>
            <h3 className="mt-3 text-2xl font-semibold tracking-tight">{layer.name}</h3>

            <p className="mt-5 text-lg leading-relaxed">{layer.plain}</p>

            <div className="mt-6 rounded-md border border-border bg-surface-2 p-5">
              <p className="rule-label mb-2 text-muted">{c.architecture.howBuilt}</p>
              <p className="text-sm leading-relaxed text-fg/90">{layer.technical}</p>
            </div>

            <div className="mt-4 rounded-md border border-accent/25 bg-accent/5 p-5">
              <p className="rule-label mb-2 text-accent">{c.architecture.lockLabel}</p>
              <p className="text-sm leading-relaxed text-fg/90">{layer.guard}</p>
            </div>

            <div className="mt-auto flex flex-wrap gap-2 pt-6">
              {layer.modules.map((m) => (
                <code
                  key={m}
                  className="rounded border border-border bg-surface-2 px-2 py-1 font-mono text-[11px] text-muted"
                >
                  {m}
                </code>
              ))}
            </div>
          </article>
        </Reveal>
      </div>
    </Section>
  );
}
