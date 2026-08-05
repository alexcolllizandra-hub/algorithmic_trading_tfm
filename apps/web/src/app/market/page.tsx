"use client";

import dynamic from "next/dynamic";
import { useMemo, useState } from "react";

import { PageShell } from "@/components/layout/PageShell";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type Column } from "@/components/ui/Table";
import { EmptyState, ErrorState, PartialNotice, Skeleton } from "@/components/ui/States";
import type { DatasetCoverage } from "@/lib/api-types";
import { fmtDate, fmtInt } from "@/lib/format";
import { useMarketCoverage, useOhlcv } from "@/lib/hooks";

// Candlestick chart is client-only (canvas); load without SSR.
const CandlestickChart = dynamic(
  () => import("@/components/charts/CandlestickChart").then((m) => m.CandlestickChart),
  { ssr: false, loading: () => <Skeleton className="h-[420px]" /> }
);

const SYMBOLS = ["BTCUSDT", "ETHUSDT"];
const TIMEFRAMES = ["1h", "15m", "5m"];

export default function MarketPage() {
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [timeframe, setTimeframe] = useState("1h");
  const { data: coverage, error: covError, isLoading: covLoading } = useMarketCoverage();
  const {
    data: ohlcv,
    error: ohlcvError,
    isLoading: ohlcvLoading,
  } = useOhlcv(symbol, timeframe, 1500);

  const klineRows = useMemo(
    () =>
      (coverage?.datasets ?? []).filter(
        (d) => d.stream === "klines" && !d.dataset_id.includes("holdout")
      ),
    [coverage]
  );

  const columns: Column<DatasetCoverage>[] = [
    {
      key: "id",
      header: "Dataset",
      render: (d) => <span className="font-mono text-xs">{d.dataset_id}</span>,
    },
    {
      key: "class",
      header: "Authenticity",
      render: (d) => (
        <Badge tone={d.classification === "REAL_HISTORICAL" ? "positive" : "warn"}>
          {d.classification}
        </Badge>
      ),
    },
    { key: "sym", header: "Symbol", render: (d) => `${d.symbol ?? "—"} ${d.timeframe ?? ""}` },
    { key: "rows", header: "Rows", align: "right", render: (d) => fmtInt(d.row_count) },
    { key: "min", header: "From", render: (d) => fmtDate(d.min_timestamp) },
    { key: "max", header: "To", render: (d) => fmtDate(d.max_timestamp) },
    {
      key: "hold",
      header: "Holdout",
      align: "center",
      render: (d) =>
        d.crosses_holdout ? (
          <Badge tone="negative">crosses</Badge>
        ) : (
          <Badge tone="positive">dev-only</Badge>
        ),
    },
  ];

  return (
    <PageShell title="Market Overview">
      <Card>
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col gap-1">
            <label htmlFor="m-symbol" className="text-xs text-muted">
              Symbol
            </label>
            <select
              id="m-symbol"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm"
            >
              {SYMBOLS.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="m-tf" className="text-xs text-muted">
              Timeframe
            </label>
            <select
              id="m-tf"
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm"
            >
              {TIMEFRAMES.map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
          </div>
          <PartialNotice>
            Development partition only — frozen-holdout observations are never served.
          </PartialNotice>
        </div>
      </Card>

      <Card>
        <CardHeader
          title={`${symbol} ${timeframe} — development candles`}
          subtitle={
            ohlcv
              ? `${ohlcv.bars.length} bars · holdout excluded: ${String(ohlcv.holdout_excluded)}`
              : undefined
          }
        />
        {ohlcvLoading ? (
          <Skeleton className="h-[420px]" />
        ) : ohlcvError ? (
          <ErrorState title="No OHLCV" detail={ohlcvError.message} />
        ) : ohlcv && ohlcv.bars.length > 0 ? (
          <CandlestickChart bars={ohlcv.bars} />
        ) : (
          <EmptyState title="No bars for this symbol/timeframe" />
        )}
      </Card>

      <Card>
        <CardHeader
          title="Data coverage & authenticity"
          subtitle={`Holdout starts ${coverage?.holdout_start?.slice(0, 10) ?? "—"}`}
        />
        {covLoading ? (
          <Skeleton className="h-48" />
        ) : covError ? (
          <ErrorState title="No coverage" detail={covError.message} />
        ) : klineRows.length === 0 ? (
          <EmptyState title="No datasets" />
        ) : (
          <DataTable columns={columns} rows={klineRows} rowKey={(d) => d.dataset_id} dense />
        )}
      </Card>
    </PageShell>
  );
}
