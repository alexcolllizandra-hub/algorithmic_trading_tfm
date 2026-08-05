"use client";

import { Suspense, useEffect, useState } from "react";

import { EquityChart } from "@/components/charts/EquityChart";
import { PageShell } from "@/components/layout/PageShell";
import { RunPicker, useSelectedRun } from "@/components/RunPicker";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { ExploratoryBanner } from "@/components/ui/ExploratoryBanner";
import { DataTable, type Column } from "@/components/ui/Table";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/States";
import { StatCard } from "@/components/ui/StatCard";
import type { PerformanceFold, TradeModel } from "@/lib/api-types";
import { fmtInt, fmtNumber, fmtSignedPercent, fmtTimestamp, signClass } from "@/lib/format";
import { useEquity, usePerformance, useTrades } from "@/lib/hooks";

function csvEscape(v: unknown): string {
  const s = v == null ? "" : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function downloadTradesCsv(rows: TradeModel[], name: string) {
  const headers = [
    "trade_id",
    "entry_time",
    "exit_time",
    "n_bars",
    "position",
    "net_return",
    "funding",
    "cost",
    "exit_reason",
  ];
  const lines = [headers.join(",")];
  for (const r of rows) {
    const rec = r as unknown as Record<string, unknown>;
    lines.push(headers.map((h) => csvEscape(rec[h])).join(","));
  }
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

function PerformanceInner() {
  const runId = useSelectedRun();
  const { data: perf, error, isLoading } = usePerformance(runId);
  const [selected, setSelected] = useState<{ method: string; fold: number } | null>(null);

  useEffect(() => {
    if (perf?.folds && perf.folds.length > 0) {
      setSelected({ method: perf.folds[0].method, fold: perf.folds[0].fold });
    } else {
      setSelected(null);
    }
  }, [perf]);

  const foldColumns: Column<PerformanceFold>[] = [
    { key: "m", header: "Method", render: (f) => f.method },
    { key: "f", header: "Fold", align: "right", render: (f) => fmtInt(f.fold) },
    {
      key: "eq",
      header: "Final equity",
      align: "right",
      render: (f) => fmtNumber(f.final_equity, 4),
    },
    {
      key: "dd",
      header: "Max drawdown",
      align: "right",
      render: (f) => <span className="text-negative">{fmtSignedPercent(f.max_drawdown)}</span>,
    },
    { key: "nt", header: "Trades", align: "right", render: (f) => fmtInt(f.n_trades) },
    {
      key: "sel",
      header: "",
      align: "right",
      render: (f) => (
        <button
          onClick={() => setSelected({ method: f.method, fold: f.fold })}
          className="rounded border border-border px-2 py-0.5 text-xs text-accent hover:bg-accent/10"
        >
          view
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <RunPicker selected={runId} />
      <ExploratoryBanner kind={perf?.kind} message={perf?.warning} />

      {!runId ? (
        <EmptyState title="Select a run" />
      ) : isLoading ? (
        <Skeleton className="h-72" />
      ) : error ? (
        <ErrorState title="No performance" detail={error.message} />
      ) : !perf || perf.folds.length === 0 ? (
        <EmptyState
          title="No test-equity artifacts"
          hint="Fold-winner test equity/trades are written for the best method only."
        />
      ) : (
        <>
          <Card>
            <CardHeader
              title="Fold-winner test performance"
              subtitle="Out-of-sample (development) test windows"
            />
            <DataTable
              columns={foldColumns}
              rows={perf.folds}
              rowKey={(f) => `${f.method}-${f.fold}`}
              dense
            />
          </Card>

          {selected && <FoldDetail runId={runId!} method={selected.method} fold={selected.fold} />}
        </>
      )}
    </div>
  );
}

function FoldDetail({ runId, method, fold }: { runId: string; method: string; fold: number }) {
  const { data: eq } = useEquity(runId, method, fold);
  const { data: tr } = useTrades(runId, method, fold, 100);

  const tradeColumns: Column<TradeModel>[] = [
    { key: "id", header: "#", align: "right", render: (t) => fmtInt(t.trade_id) },
    { key: "entry", header: "Entry", render: (t) => fmtTimestamp(t.entry_time) },
    { key: "exit", header: "Exit", render: (t) => fmtTimestamp(t.exit_time) },
    { key: "bars", header: "Bars", align: "right", render: (t) => fmtInt(t.n_bars) },
    { key: "pos", header: "Pos", align: "right", render: (t) => fmtNumber(t.position, 0) },
    {
      key: "ret",
      header: "Net return",
      align: "right",
      render: (t) => (
        <span className={signClass(t.net_return)}>{fmtSignedPercent(t.net_return)}</span>
      ),
    },
    {
      key: "fund",
      header: "Funding",
      align: "right",
      render: (t) => fmtSignedPercent(t.funding, 4),
    },
    { key: "reason", header: "Exit reason", render: (t) => <Badge>{t.exit_reason ?? "—"}</Badge> },
  ];

  const last = eq?.points.at(-1);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard
          label="Final equity"
          value={fmtNumber(last?.equity, 4)}
          metricKey="total_return"
        />
        <StatCard
          label="Max drawdown"
          value={fmtSignedPercent(eq ? Math.min(...eq.points.map((p) => p.drawdown ?? 0)) : null)}
          metricKey="max_drawdown"
          valueClassName="text-negative"
        />
        <StatCard label="Bars" value={fmtInt(eq?.points.length)} />
        <StatCard label="Trades" value={fmtInt(tr?.items.length)} metricKey="n_trades" />
      </div>

      <Card>
        <CardHeader title={`Equity & drawdown — ${method} · fold ${fold}`} />
        {eq && eq.points.length > 0 ? (
          <EquityChart points={eq.points} />
        ) : (
          <EmptyState title="No equity" />
        )}
      </Card>

      <Card>
        <CardHeader
          title="Trades"
          right={
            tr && tr.items.length > 0 ? (
              <button
                onClick={() =>
                  downloadTradesCsv(tr.items, `${runId}_${method}_fold${fold}_trades.csv`)
                }
                className="rounded-md border border-border px-3 py-1 text-xs text-accent hover:bg-accent/10"
              >
                Export CSV
              </button>
            ) : undefined
          }
        />
        {tr && tr.items.length > 0 ? (
          <DataTable
            columns={tradeColumns}
            rows={tr.items}
            rowKey={(t) => String(t.trade_id)}
            dense
          />
        ) : (
          <EmptyState title="No trades in this fold" />
        )}
      </Card>
    </div>
  );
}

export default function PerformancePage() {
  return (
    <PageShell title="Performance">
      <Suspense fallback={<Skeleton className="h-72" />}>
        <PerformanceInner />
      </Suspense>
    </PageShell>
  );
}
