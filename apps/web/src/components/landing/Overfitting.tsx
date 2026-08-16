"use client";

import { OptimismScatter } from "@/components/landing/charts/OptimismScatter";
import { LANDING_CHART } from "@/components/landing/charts/palette";
import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";
import { formatPct, formatSharpe, useEvidence } from "@/lib/evidence";

function Stat({
  value,
  label,
  tone = "default",
}: {
  value: string;
  label: string;
  tone?: "default" | "bad";
}) {
  return (
    <div className="rounded-md border border-border bg-surface-2 p-4">
      <p
        className={`tabular text-2xl font-semibold tracking-tight ${
          tone === "bad" ? "text-negative" : "text-accent"
        }`}
      >
        {value}
      </p>
      <p className="mt-1 text-xs leading-relaxed text-muted">{label}</p>
    </div>
  );
}

/** The leaked-feature experiment, as a bar per variant. */
function LeakageBars({ rows }: { rows: { variant: string; sharpe: number | null }[] }) {
  const labelled: Record<string, string> = {
    "causal (trailing)": "Solo mira al pasado",
    "leaky (centred)": "Hace trampa",
    "leaky, orientation flipped": "Hace trampa (al revés)",
    "buy and hold": "Comprar y esperar",
  };
  const values = rows.map((r) => Math.abs(r.sharpe ?? 0));
  const max = Math.max(...values, 1);

  return (
    <ul className="space-y-3">
      {rows.map((row) => {
        const value = row.sharpe ?? 0;
        const cheats = row.variant.startsWith("leaky");
        const width = (Math.abs(value) / max) * 100;
        return (
          <li key={row.variant}>
            <div className="flex items-baseline justify-between gap-3 text-sm">
              <span className={cheats ? "text-negative" : "text-fg"}>
                {labelled[row.variant] ?? row.variant}
              </span>
              <span className="tabular font-mono text-xs text-muted">{formatSharpe(value)}</span>
            </div>
            <div className="mt-1.5 h-2 rounded-full bg-surface-2">
              <div
                className="h-2 rounded-full transition-all"
                style={{
                  width: `${width}%`,
                  background: cheats ? "rgb(248 113 113)" : LANDING_CHART.accent,
                }}
              />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export function Overfitting() {
  const { data, error } = useEvidence();

  return (
    <Section id="sobreajuste">
      <SectionHeading
        eyebrow="El problema central"
        title="Por qué casi todos los backtests que ves son mentira"
        lead="No porque quien los publica mienta, sino porque probar muchas estrategias y quedarse con la mejor produce un número bonito aunque no haya nada que encontrar. Esto es lo que pasa cuando lo mides."
      />

      <div className="mt-14 grid gap-10 lg:grid-cols-[1.05fr_1fr] lg:gap-14">
        <Reveal>
          <div className="rounded-card border border-border bg-surface p-6 md:p-8">
            {error && (
              <p className="text-sm text-muted">
                No se pudo cargar la evidencia del estudio. Genera el fichero con{" "}
                <code className="font-mono text-xs text-accent">
                  uv run python scripts/export_web_evidence.py
                </code>
                .
              </p>
            )}
            {!data && !error && (
              <div className="h-[380px] animate-pulse rounded-md bg-surface-2" aria-hidden />
            )}
            {data && (
              <OptimismScatter
                points={data.optimism.points}
                slope={data.optimism.slope}
                meanVal={data.optimism.mean_val}
                meanTest={data.optimism.mean_test}
              />
            )}
          </div>
        </Reveal>

        <div className="flex flex-col justify-center">
          <Reveal delay={0.05}>
            <p className="rule-label text-accent">En simple</p>
            <p className="mt-3 text-lg leading-relaxed">
              Imagina 3.000 alumnos haciendo un examen de prueba. Te quedas con los que sacan
              sobresaliente y les pones el examen de verdad.{" "}
              <strong className="font-semibold">Suspenden.</strong> No porque hicieran trampa, sino
              porque en el examen de prueba había tantos alumnos que alguien tenía que acertar por
              casualidad.
            </p>
            <p className="mt-4 leading-relaxed text-muted">
              Cada punto del gráfico es una estrategia que ganó su ronda de selección. Si la nota de
              selección significara algo, los puntos caerían sobre la línea discontinua. La línea
              roja es lo que ocurre de verdad: casi plana. Elegir bien no sirvió de nada.
            </p>
          </Reveal>

          {data && (
            <Reveal delay={0.1}>
              <div className="mt-8 grid grid-cols-2 gap-3">
                <Stat
                  value={formatSharpe(data.optimism.mean_val)}
                  label="Nota media con la que se las eligió"
                />
                <Stat
                  value={formatSharpe(data.optimism.mean_test)}
                  label="Nota media que sacaron después"
                  tone="bad"
                />
                <Stat
                  value={formatPct(data.optimism.share_underperforming)}
                  label="Empeoraron respecto a su nota de selección"
                  tone="bad"
                />
                <Stat
                  value={`${(data.optimism.slope * 100).toFixed(0)}%`}
                  label="De la ventaja aparente que sobrevive. Lo honesto sería 100%"
                  tone="bad"
                />
              </div>
            </Reveal>
          )}
        </div>
      </div>

      {/* The second failure mode: looking at the future. */}
      <Reveal delay={0.1}>
        <div className="mt-16 grid gap-10 rounded-card border border-border bg-surface p-6 md:p-8 lg:grid-cols-[1fr_1.05fr] lg:gap-14">
          <div>
            <p className="rule-label text-accent">El otro fallo clásico</p>
            <h3 className="mt-3 text-2xl font-semibold tracking-tight">
              Mirar el futuro sin darte cuenta
            </h3>
            <p className="mt-4 leading-relaxed text-muted">
              Un indicador mal programado puede usar datos que en su momento nadie tenía. No falla
              con un error: funciona <em>demasiado</em> bien. Aquí está medido a propósito, con la
              misma regla, los mismos datos y las mismas comisiones. Lo único que cambia es que una
              versión puede ver 23 horas hacia delante.
            </p>
            <p className="mt-4 leading-relaxed text-muted">
              El signo da igual —basta invertir la regla— y por eso lo que delata la trampa no es
              que gane, sino <strong className="font-medium text-fg">cuánto</strong> gana. Nada real
              en este mercado se acerca a esas cifras.
            </p>
          </div>

          <div className="flex flex-col justify-center">
            {data && data.leakage.length > 0 ? (
              <>
                <LeakageBars rows={data.leakage} />
                <p className="mt-5 text-xs leading-relaxed text-muted">
                  Escala: Sharpe anualizado neto de costes, en valor absoluto. &ldquo;Comprar y
                  esperar&rdquo; es la referencia honesta del mismo periodo.
                </p>
              </>
            ) : (
              <div className="h-40 animate-pulse rounded-md bg-surface-2" aria-hidden />
            )}
          </div>
        </div>
      </Reveal>
    </Section>
  );
}
