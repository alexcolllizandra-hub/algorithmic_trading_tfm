"use client";

import { useState } from "react";

import { ChartCaption } from "@/components/landing/charts/ChartFrame";
import { DistributionChart } from "@/components/landing/charts/DistributionChart";
import { ASSET_COLOR } from "@/components/landing/charts/palette";
import { PriceChart } from "@/components/landing/charts/PriceChart";
import { VolatilityChart } from "@/components/landing/charts/VolatilityChart";
import { tpl, useLandingCopy } from "@/components/landing/copy";
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
  const c = useLandingCopy();
  const metrics = [
    { label: c.market.metrics.vol, value: fmtPercent(item.annualised_volatility, 1) },
    { label: c.market.metrics.worst, value: fmtPercent(item.worst_bar, 1) },
    { label: c.market.metrics.drawdown, value: fmtPercent(item.max_drawdown, 1) },
    { label: c.market.metrics.kurtosis, value: fmtNumber(item.excess_kurtosis, 1) },
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
  const c = useLandingCopy();
  return (
    <table className="w-full text-sm">
      <caption className="sr-only">{c.market.fatTailsCaption}</caption>
      <thead>
        <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
          <th scope="col" className="py-2 font-medium">
            {c.market.fatTailsMove}
          </th>
          <th scope="col" className="py-2 text-right font-medium">
            {c.market.fatTailsExpected}
          </th>
          <th scope="col" className="py-2 text-right font-medium">
            {c.market.fatTailsObserved}
          </th>
        </tr>
      </thead>
      <tbody className="divide-y divide-border">
        {events.map((event) => (
          <tr key={event.sigma}>
            <th scope="row" className="py-2.5 text-left font-normal">
              {c.market.fatTailsOver} {event.sigma}
              {"σ"}
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
            {c.market.fatTailsFooterPrefix} {fmtInt(n)} {c.market.fatTailsFooterSuffix}
          </td>
        </tr>
      </tfoot>
    </table>
  );
}

export function MarketDashboard() {
  const [symbol, setSymbol] = useState("BTCUSDT");
  const c = useLandingCopy();

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
      <SectionHeading eyebrow={c.market.eyebrow} title={c.market.title} lead={c.market.lead} />

      <Reveal delay={0.05}>
        <div className="mt-10 flex flex-wrap items-center gap-3">
          <div
            role="tablist"
            aria-label={c.market.assetAria}
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
            {symbol} · {c.market.seriesSuffix} {seriesFile?.timeframe ?? "1h"}
          </span>
        </div>
      </Reveal>

      {seriesError && (
        <div className="mt-8">
          <ErrorState title={c.market.loadError} detail={seriesError.message} />
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
              title={`${c.market.pricePanelTitle} ${baseAsset(symbol)}`}
              subtitle={c.market.pricePanelSubtitle}
            >
              <PriceChart points={series.price} color={color} />
              <ChartCaption>{c.market.priceCaption}</ChartCaption>
            </Panel>
          </Reveal>

          <Reveal delay={0.05}>
            <Panel
              title={c.market.volPanelTitle}
              subtitle={`${c.market.volPanelSubtitlePrefix} ${seriesFile?.volatility_window_days ?? 30} ${c.market.volPanelSubtitleSuffix}`}
            >
              <VolatilityChart
                points={series.volatility}
                color={color}
                median={median(series.volatility.map((point) => point.v))}
              />
              <ChartCaption>{c.market.volCaption}</ChartCaption>
            </Panel>
          </Reveal>

          {distribution && (
            <Reveal delay={0.05}>
              <Panel title={c.market.distPanelTitle} subtitle={c.market.distPanelSubtitle}>
                <div className="lg:grid lg:grid-cols-[1.6fr_1fr] lg:gap-8">
                  <div className="min-w-0">
                    <DistributionChart distribution={distribution} color={color} />
                    <ChartCaption>{c.market.distCaption}</ChartCaption>
                  </div>
                  <div className="mt-8 lg:mt-0">
                    <FatTails events={distribution.sigma_events} n={distribution.stats.n} />
                    <p className="mt-5 text-sm leading-relaxed text-muted">
                      {tpl(c.market.kurtosisText, {
                        kurtosis: fmtNumber(distribution.stats.excess_kurtosis, 1),
                        skew: fmtNumber(distribution.stats.skew, 2),
                      })}
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
