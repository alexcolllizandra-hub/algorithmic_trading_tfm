import { CONCEPTS } from "@/components/landing/content";
import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";

export function Concepts() {
  return (
    <Section id="conceptos">
      <SectionHeading
        eyebrow="Conceptos clave"
        title="Cinco ideas que deciden si un resultado vale algo"
        lead="Cada tarjeta trae la definición técnica y el ejemplo cotidiano que la aterriza. Son las cinco trampas en las que cae la mayoría de los backtests que circulan por ahí."
      />

      <div className="mt-14 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {CONCEPTS.map((concept, index) => (
          <Reveal key={concept.id} delay={index * 0.05}>
            <article className="flex h-full flex-col rounded-card border border-border bg-surface p-7 transition-colors hover:border-accent/40">
              <h3 className="text-lg font-semibold tracking-tight">{concept.title}</h3>

              <p className="mt-4 text-sm leading-relaxed text-muted">{concept.technical}</p>

              <div className="mt-5 rounded-md border border-border bg-surface-2 p-4">
                <p className="rule-label mb-2 text-accent">En la vida real</p>
                <p className="text-sm leading-relaxed text-fg/90">{concept.everyday}</p>
              </div>

              <p className="mt-auto pt-5 text-sm font-medium text-fg">{concept.punchline}</p>

              {concept.evidence && (
                <a
                  href={concept.evidence.href}
                  className="mt-3 inline-flex items-center gap-1.5 text-sm text-accent underline-offset-4 hover:underline"
                >
                  {concept.evidence.label}
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
