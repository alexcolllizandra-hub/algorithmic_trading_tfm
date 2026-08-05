"use client";

import { Suspense, useEffect, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { EquityChart } from "@/components/charts/EquityChart";
import { HowToRead } from "@/components/education/HowToRead";
import { InterpretationBox } from "@/components/education/InterpretationBox";
import { SectionIntro } from "@/components/education/SectionIntro";
import { PageShell } from "@/components/layout/PageShell";
import { RunPicker, useSelectedRun } from "@/components/RunPicker";
import { ContextBar } from "@/components/research/ContextBar";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { ExploratoryBanner } from "@/components/ui/ExploratoryBanner";
import { DataTable, type Column } from "@/components/ui/Table";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/States";
import { StatCard } from "@/components/ui/StatCard";
import type { FoldSelection, PerformanceFold, TradeModel } from "@/lib/api-types";
import { fmtInt, fmtNumber, fmtSignedPercent, fmtTimestamp, signClass } from "@/lib/format";
import { es } from "@/lib/i18n/es";
import { useEquity, usePerformance, useTrades } from "@/lib/hooks";

function positionLabel(pos: number | null | undefined): string {
  if (pos == null || pos === 0) return es.trades.flat;
  return pos > 0 ? es.trades.long : es.trades.short;
}

function csvEscape(v: unknown): string {
  const s = v == null ? "" : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function downloadTradesCsv(rows: TradeModel[], name: string) {
  const headers = ["trade_id", "entry_time", "exit_time", "position", "net_return", "exit_reason"];
  const lines = [headers.join(",")];
  for (const r of rows) {
    lines.push(
      [r.trade_id, r.entry_time, r.exit_time, r.position, r.net_return, r.exit_reason]
        .map(csvEscape)
        .join(",")
    );
  }
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

function ResultadosInner() {
  const params = useSearchParams();
  const router = useRouter();
  const runId = useSelectedRun();
  const method = params.get("method") ?? "";
  const foldParam = params.get("fold");
  const fold = foldParam != null ? Number(foldParam) : NaN;

  const { data: perf, error, isLoading } = usePerformance(runId);

  useEffect(() => {
    if (!runId || !perf?.folds.length) return;
    const sp = new URLSearchParams(params.toString());
    let changed = false;
    if (!method) {
      sp.set("method", perf.folds[0].method);
      changed = true;
    }
    if (!foldParam) {
      sp.set("fold", String(perf.folds[0].fold));
      changed = true;
    }
    if (changed) router.replace(`/resultados?${sp.toString()}`);
  }, [runId, perf, method, foldParam, params, router]);

  const selectedFold = perf?.folds.find((f) => f.method === method && f.fold === fold) ?? null;

  const selection: FoldSelection | null =
    runId && method && Number.isFinite(fold) && selectedFold
      ? {
          runId,
          method,
          fold,
          candidateId: selectedFold.candidate_id,
          periodStart: selectedFold.period_start,
          periodEnd: selectedFold.period_end,
        }
      : runId && method && Number.isFinite(fold)
        ? { runId, method, fold, candidateId: null, periodStart: null, periodEnd: null }
        : null;

  const setSelection = (f: PerformanceFold) => {
    const sp = new URLSearchParams(params.toString());
    sp.set("run", runId!);
    sp.set("method", f.method);
    sp.set("fold", String(f.fold));
    router.replace(`/resultados?${sp.toString()}`);
  };

  const foldColumns: Column<PerformanceFold>[] = [
    { key: "m", header: "Método", render: (f) => f.method },
    { key: "f", header: "Fold", align: "right", render: (f) => fmtInt(f.fold) },
    {
      key: "eq",
      header: "Equity final",
      align: "right",
      render: (f) => fmtNumber(f.final_equity, 4),
    },
    {
      key: "dd",
      header: "Max DD",
      align: "right",
      render: (f) => <span className="text-negative">{fmtSignedPercent(f.max_drawdown)}</span>,
    },
    { key: "nt", header: "Ops", align: "right", render: (f) => fmtInt(f.n_trades) },
    {
      key: "cand",
      header: "Candidato",
      render: (f) => <span className="font-mono text-xs">{f.candidate_id ?? "—"}</span>,
    },
    {
      key: "per",
      header: "Periodo",
      render: (f) =>
        f.period_start && f.period_end
          ? `${f.period_start.slice(0, 10)} → ${f.period_end.slice(0, 10)}`
          : "—",
    },
    {
      key: "sel",
      header: "",
      align: "right",
      render: (f) => (
        <button
          type="button"
          onClick={() => setSelection(f)}
          className="rounded border border-border px-2 py-0.5 text-xs text-accent hover:bg-accent/10"
        >
          ver
        </button>
      ),
    },
  ];

  const aggregateRows = useMemo(() => {
    if (!perf?.aggregate) return [];
    return Object.entries(perf.aggregate).flatMap(([methodKey, metrics]) =>
      Object.entries(metrics).map(([metric, value]) => ({
        method: methodKey,
        metric,
        value,
      }))
    );
  }, [perf]);

  const s = es.sections.resultados;

  return (
    <div className="space-y-6">
      <SectionIntro title={s.title} subtitle={s.subtitle} questions={s} />
      <RunPicker selected={runId} />
      <ExploratoryBanner kind={perf?.kind} message={perf?.warning ?? es.warnings.exploratory} />

      {!runId ? (
        <EmptyState title={es.common.selectRun} />
      ) : isLoading ? (
        <Skeleton className="h-72" />
      ) : error ? (
        <ErrorState title="Sin rendimiento" detail={error.message} />
      ) : !perf || perf.folds.length === 0 ? (
        <EmptyState title="Sin artefactos de equity test" />
      ) : (
        <>
          <ContextBar selection={selection} />

          {aggregateRows.length > 0 && (
            <Card>
              <CardHeader
                title="Resultados agregados OOS"
                subtitle={`Mejor método: ${perf.best_method ?? "—"}`}
              />
              <DataTable
                columns={[
                  { key: "m", header: "Método", render: (r) => r.method },
                  { key: "metric", header: "Métrica", render: (r) => r.metric },
                  {
                    key: "v",
                    header: "Valor",
                    align: "right",
                    render: (r) => fmtNumber(r.value, 4),
                  },
                ]}
                rows={aggregateRows}
                rowKey={(r) => `${r.method}-${r.metric}`}
                dense
              />
            </Card>
          )}

          <Card>
            <CardHeader title="Rendimiento por fold (ventana test)" />
            <DataTable
              columns={foldColumns}
              rows={perf.folds}
              rowKey={(f) => `${f.method}-${f.fold}`}
              dense
            />
          </Card>

          {selection && Number.isFinite(fold) && (
            <FoldDetail selection={selection} tableFold={selectedFold} />
          )}
        </>
      )}

      <HowToRead>
        <p>{s.porQueAnswer}</p>
        <p>{es.glossary.oos.definition}</p>
      </HowToRead>
    </div>
  );
}

function FoldDetail({
  selection,
  tableFold,
}: {
  selection: FoldSelection;
  tableFold: PerformanceFold | null;
}) {
  const { runId, method, fold } = selection;

  const { data: eqProbe } = useEquity(runId, method, fold, 10000);
  const fullLimit =
    eqProbe && eqProbe.summary.n_points_total > eqProbe.meta.returned
      ? eqProbe.summary.n_points_total
      : undefined;
  const { data: equity } = useEquity(runId, method, fold, fullLimit);
  const eq = equity ?? eqProbe;

  const { data: tr } = useTrades(runId, method, fold, 100);

  const summary = eq?.summary;
  const lastPoint = eq?.points.at(-1);

  const computedFinal = lastPoint?.equity ?? null;
  const computedDd =
    eq && eq.points.length > 0 ? Math.min(...eq.points.map((p) => p.drawdown ?? 0)) : null;

  const integrityIssues: string[] = [];
  if (summary && computedFinal != null && summary.final_equity != null) {
    if (Math.abs(computedFinal - summary.final_equity) > 1e-6) {
      integrityIssues.push(
        `final_equity: summary=${summary.final_equity}, puntos=${computedFinal}`
      );
    }
  }
  if (summary && computedDd != null && summary.max_drawdown != null) {
    if (Math.abs(computedDd - summary.max_drawdown) > 1e-6) {
      integrityIssues.push(`max_drawdown: summary=${summary.max_drawdown}, puntos=${computedDd}`);
    }
  }
  if (tableFold && summary) {
    if (tableFold.final_equity != null && summary.final_equity != null) {
      if (Math.abs(tableFold.final_equity - summary.final_equity) > 1e-6) {
        integrityIssues.push(
          `tabla vs summary equity: ${tableFold.final_equity} ≠ ${summary.final_equity}`
        );
      }
    }
    if (tableFold.max_drawdown != null && summary.max_drawdown != null) {
      if (Math.abs(tableFold.max_drawdown - summary.max_drawdown) > 1e-6) {
        integrityIssues.push(
          `tabla vs summary DD: ${tableFold.max_drawdown} ≠ ${summary.max_drawdown}`
        );
      }
    }
  }
  if (eq && summary && eq.meta.returned < summary.n_points_total) {
    integrityIssues.push(
      `paginación incompleta: ${eq.meta.returned}/${summary.n_points_total} puntos`
    );
  }

  const tradeColumns: Column<TradeModel>[] = [
    { key: "id", header: "#", align: "right", render: (t) => fmtInt(t.trade_id) },
    { key: "entry", header: "Entrada", render: (t) => fmtTimestamp(t.entry_time) },
    { key: "exit", header: "Salida", render: (t) => fmtTimestamp(t.exit_time) },
    {
      key: "pos",
      header: "Posición",
      render: (t) => (
        <Badge
          tone={
            t.position != null && t.position > 0
              ? "positive"
              : t.position != null && t.position < 0
                ? "negative"
                : "neutral"
          }
        >
          {positionLabel(t.position)}
        </Badge>
      ),
    },
    {
      key: "ret",
      header: "Retorno neto",
      align: "right",
      render: (t) => (
        <span className={signClass(t.net_return)}>{fmtSignedPercent(t.net_return)}</span>
      ),
    },
    { key: "reason", header: "Salida", render: (t) => <Badge>{t.exit_reason ?? "—"}</Badge> },
  ];

  return (
    <div className="space-y-6">
      {integrityIssues.length > 0 && (
        <InterpretationBox tone="error" title={es.warnings.integrityMismatch}>
          <ul className="list-inside list-disc space-y-1">
            {integrityIssues.map((msg) => (
              <li key={msg}>{msg}</li>
            ))}
          </ul>
        </InterpretationBox>
      )}

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard
          label="Equity final"
          value={fmtNumber(summary?.final_equity, 4)}
          metricKey="total_return"
        />
        <StatCard
          label="Max drawdown"
          value={fmtSignedPercent(summary?.max_drawdown)}
          metricKey="max_drawdown"
          valueClassName="text-negative"
        />
        <StatCard label="Barras (serie)" value={fmtInt(summary?.n_points_total)} />
        <StatCard
          label="Operaciones"
          value={fmtInt(tr?.meta.total ?? tr?.items.length)}
          metricKey="n_trades"
        />
      </div>

      <Card>
        <CardHeader title={`Equity y drawdown — ${method} · fold ${fold}`} />
        {eq && eq.points.length > 0 ? (
          <EquityChart points={eq.points} />
        ) : (
          <EmptyState title="Sin curva de equity" />
        )}
      </Card>

      <Card>
        <CardHeader
          title="Operaciones"
          right={
            tr && tr.items.length > 0 ? (
              <button
                type="button"
                onClick={() =>
                  downloadTradesCsv(tr.items, `${runId}_${method}_fold${fold}_trades.csv`)
                }
                className="rounded-md border border-border px-3 py-1 text-xs text-accent hover:bg-accent/10"
              >
                {es.trades.exportCsv}
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
          <EmptyState title="Sin operaciones en este fold" />
        )}
      </Card>
    </div>
  );
}

export default function ResultadosPage() {
  return (
    <PageShell title={es.sections.resultados.title}>
      <Suspense fallback={<Skeleton className="h-72" />}>
        <ResultadosInner />
      </Suspense>
    </PageShell>
  );
}
