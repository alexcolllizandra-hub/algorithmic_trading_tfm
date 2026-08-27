"use client";

// Data & EDA, static-first: every primary chart is rendered live from the
// exported real datasets (market series, distributions, landing-extra
// structure blocks). The frozen matplotlib gallery — the artifacts the
// thesis cites — remains available as a collapsed annex served by the
// optional local API.

import { Suspense, useState } from "react";

import { EdaFigureAnnex } from "@/components/eda/EdaFigureAnnex";
import {
  ChartReading,
  EdaDistributionChart,
  EdaFundingChart,
  EdaPriceChart,
  EdaSeasonalityHeatmap,
  EdaSigmaTable,
  EdaUnderwaterChart,
  EdaVolatilityChart,
} from "@/components/eda/EdaCharts";
import { HowToRead } from "@/components/education/HowToRead";
import { InterpretationBox } from "@/components/education/InterpretationBox";
import { SectionIntro } from "@/components/education/SectionIntro";
import { PageShell } from "@/components/layout/PageShell";
import { useLandingExtra } from "@/components/landing/charts/extra";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type Column } from "@/components/ui/Table";
import { ErrorState, PartialNotice, Skeleton } from "@/components/ui/States";
import { StatCard } from "@/components/ui/StatCard";
import { cn } from "@/lib/cn";
import { fmtInt, fmtPercent } from "@/lib/format";
import { useI18n, useIntlLocale } from "@/lib/i18n";
import {
  baseAsset,
  useDistributions,
  useMarketSeries,
  useProvenance,
  useSummary,
  type ProvenanceDataset,
} from "@/lib/site-data";

function DatosEdaInner() {
  const t = useI18n();
  const intl = useIntlLocale();
  const [symbol, setSymbol] = useState("BTCUSDT");

  const { data: seriesFile, error: seriesError, isLoading } = useMarketSeries();
  const { data: distributionsFile } = useDistributions();
  const { data: summaryFile } = useSummary();
  const { data: provenance } = useProvenance();
  const { data: extra } = useLandingExtra();

  const series = seriesFile?.series.find((entry) => entry.symbol === symbol);
  const distribution = distributionsFile?.items.find(
    (item) => item.symbol === symbol && item.partition === "development"
  );
  const development = summaryFile?.items.filter((item) => item.partition === "development") ?? [];
  const symbols = seriesFile?.series.map((entry) => entry.symbol) ?? ["BTCUSDT", "ETHUSDT"];

  const barsTotal = development.reduce((total, item) => total + item.bars, 0);
  const coverage = development.length
    ? development.reduce((total, item) => total + item.coverage_pct, 0) / development.length
    : null;
  const span = development[0]
    ? `${development[0].start.slice(0, 7)} — ${development[0].end.slice(0, 7)}`
    : "—";

  const s = t.sections.datosEda;
  const ms = extra?.market_structure;
  const days = intl.startsWith("es")
    ? ["L", "M", "X", "J", "V", "S", "D"]
    : ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  const provColumns: Column<ProvenanceDataset>[] = [
    {
      key: "id",
      header: t.eda.colDataset,
      render: (d) => <span className="font-mono text-xs">{d.dataset_id}</span>,
    },
    {
      key: "partition",
      header: t.eda.colPartition,
      render: (d) => (
        <Badge tone={d.partition === "development" ? "positive" : "warn"}>
          {d.partition === "development" ? t.eda.partitionDev : t.eda.partitionHoldout}
        </Badge>
      ),
    },
    { key: "rows", header: t.eda.colRows, align: "right", render: (d) => fmtInt(d.rows) },
    {
      key: "span",
      header: t.eda.colSpan,
      render: (d) => `${d.start.slice(0, 10)} → ${d.end.slice(0, 10)}`,
    },
    {
      key: "sha",
      header: t.eda.colSha,
      render: (d) => (
        <span className="font-mono text-xs text-muted">{d.sha256?.slice(0, 16) ?? "—"}…</span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <SectionIntro title={s.title} subtitle={s.subtitle} questions={s} />
      <PartialNotice>{t.warnings.devPartitionOnly}</PartialNotice>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label={t.eda.statBars} value={barsTotal ? fmtInt(barsTotal) : "—"} />
        <StatCard
          label={t.eda.statCoverage}
          value={coverage == null ? "—" : `${coverage.toFixed(2)}%`}
        />
        <StatCard label={t.eda.statSpan} value={span} />
        <StatCard
          label={t.eda.statDatasets}
          value={provenance ? fmtInt(provenance.datasets.length) : "—"}
        />
      </div>

      <Card>
        <CardHeader title={t.eda.provenanceTitle} subtitle={t.eda.provenanceSubtitle} />
        {provenance ? (
          <DataTable
            columns={provColumns}
            rows={provenance.datasets}
            rowKey={(d) => d.dataset_id}
            dense
          />
        ) : (
          <Skeleton className="h-40" />
        )}
      </Card>

      {/* Asset selector for the per-symbol charts. */}
      <div className="flex flex-wrap items-center gap-3">
        <div
          role="tablist"
          aria-label={t.explorer.pickAsset}
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
                entry === symbol ? "bg-[var(--accent)] text-white" : "text-muted hover:text-fg"
              )}
            >
              {baseAsset(entry)}
            </button>
          ))}
        </div>
        <span className="font-mono text-xs text-muted">
          {symbol} · {seriesFile?.timeframe ?? "1h"}
        </span>
      </div>

      {seriesError && <ErrorState title={t.explorer.loadError} detail={seriesError.message} />}
      {isLoading && !seriesError && <Skeleton className="h-72" />}

      {series && (
        <>
          <Card>
            <CardHeader
              title={`${t.eda.priceTitle} · ${baseAsset(symbol)}`}
              subtitle={t.eda.priceSubtitle}
            />
            <EdaPriceChart series={series} />
            <ChartReading what={t.eda.priceWhat} why={t.eda.priceWhy} />
          </Card>

          <Card>
            <CardHeader
              title={t.eda.volTitle}
              subtitle={`${t.eda.volSubtitlePrefix} ${seriesFile?.volatility_window_days ?? 30} ${t.eda.volSubtitleSuffix}`}
            />
            <EdaVolatilityChart series={series} />
            <ChartReading what={t.eda.volWhat} why={t.eda.volWhy} />
          </Card>
        </>
      )}

      {distribution && (
        <Card>
          <CardHeader title={t.eda.distTitle} subtitle={t.eda.distSubtitle} />
          <div className="lg:grid lg:grid-cols-[1.6fr_1fr] lg:gap-8">
            <div className="min-w-0">
              <EdaDistributionChart item={distribution} />
            </div>
            <div className="mt-6 lg:mt-0">
              <EdaSigmaTable item={distribution} />
            </div>
          </div>
          <ChartReading what={t.eda.distWhat} why={t.eda.distWhy} />
        </Card>
      )}

      {ms && (
        <>
          <Card>
            <CardHeader title={t.eda.seasonTitle} subtitle="BTC · 2020–2025 · UTC" />
            <EdaSeasonalityHeatmap cells={ms.seasonality} days={days} />
            <ChartReading what={t.eda.seasonWhat} why={t.eda.seasonWhy} />
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader
                title={t.eda.uwTitle}
                subtitle={`max ${fmtPercent(ms.underwater_stats.max_drawdown, 0)} · ${fmtPercent(
                  ms.underwater_stats.share_below_peak,
                  1
                )}`}
              />
              <EdaUnderwaterChart points={ms.underwater} />
              <ChartReading what={t.eda.uwWhat} why={t.eda.uwWhy} />
            </Card>
            <Card>
              <CardHeader
                title={t.eda.fundingTitle}
                subtitle={`${fmtInt(ms.funding_stats.n_events)} · ${fmtPercent(
                  ms.funding_stats.share_positive,
                  1
                )} > 0`}
              />
              <EdaFundingChart points={ms.funding} />
              <ChartReading
                what={t.eda.fundingWhat}
                why={t.eda.fundingWhy.replace(
                  "{pct}",
                  fmtPercent(ms.funding_stats.annualised_mean, 1)
                )}
              />
            </Card>
          </div>
        </>
      )}

      <EdaFigureAnnex />

      <HowToRead>
        <p>{t.glossary.pilot.definition}</p>
        <p>{t.glossary.holdout.definition}</p>
      </HowToRead>

      <InterpretationBox tone="info">{s.queConcluirAnswer}</InterpretationBox>
    </div>
  );
}

export default function DatosEdaPage() {
  const t = useI18n();
  return (
    <PageShell title={t.sections.datosEda.title}>
      <Suspense fallback={<Skeleton className="h-72" />}>
        <DatosEdaInner />
      </Suspense>
    </PageShell>
  );
}
