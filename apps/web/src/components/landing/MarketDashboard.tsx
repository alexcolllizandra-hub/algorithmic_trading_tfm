"use client";

import { useState } from "react";

import { ChartCaption } from "@/components/landing/charts/ChartFrame";
import { DistributionChart } from "@/components/landing/charts/DistributionChart";
import { ASSET_COLOR } from "@/components/landing/charts/palette";
import { PriceChart } from "@/components/landing/charts/PriceChart";
import { VolatilityChart } from "@/components/landing/charts/VolatilityChart";
import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";
import { ErrorState, Skeleton } from "@/components/ui/States";
import { cn } from "@/lib/cn";
import { fmtInt, fmtNumber, fmtPercent } from "@/lib/format";
import {
  baseAsset,
  useDistributions,
  useMarketSeries,
  useSummary,
  type SummaryItem,
} from "@/lib/site-data";

function median(values: number[]): number {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function Panel({
  title,
  subtitle,
  children,
  className,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("rounded-card border border-border bg-surface p-6", className)}>
      <div className="mb-5">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-muted">{title}</h3>
        <p className="mt-1 text-sm text-muted/80">{subtitle}</p>
      </div>
      {children}
    </div>
  );
}

function Metrics({ item }: { item: SummaryItem }) {
  const metrics = [
    { label: "Volatilidad anualizada", value: fmtPercent(item.annualised_volatility, 1) },
    { label: "Peor hora", value: fmtPercent(item.worst_bar, 1) },
    { label: "Caída máxima", value: fmtPercent(item.max_drawdown, 1) },
    { label: "Exceso de curtosis", value: fmtNumber(item.excess_kurtosis, 1) },
  ];

  return (
    <dl className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {metrics.map((metric) => (
        <div key={metric.label} className="rounded-md border border-border bg-surface-2 px-4 py-3">
          <dt className="text-xs leading-snug text-muted">{metric.label}</dt>
          <dd className="tabular mt-1 text-lg font-semibold">{metric.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function FatTails({
  events,
  n,
}: {
  events: { sigma: number; observed: number; expected_normal: number }[];
  n: number;
}) {
  return (
    <table className="w-full text-sm">
      <caption className="sr-only">
        Movimientos extremos observados frente a los que predice una distribución normal
      </caption>
      <thead>
        <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
          <th scope="col" className="py-2 font-medium">
            Movimiento
          </th>
          <th scope="col" className="py-2 text-right font-medium">
            Predice la normal
          </th>
          <th scope="col" className="py-2 text-right font-medium">
            Ocurrió
          </th>
        </tr>
      </thead>
      <tbody className="divide-y divide-border">
        {events.map((event) => (
          <tr key={event.sigma}>
            <th scope="row" className="py-2.5 text-left font-normal">
              Más de {event.sigma}
              {"\u03C3"}
            </th>
            <td className="tabular py-2.5 text-right text-muted">
              {event.expected_normal < 0.01
                ? event.expected_normal.toExponential(0)
                : fmtNumber(event.expected_normal, 2)}
            </td>
            <td className="tabular py-2.5 text-right font-semibold text-negative">
              {fmtInt(event.observed)}
            </td>
          </tr>
        ))}
      </tbody>
      <tfoot>
        <tr>
          <td colSpan={3} className="pt-3 text-xs text-muted">
            Sobre {fmtInt(n)} horas de la partición de desarrollo.
          </td>
        </tr>
      </tfoot>
    </table>
  );
}

export function MarketDashboard() {
  const [symbol, setSymbol] = useState("BTCUSDT");

  const { data: seriesFile, error: seriesError, isLoading } = useMarketSeries();
  const { data: distributionsFile } = useDistributions();
  const { data: summaryFile } = useSummary();

  const series = seriesFile?.series.find((entry) => entry.symbol === symbol);
  const distribution = distributionsFile?.items.find(
    (item) => item.symbol === symbol && item.partition === "development"
  );
  const summary = summaryFile?.items.find(
    (item) => item.symbol === symbol && item.partition === "development"
  );
  const color = ASSET_COLOR[symbol] ?? ASSET_COLOR.BTCUSDT;
  const symbols = seriesFile?.series.map((entry) => entry.symbol) ?? ["BTCUSDT", "ETHUSDT"];

  return (
    <Section id="datos">
      <SectionHeading
        eyebrow="Datos reales"
        title="Esto no es un ejemplo ilustrativo"
        lead={
          <>
            Todo lo que hay debajo sale de los ficheros que usa la investigación, exportados por el
            propio pipeline. El área sombreada es el holdout: se dibuja para que se vea dónde
            empieza, y ningún número de esta página se ha elegido mirándolo.
          </>
        }
      />

      <Reveal delay={0.05}>
        <div className="mt-10 flex flex-wrap items-center gap-3">
          <div
            role="tablist"
            aria-label="Activo"
            className="inline-flex rounded-md border border-border bg-surface p-1"
          >
            {symbols.map((entry) => (
              <button
                key={entry}
                type="button"
                role="tab"
                aria-selected={entry === symbol}
                onClick={() => setSymbol(entry)}
                className={cn(
                  "rounded px-4 py-1.5 text-sm font-medium transition-colors",
                  entry === symbol ? "bg-accent text-accent-fg" : "text-muted hover:text-fg"
                )}
              >
                {baseAsset(entry)}
              </button>
            ))}
          </div>
          <span className="font-mono text-xs text-muted">
            {symbol} · perpetuo USDT-M · velas de {seriesFile?.timeframe ?? "1h"}
          </span>
        </div>
      </Reveal>

      {seriesError && (
        <div className="mt-8">
          <ErrorState title="No se pudieron cargar los datos" detail={seriesError.message} />
        </div>
      )}

      {isLoading && !seriesError && (
        <div className="mt-8 space-y-6">
          <Skeleton className="h-72 w-full" />
          <Skeleton className="h-72 w-full" />
        </div>
      )}

      {series && (
        <div className="mt-8 space-y-6">
          {summary && (
            <Reveal>
              <Metrics item={summary} />
            </Reveal>
          )}

          <Reveal delay={0.05}>
            <Panel
              title={`Precio de ${baseAsset(symbol)}`}
              subtitle="Cierre diario, escala logarítmica"
            >
              <PriceChart points={series.price} color={color} />
              <ChartCaption>
                Escala logarítmica porque en seis años el precio se multiplica: en lineal, los
                primeros años quedarían aplastados contra el eje.
              </ChartCaption>
            </Panel>
          </Reveal>

          <Reveal delay={0.05}>
            <Panel
              title="Volatilidad"
              subtitle={`Desviación típica móvil de ${seriesFile?.volatility_window_days ?? 30} días, anualizada`}
            >
              <VolatilityChart
                points={series.volatility}
                color={color}
                median={median(series.volatility.map((point) => point.v))}
              />
              <ChartCaption>
                La ventana solo mira hacia atrás: el valor de un día se calcula con las horas
                anteriores y nunca con las posteriores. La volatilidad no es constante, y por eso
                una estrategia con parámetros fijos se comporta distinto según la época.
              </ChartCaption>
            </Panel>
          </Reveal>

          {distribution && (
            <Reveal delay={0.05}>
              <Panel
                title="Distribución de retornos"
                subtitle="Observado frente a una normal con la misma media y desviación típica"
              >
                <div className="lg:grid lg:grid-cols-[1.6fr_1fr] lg:gap-8">
                  <div className="min-w-0">
                    <DistributionChart distribution={distribution} color={color} />
                    <ChartCaption>
                      Eje vertical logarítmico. La curva discontinua es lo que predeciría una
                      campana de Gauss; la zona sombreada marca lo que queda más allá de tres
                      desviaciones típicas. La diferencia entre ambas curvas en los extremos es
                      exactamente lo que significa &ldquo;colas gordas&rdquo;.
                    </ChartCaption>
                  </div>
                  <div className="mt-8 lg:mt-0">
                    <FatTails events={distribution.sigma_events} n={distribution.stats.n} />
                    <p className="mt-5 text-sm leading-relaxed text-muted">
                      Con exceso de curtosis de {fmtNumber(distribution.stats.excess_kurtosis, 1)} y
                      asimetría de {fmtNumber(distribution.stats.skew, 2)}, la normal no es una
                      aproximación imperfecta: es la distribución equivocada. Cualquier medida de
                      riesgo que la asuma subestima lo que puede pasar en un día malo.
                    </p>
                  </div>
                </div>
              </Panel>
            </Reveal>
          )}
        </div>
      )}
    </Section>
  );
}
