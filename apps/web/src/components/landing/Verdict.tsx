"use client";

import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";
import { TEST_COUNT_LABEL, formatPct, useEvidence } from "@/lib/evidence";

/** A PBO meter: 0 = selection works, 0.5 = coin flip, 1 = systematically wrong. */
function PboMeter({ value, splits }: { value: number; splits: number }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return (
    <div>
      <div className="relative h-9 overflow-hidden rounded-md bg-surface-2">
        <div
          className="h-full bg-negative/80 transition-all"
          style={{ width: `${pct}%` }}
          aria-hidden
        />
        <div className="absolute inset-y-0 left-1/2 w-0.5 -translate-x-1/2 bg-fg" aria-hidden />
        <span className="tabular absolute inset-y-0 left-3 flex items-center text-sm font-semibold text-fg">
          {value.toFixed(3)}
        </span>
      </div>
      <div className="mt-2 flex justify-between text-[11px] text-muted">
        <span>0 · elegir funciona</span>
        <span className="font-medium text-fg">0.5 · cara o cruz</span>
        <span>1 · siempre al revés</span>
      </div>
      <p className="mt-3 text-xs leading-relaxed text-muted">
        Probabilidad de que la mejor estrategia dentro de la muestra quede en la mitad mala fuera de
        ella, medida sobre {splits} particiones.
      </p>
    </div>
  );
}

export function Verdict() {
  const { data, error } = useEvidence();

  return (
    <Section id="veredicto">
      <SectionHeading
        eyebrow="El resultado"
        title={
          data
            ? `${data.study.n_families} familias, ninguna sobrevive`
            : "Ninguna familia sobrevive"
        }
        lead="Este es el hallazgo de la tesis, y es negativo. Merece la pena decir por qué eso es un resultado y no un fracaso: el estudio podía haber encontrado algo, se le dio la oportunidad de hacerlo, y tres diagnósticos independientes coinciden en que no lo hay."
      />

      {error && (
        <p className="mt-10 text-sm text-muted">
          No se pudo cargar la evidencia del estudio.{" "}
          <code className="font-mono text-xs text-accent">
            uv run python scripts/export_web_evidence.py
          </code>
        </p>
      )}

      {!data && !error && (
        <div className="mt-14 h-72 animate-pulse rounded-card bg-surface" aria-hidden />
      )}

      {data && (
        <>
          <Reveal>
            <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[
                {
                  v: String(data.study.n_families),
                  l: "familias de estrategia evaluadas",
                },
                {
                  v: data.study.n_configurations.toLocaleString("es-ES"),
                  l: "configuraciones distintas probadas",
                },
                {
                  v: String(data.study.holm_rejected),
                  l: "sobreviven a la corrección por número de pruebas",
                },
                {
                  v: data.study.smallest_raw_p.toFixed(2),
                  l: `p-valor más bajo del estudio. Haría falta menos de ${data.study.alpha}`,
                },
              ].map((s) => (
                <div key={s.l} className="rounded-card border border-border bg-surface p-6">
                  <p className="tabular text-3xl font-semibold tracking-tight text-fg">{s.v}</p>
                  <p className="mt-2 text-sm leading-relaxed text-muted">{s.l}</p>
                </div>
              ))}
            </div>
          </Reveal>

          <div className="mt-10 grid gap-6 lg:grid-cols-2">
            <Reveal delay={0.05}>
              <article className="h-full rounded-card border border-border bg-surface p-6 md:p-8">
                <p className="rule-label text-accent">Probabilidad de sobreajuste</p>
                <h3 className="mt-3 text-xl font-semibold tracking-tight">
                  Elegir la mejor no sirve de nada
                </h3>
                <div className="mt-6">
                  <PboMeter value={data.study.pbo} splits={data.study.pbo_splits} />
                </div>
                <p className="mt-5 text-sm leading-relaxed text-muted">
                  Sale prácticamente en el medio. Es la firma de una búsqueda operando sobre ruido:
                  la que gana en una mitad de los datos tiene las mismas probabilidades que
                  cualquier otra de ganar en la siguiente.
                </p>
              </article>
            </Reveal>

            <Reveal delay={0.1}>
              <article className="h-full rounded-card border border-border bg-surface p-6 md:p-8">
                <p className="rule-label text-accent">A prueba de discusión</p>
                <h3 className="mt-3 text-xl font-semibold tracking-tight">
                  Da igual cómo cuentes las pruebas
                </h3>
                <p className="mt-4 text-sm leading-relaxed text-muted">
                  La objeción habitual a una corrección por pruebas múltiples es que el número de
                  pruebas se ha elegido a conveniencia. Aquí no cambia nada: bajo las cuatro formas
                  razonables de contarlas, el umbral exigido sigue quedando por debajo del mejor
                  p-valor observado.
                </p>
                <ul className="mt-6 space-y-2.5">
                  {data.study.sensitivity.map((row) => (
                    <li
                      key={row.definition}
                      className="flex items-baseline justify-between gap-3 border-b border-border/60 pb-2.5 text-sm last:border-0"
                    >
                      <span className="text-muted">
                        {TEST_COUNT_LABEL[row.definition] ?? row.definition}
                      </span>
                      <span className="tabular shrink-0 font-mono text-xs">
                        {row.n_tests.toLocaleString("es-ES")} pruebas
                      </span>
                      <span
                        className={
                          row.any_survive
                            ? "shrink-0 text-xs text-warn"
                            : "shrink-0 text-xs text-muted"
                        }
                      >
                        {row.any_survive ? "sobrevive alguna" : "ninguna"}
                      </span>
                    </li>
                  ))}
                </ul>
              </article>
            </Reveal>
          </div>

          <Reveal delay={0.1}>
            <div className="mt-10 overflow-hidden rounded-card border border-border bg-surface">
              <div className="border-b border-border px-6 py-5">
                <h3 className="text-lg font-semibold tracking-tight">Familia por familia</h3>
                <p className="mt-1.5 text-sm text-muted">
                  Retorno compuesto neto de comisiones, deslizamiento y funding sobre el periodo de
                  desarrollo, promediado entre semillas.
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-muted">
                      <th className="px-6 py-3 font-medium">Familia</th>
                      <th className="px-6 py-3 font-medium">Activo</th>
                      <th className="px-6 py-3 text-right font-medium">Retorno</th>
                      <th className="px-6 py-3 text-right font-medium">Sharpe</th>
                      <th className="px-6 py-3 text-right font-medium">p-valor</th>
                      <th className="px-6 py-3 text-right font-medium">Veredicto</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...data.study.families]
                      .sort((a, b) => a.p_value - b.p_value)
                      .map((f) => (
                        <tr
                          key={`${f.family}-${f.symbol}`}
                          className="border-b border-border/50 last:border-0"
                        >
                          <td className="px-6 py-3 font-medium">{f.family}</td>
                          <td className="px-6 py-3 text-muted">{f.symbol.replace(/USDT$/, "")}</td>
                          <td
                            className={`tabular px-6 py-3 text-right ${
                              f.total_return >= 0 ? "text-positive" : "text-negative"
                            }`}
                          >
                            {formatPct(f.total_return, 1)}
                          </td>
                          <td className="tabular px-6 py-3 text-right text-muted">
                            {f.sharpe.toFixed(2)}
                          </td>
                          <td className="tabular px-6 py-3 text-right text-muted">
                            {f.p_value.toFixed(3)}
                          </td>
                          <td className="px-6 py-3 text-right">
                            <span className="rounded border border-negative/30 bg-negative/10 px-2 py-0.5 text-xs text-negative">
                              rechazada
                            </span>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          </Reveal>

          <Reveal delay={0.1}>
            <div className="mt-10 rounded-card border border-warn/30 bg-warn/5 p-6 md:p-8">
              <p className="rule-label text-warn">Los seis meses congelados</p>
              <h3 className="mt-3 text-xl font-semibold tracking-tight">
                Se abrieron una vez. No se publica la cifra.
              </h3>
              <p className="mt-4 max-w-3xl leading-relaxed text-muted">
                La partición reservada se abrió sobre un candidato declarado de antemano, y su
                lectura existe en disco. No aparece aquí porque quedó pendiente una auditoría de
                procedencia: comprobar que el candidato estaba realmente congelado antes de mirar.
                No se ha reescrito el historial para taparlo, porque hacerlo destruiría justo la
                prueba que hace auditable una apertura.
              </p>
              <p className="mt-4 max-w-3xl leading-relaxed text-muted">
                La conclusión del estudio no depende de esa lectura. El holdout era la prueba
                confirmatoria de un candidato que la corrección por pruebas múltiples{" "}
                <strong className="font-medium text-fg">ya había rechazado</strong>. Publicarla
                cambiaría el énfasis de un párrafo, no el resultado.
              </p>
              <p className="mt-5 font-mono text-xs text-warn">
                estado: {data.holdout_state} · commit {data.study.source_commit.slice(0, 12)}
              </p>
            </div>
          </Reveal>
        </>
      )}
    </Section>
  );
}
