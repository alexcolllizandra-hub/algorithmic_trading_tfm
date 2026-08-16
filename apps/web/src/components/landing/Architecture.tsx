"use client";

import { useState } from "react";

import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";
import { cn } from "@/lib/cn";

interface Layer {
  id: string;
  name: string;
  role: string;
  plain: string;
  technical: string;
  guard: string;
  modules: string[];
}

const LAYERS: Layer[] = [
  {
    id: "datos",
    name: "Datos",
    role: "Traer el mercado a disco y no volver a tocarlo",
    plain:
      "Se descargan las velas de Binance una vez y se guardan tal cual. A partir de ahí, " +
      "cualquier transformación vive en una copia derivada que sabe de dónde viene.",
    technical:
      "Descarga masiva desde data.binance.vision con incrementales por CCXT. Cada dataset " +
      "lleva un manifiesto con origen, símbolo, periodo, número de filas y SHA-256. " +
      "Validación con esquemas: huecos, duplicados, OHLC imposible y volúmenes negativos.",
    guard: "data/raw es de solo lectura. Los extremos se marcan, nunca se borran.",
    modules: ["data/providers", "data/manifest", "validation/schemas"],
  },
  {
    id: "features",
    name: "Indicadores",
    role: "Calcular solo lo que se podía saber en su momento",
    plain:
      "Cada indicador se calcula mirando exclusivamente hacia atrás. Si recortas el futuro " +
      "del fichero, ningún valor del pasado puede cambiar.",
    technical:
      "Registro declarativo de tipos de indicador: cada uno declara sus entradas, su ventana, " +
      "el instante en que su valor es conocible y cuántas filas iniciales quedan vacías. " +
      "Los indicadores contextuales se retrasan explícitamente antes de usarse.",
    guard:
      "Siete pruebas de causalidad que se ejecutan sobre los datos reales, no sobre fixtures. " +
      "Una fuga plantada a propósito las hace fallar al instante.",
    modules: ["features/spec", "features/causal", "features/registry"],
  },
  {
    id: "estrategias",
    name: "Estrategias",
    role: "Reglas que caben en una frase",
    plain:
      "Nada de cajas negras. Cruce de medias, ruptura de rango, reversión a la media, " +
      "funding, confirmación entre BTC y ETH. Si una regla funciona, se puede explicar.",
    technical:
      "Trece familias con un espacio de parámetros tipado y finito, con reparación de " +
      "combinaciones inválidas y hash canónico por candidato. El mismo motor sirve las nueve " +
      "variantes de Candle Range Theory.",
    guard: "El espacio se declara antes de buscar y no se amplía después de ver resultados.",
    modules: ["strategies/*", "search/space", "crt/*"],
  },
  {
    id: "backtest",
    name: "Backtest",
    role: "Simular pagando lo que se paga",
    plain:
      "La orden se decide con la vela cerrada y se ejecuta en la apertura de la siguiente. " +
      "Nunca al precio que acaba de revelar la señal.",
    technical:
      "Libro por vela con señal, posición, precio de ejecución, retorno bruto, comisión, " +
      "deslizamiento, funding y retorno neto. Un giro de largo a corto mueve dos unidades de " +
      "nocional y se cobra como dos.",
    guard:
      "Si el experimento exige funding y no hay serie de funding, el motor falla en vez de " +
      "suponer cero.",
    modules: ["backtesting/engine", "backtesting/metrics"],
  },
  {
    id: "validacion",
    name: "Validación temporal",
    role: "Fabricar futuro de verdad, quince veces",
    plain:
      "Se entrena con el pasado y se evalúa con lo que vino después, avanzando por el " +
      "calendario. Entre ambos se deja un hueco para que ninguna operación cruce la frontera.",
    technical:
      "Walk-forward expandido: quince pliegues con entrenamiento anclado, ventana de " +
      "selección y ventana de prueba de 90 días sin solape. La purga y el embargo se derivan " +
      "del periodo máximo de mantenimiento, no se eligen a ojo.",
    guard:
      "Ningún pliegue puede tocar el holdout congelado. La comprobación lanza excepción, no " +
      "un aviso.",
    modules: ["validation/walk_forward", "search/evaluator"],
  },
  {
    id: "inferencia",
    name: "Inferencia",
    role: "Contar cuántas veces se ha mirado",
    plain:
      "Si pruebas trece estrategias, una parecerá buena por azar. Se lleva la cuenta de todas " +
      "las pruebas y se corrige el resultado en consecuencia.",
    technical:
      "Diez semillas por unidad, con la unidad de inferencia en activo × pliegue y las " +
      "semillas promediadas dentro de cada celda. Corrección Holm-Bonferroni y " +
      "Benjamini-Hochberg, Sharpe deflactado y probabilidad de sobreajuste del backtest.",
    guard:
      "El veredicto se comprueba bajo cuatro formas distintas de contar las pruebas, de trece " +
      "a casi medio millón.",
    modules: ["evaluation/multiple_testing", "evaluation/study_robustness"],
  },
];

export function Architecture() {
  const [active, setActive] = useState(LAYERS[0].id);
  const layer = LAYERS.find((l) => l.id === active) ?? LAYERS[0];

  return (
    <Section id="arquitectura">
      <SectionHeading
        eyebrow="Cómo funciona por dentro"
        title="Seis capas, y cada una con su cerrojo"
        lead="El dato entra por arriba y sale por abajo convertido en un veredicto. Lo que hace defendible el resultado no es ninguna capa en concreto, sino que cada una falla en cerrado: ante la duda, el sistema se para en vez de continuar con un supuesto."
      />

      <div className="mt-14 grid gap-8 lg:grid-cols-[280px_1fr] lg:gap-12">
        {/* The stack. Vertical on desktop so the flow reads top to bottom. */}
        <Reveal>
          <ol className="relative space-y-2">
            {LAYERS.map((l, index) => {
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
              <p className="rule-label mb-2 text-muted">Cómo está hecho</p>
              <p className="text-sm leading-relaxed text-fg/90">{layer.technical}</p>
            </div>

            <div className="mt-4 rounded-md border border-accent/25 bg-accent/5 p-5">
              <p className="rule-label mb-2 text-accent">El cerrojo</p>
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
