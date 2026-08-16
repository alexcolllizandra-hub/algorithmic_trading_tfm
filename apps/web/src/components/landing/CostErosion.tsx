"use client";

// "Efficient market", paid off with the study's own numbers instead of a
// supermarket metaphor. Both series already ship in evidence.json; until now
// nothing rendered them.

import {
  breakEvenBps,
  CostErosionChart,
  TurnoverWedgeChart,
} from "@/components/landing/charts/CostErosion";
import { LANDING_CHART } from "@/components/landing/charts/palette";
import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";
import { formatSharpe, useEvidence } from "@/lib/evidence";

function Panel({
  label,
  title,
  caption,
  children,
}: {
  label: string;
  title: string;
  caption: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-card border border-border bg-surface p-6 md:p-7">
      <p className="rule-label text-accent">{label}</p>
      <h3 className="mt-2.5 text-lg font-semibold tracking-tight">{title}</h3>
      <div className="mt-6">{children}</div>
      <p className="mt-4 text-xs leading-relaxed text-muted">{caption}</p>
    </div>
  );
}

export function CostErosion() {
  const { data, error } = useEvidence();

  if (error) return null;

  const crossing = data ? breakEvenBps(data.cost_sensitivity) : null;
  const buyAndHold = data?.turnover.buy_and_hold_sharpe ?? null;

  return (
    <Section id="costes">
      <SectionHeading
        eyebrow="Mercado eficiente"
        title="La ventaja existe hasta que pagas por ella"
        lead="La versión de manual dice que si el precio ya incorpora la información, ninguna regla basada en esa información gana dinero. Aquí está la versión medida: la misma estrategia, el mismo periodo, subiendo solo lo que cuesta operar."
      />

      <div className="mt-14 grid gap-6 lg:grid-cols-2">
        <Reveal>
          <Panel
            label="Erosión por costes"
            title="Dónde se acaba la ventaja"
            caption="Sharpe anualizado sobre la partición de desarrollo, variando únicamente el coste de ida y vuelta. Todo lo demás queda fijo."
          >
            {data ? (
              <CostErosionChart rows={data.cost_sensitivity} />
            ) : (
              <div className="h-[280px] animate-pulse rounded-md bg-surface-2" aria-hidden />
            )}
          </Panel>
        </Reveal>

        <Reveal delay={0.05}>
          <Panel
            label="Bruto contra neto"
            title="Cuanto más operas, más se abre la cuña"
            caption="Cada par de puntos es una configuración de medias móviles. Arriba el resultado antes de costes; abajo, el mismo después de comisiones, deslizamiento y funding."
          >
            {data ? (
              <TurnoverWedgeChart grid={data.turnover.grid} />
            ) : (
              <div className="h-[280px] animate-pulse rounded-md bg-surface-2" aria-hidden />
            )}
          </Panel>
        </Reveal>
      </div>

      {data && (
        <Reveal delay={0.1}>
          <div className="mt-10 grid gap-6 lg:grid-cols-[1fr_1.15fr] lg:gap-14">
            <div className="grid grid-cols-2 gap-3 self-start">
              <div className="rounded-md border border-border bg-surface-2 p-4">
                <p className="tabular text-2xl font-semibold tracking-tight text-negative">
                  {crossing != null ? `${crossing.toFixed(0)} bps` : "—"}
                </p>
                <p className="mt-1 text-xs leading-relaxed text-muted">
                  Coste por vuelta al que la ventaja llega a cero
                </p>
              </div>
              <div className="rounded-md border border-border bg-surface-2 p-4">
                <p className="tabular text-2xl font-semibold tracking-tight text-accent">
                  {formatSharpe(buyAndHold)}
                </p>
                <p className="mt-1 text-xs leading-relaxed text-muted">
                  Sharpe de comprar y esperar en el mismo periodo
                </p>
              </div>
            </div>

            <div className="flex flex-col justify-center">
              <p className="rule-label text-accent">En simple</p>
              <p className="mt-3 text-lg leading-relaxed">
                No hace falta que el mercado sea perfecto para que no ganes.{" "}
                <strong className="font-semibold">Basta con que cobre por participar.</strong>
              </p>
              <p className="mt-4 leading-relaxed text-muted">
                La curva de la izquierda no baja porque la estrategia empeore: es exactamente la
                misma regla, sobre exactamente los mismos datos. Lo único que sube es el peaje. A{" "}
                {crossing != null
                  ? `${crossing.toFixed(0)} puntos básicos`
                  : "cierto nivel de coste"}{" "}
                por operación completa, lo que parecía una ventaja ya no lo es — y ese peaje está
                dentro del rango que cobra un exchange real.
              </p>
              <p className="mt-4 leading-relaxed text-muted">
                La cuña de la derecha explica por qué la solución no es operar más. Cada punto azul
                es lo que habrías ganado si operar fuese gratis; el rojo debajo es lo que queda al
                pagar. Cuanto más a la derecha, más veces entras y sales, y más se separan.{" "}
                <span className="font-medium" style={{ color: LANDING_CHART.accent }}>
                  La actividad no es una fuente de rentabilidad: es una fuente de coste.
                </span>
              </p>
            </div>
          </div>
        </Reveal>
      )}
    </Section>
  );
}
