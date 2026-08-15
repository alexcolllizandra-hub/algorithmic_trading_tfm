import { ROADMAP } from "@/components/landing/content";
import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";
import { StatusPill } from "@/components/landing/StatusPill";

export function Roadmap() {
  return (
    <Section id="roadmap">
      <SectionHeading
        eyebrow="Roadmap"
        title="Dónde está el proyecto, sin adornos"
        lead="Dos de las puertas ya se han cerrado en negativo y están contadas como tales. En investigación eso no es un contratiempo: es el resultado."
      />

      <ol className="mt-14 space-y-px">
        {ROADMAP.map((phase, index) => (
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
                  <StatusPill status={phase.status} />
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
