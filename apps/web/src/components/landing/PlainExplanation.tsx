import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";

const STEPS = [
  {
    n: "01",
    title: "Una receta, no una corazonada",
    body: (
      <>
        Operar de forma sistemática es cocinar con receta escrita en lugar de a ojo. La receta dice
        exactamente qué comprar, cuánto y cuándo vender. Como está escrita, se puede repetir, medir
        y corregir. Cocinar a ojo puede salir bien, pero no sabrás por qué, y no podrás repetirlo.
      </>
    ),
  },
  {
    n: "02",
    title: "Probarla con la comida de ayer",
    body: (
      <>
        Antes de arriesgar dinero, la receta se prueba sobre lo que ya pasó: si hubiera seguido esta
        regla los últimos seis años, ¿habría ganado? Eso es un <em>backtest</em>. Y aquí aparece la
        trampa, porque el pasado ya se conoce y siempre se deja convencer.
      </>
    ),
  },
  {
    n: "03",
    title: "Por qué casi siempre engaña",
    body: (
      <>
        Si retocas la receta hasta que el año pasado sale perfecto, no has descubierto nada: has
        copiado las respuestas del examen. El resultado brillante no dice si mañana funcionará; solo
        dice cuánto has ajustado. Casi todo este proyecto consiste en cerrarse a sí mismo esa
        puerta.
      </>
    ),
  },
];

export function PlainExplanation() {
  return (
    <Section id="en-simple">
      <SectionHeading
        eyebrow="Qué es esto, en simple"
        title="Sin una sola palabra técnica"
        lead="Si nunca has operado en un mercado, esta sección es suficiente para entender el resto de la página."
      />

      <div className="mt-14 grid gap-px overflow-hidden rounded-card border border-border bg-border md:grid-cols-3">
        {STEPS.map((step, index) => (
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
          Un resultado negativo obtenido con rigor es un resultado válido. Un resultado positivo
          obtenido mirando el futuro no lo es.
          <footer className="mt-3 text-sm text-muted">
            Es la regla que ordena todas las decisiones del proyecto.
          </footer>
        </blockquote>
      </Reveal>
    </Section>
  );
}
