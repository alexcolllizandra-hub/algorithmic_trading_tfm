"use client";

import { Suspense, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { ConvergencePanel } from "@/components/ConvergencePanel";
import { ComparisonBars } from "@/components/charts/ComparisonBars";
import { DiversityChart } from "@/components/charts/DiversityChart";
import { HowToRead } from "@/components/education/HowToRead";
import { SectionIntro } from "@/components/education/SectionIntro";
import { PageShell } from "@/components/layout/PageShell";
import { RunPicker, useSelectedRun } from "@/components/RunPicker";
import { FairnessPanel } from "@/components/research/FairnessPanel";
import { RunPerformanceSection } from "@/components/research/RunPerformance";
import { Badge, RunKindBadge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { ExploratoryBanner } from "@/components/ui/ExploratoryBanner";
import { DataTable, type Column } from "@/components/ui/Table";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/States";
import { InfoTip } from "@/components/ui/Tooltip";
import type {
  CandidateModel,
  FoldWinnerModel,
  MethodComparison,
  RunSummary,
} from "@/lib/api-types";
import { useI18n } from "@/lib/i18n";
import { fmtInt, fmtRatio, fmtSignedPercent, signClass } from "@/lib/format";
import { metricHelp } from "@/lib/metrics";
import { useAnalytics, useCandidates, useComparison, useFolds, useRun, useRuns } from "@/lib/hooks";

type MainTab = "lista" | "detalle" | "rendimiento" | "analytics" | "fairness";
type DetailTab = "comparison" | "candidates" | "folds";
type Method = "random_search" | "genetic_algorithm";

const FAMILIES = ["", "momentum", "breakout", "mean_reversion"];
const KINDS = ["", "development", "synthetic-smoke", "final-holdout"];

function ExperimentosInner() {
  const t = useI18n();
  const params = useSearchParams();
  const router = useRouter();
  const runId = useSelectedRun();
  const tab = (params.get("tab") as MainTab) || (runId ? "detalle" : "lista");

  const setTab = (t: MainTab) => {
    const sp = new URLSearchParams(params.toString());
    sp.set("tab", t);
    router.replace(`/experimentos?${sp.toString()}`);
  };

  const s = t.sections.experimentos;

  return (
    <div className="space-y-6">
      <SectionIntro title={s.title} subtitle={s.subtitle} questions={s} />
      <RunPicker selected={runId} />

      <div className="flex flex-wrap gap-1 border-b border-border">
        {(
          [
            ["lista", "Lista"],
            ["detalle", "Detalle"],
            ["rendimiento", "Rendimiento"],
            ["analytics", "Analytics"],
            ["fairness", "Validez"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`px-4 py-2 text-sm ${
              tab === id ? "border-b-2 border-accent text-fg" : "text-muted hover:text-fg"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "lista" && <RunsList />}
      {tab === "detalle" && <RunDetail runId={runId} />}
      {tab === "rendimiento" && <RunPerformanceSection />}
      {tab === "analytics" && <AnalyticsTab runId={runId} />}
      {tab === "fairness" && <FairnessPanel runId={runId} />}

      <HowToRead>
        <p>{t.glossary.fairBudget.definition}</p>
        <p>{t.glossary.oos.definition}</p>
      </HowToRead>
    </div>
  );
}

function RunsList() {
  const { data, error, isLoading } = useRuns();
  const [family, setFamily] = useState("");
  const [kind, setKind] = useState("");
  const [query, setQuery] = useState("");

  const rows = useMemo(() => {
    let items = data?.items ?? [];
    if (family) items = items.filter((r) => r.family === family);
    if (kind) items = items.filter((r) => r.kind === kind);
    if (query) items = items.filter((r) => r.run_id.toLowerCase().includes(query.toLowerCase()));
    return items;
  }, [data, family, kind, query]);

  const columns: Column<RunSummary>[] = [
    {
      key: "run",
      header: "Run",
      render: (r) => <span className="font-mono text-xs">{r.run_id}</span>,
    },
    { key: "kind", header: "Tipo", render: (r) => <RunKindBadge kind={r.kind} /> },
    { key: "family", header: "Familia", render: (r) => r.family },
    { key: "symbol", header: "Símbolo", render: (r) => `${r.symbol} ${r.timeframe}` },
    { key: "folds", header: "Folds", align: "right", render: (r) => fmtInt(r.n_folds) },
    { key: "budget", header: "Budget", align: "right", render: (r) => fmtInt(r.budget) },
    {
      key: "best",
      header: "Mejor OOS",
      render: (r) => (r.best_method ? <Badge tone="accent">{r.best_method}</Badge> : "—"),
    },
  ];

  return (
    <>
      <Card>
        <div className="flex flex-wrap items-end gap-4">
          <FilterSelect
            id="f-family"
            label="Familia"
            value={family}
            options={FAMILIES}
            onChange={setFamily}
            allLabel="Todas"
          />
          <FilterSelect
            id="f-kind"
            label="Tipo"
            value={kind}
            options={KINDS}
            onChange={setKind}
            allLabel="Todos"
          />
          <div className="flex flex-1 flex-col gap-1">
            <label htmlFor="f-query" className="text-xs text-muted">
              Buscar run
            </label>
            <input
              id="f-query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full rounded-md border border-border bg-surface px-3 py-1.5 text-sm"
            />
          </div>
          <span className="text-sm text-muted">{rows.length} runs</span>
        </div>
      </Card>
      {isLoading ? (
        <Skeleton className="h-64" />
      ) : error ? (
        <ErrorState title="Error al cargar runs" detail={error.message} />
      ) : rows.length === 0 ? (
        <EmptyState title="Sin runs" />
      ) : (
        <DataTable columns={columns} rows={rows} rowKey={(r) => r.run_id} />
      )}
    </>
  );
}

function FilterSelect({
  id,
  label,
  value,
  options,
  onChange,
  allLabel,
}: {
  id: string;
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
  allLabel: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs text-muted">
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o || allLabel}
          </option>
        ))}
      </select>
    </div>
  );
}

function RunDetail({ runId }: { runId: string | null }) {
  const t = useI18n();
  const [tab, setTab] = useState<DetailTab>("comparison");
  const { data: run, error, isLoading } = useRun(runId);

  if (!runId) return <EmptyState title={t.common.selectRun} />;
  if (isLoading) return <Skeleton className="h-40" />;
  if (error) return <ErrorState title="Run no encontrado" detail={error.message} />;

  return (
    <>
      <div className="flex items-center gap-3">
        <span className="font-mono text-sm">{runId}</span>
        {run && <RunKindBadge kind={run.kind} />}
      </div>
      <ExploratoryBanner kind={run?.kind} />
      <div className="flex gap-1 border-b border-border">
        {(["comparison", "candidates", "folds"] as DetailTab[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm capitalize ${
              tab === t ? "border-b-2 border-accent text-fg" : "text-muted hover:text-fg"
            }`}
          >
            {t === "comparison" ? "Comparación" : t === "candidates" ? "Candidatos" : "Folds"}
          </button>
        ))}
      </div>
      {tab === "comparison" && <ComparisonTab runId={runId} />}
      {tab === "candidates" && (
        <CandidatesTab runId={runId} methods={run?.available_methods ?? []} />
      )}
      {tab === "folds" && <FoldsTab runId={runId} />}
    </>
  );
}

function ComparisonTab({ runId }: { runId: string }) {
  const { data, error, isLoading } = useComparison(runId);
  if (isLoading) return <Skeleton className="h-64" />;
  if (error) return <ErrorState title="Sin comparación" detail={error.message} />;
  if (!data) return <EmptyState title="Sin artefacto de comparación" />;

  const columns: Column<MethodComparison>[] = [
    { key: "method", header: "Método", render: (m) => m.method },
    { key: "evaluated", header: "Evaluados", align: "right", render: (m) => fmtInt(m.evaluated) },
    { key: "feasible", header: "Factibles", align: "right", render: (m) => fmtInt(m.feasible) },
    {
      key: "val",
      header: "Mejor val fitness",
      align: "right",
      render: (m) => fmtRatio(m.best_val_fitness),
    },
    {
      key: "oos",
      header: "Sharpe OOS medio",
      align: "right",
      render: (m) => (
        <span className={signClass(m.mean_test_sharpe)}>{fmtRatio(m.mean_test_sharpe)}</span>
      ),
    },
    {
      key: "ret",
      header: "Retorno OOS medio",
      align: "right",
      render: (m) => (
        <span className={signClass(m.mean_test_total_return)}>
          {fmtSignedPercent(m.mean_test_total_return)}
        </span>
      ),
    },
    {
      key: "winners",
      header: "Ganadores fold",
      align: "right",
      render: (m) => fmtInt(m.n_fold_winners),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader
            title="Comparación de métodos"
            subtitle={data.comparison_metric ?? undefined}
            right={
              data.best_out_of_sample_method ? (
                <Badge tone="accent">Mejor OOS: {data.best_out_of_sample_method}</Badge>
              ) : undefined
            }
          />
          <DataTable columns={columns} rows={data.methods} rowKey={(m) => m.method} />
        </Card>
        <Card>
          <CardHeader title="Sharpe OOS agregado" />
          <ComparisonBars methods={data.methods} />
        </Card>
      </div>
      <Card>
        <CardHeader
          title={
            <span className="inline-flex items-center">
              Verificación presupuesto equitativo
              <InfoTip text={metricHelp("budget") ?? ""} label="budget" />
            </span>
          }
          subtitle={data.fair_budget.definition ?? undefined}
          right={
            <Badge tone={data.fair_budget.ok ? "positive" : "negative"}>
              {data.fair_budget.ok ? "COINCIDE" : "DISCREPANCIA"}
            </Badge>
          }
        />
        <DataTable
          columns={[
            { key: "m", header: "Método", render: (r) => r.method },
            { key: "e", header: "Evaluados", align: "right", render: (r) => fmtInt(r.evaluated) },
            {
              key: "ok",
              header: "En budget",
              align: "center",
              render: (r) => (
                <Badge tone={r.within_budget ? "positive" : "negative"}>
                  {r.within_budget ? "sí" : "no"}
                </Badge>
              ),
            },
          ]}
          rows={data.fair_budget.rows}
          rowKey={(r) => r.method}
          dense
        />
      </Card>
    </div>
  );
}

function CandidatesTab({ runId, methods }: { runId: string; methods: string[] }) {
  const available = methods.filter(
    (m) => m === "random_search" || m === "genetic_algorithm"
  ) as Method[];
  const [method, setMethod] = useState<Method>(available[0] ?? "random_search");
  const { data, error, isLoading } = useCandidates(runId, method, 50);

  const columns: Column<CandidateModel>[] = [
    {
      key: "id",
      header: "Candidato",
      render: (c) => <span className="font-mono text-xs">{c.candidate_id}</span>,
    },
    {
      key: "status",
      header: "Estado",
      render: (c) => (
        <Badge tone={c.status === "evaluated" ? "positive" : "warn"}>{c.status}</Badge>
      ),
    },
    {
      key: "fit",
      header: "Fitness",
      align: "right",
      render: (c) => <span className={signClass(c.fitness)}>{fmtRatio(c.fitness)}</span>,
    },
    {
      key: "val",
      header: "Sharpe val medio",
      align: "right",
      render: (c) => fmtRatio(c.mean_val_sharpe),
    },
  ];

  return (
    <Card>
      <CardHeader
        title="Ranking de candidatos"
        subtitle="Ordenados por fitness de validación"
        right={
          <div className="flex gap-1">
            {available.map((mth) => (
              <button
                key={mth}
                type="button"
                onClick={() => setMethod(mth)}
                className={`rounded-md border px-3 py-1 text-xs ${
                  method === mth
                    ? "border-accent bg-accent/15 text-accent"
                    : "border-border text-muted"
                }`}
              >
                {mth}
              </button>
            ))}
          </div>
        }
      />
      {isLoading ? (
        <Skeleton className="h-48" />
      ) : error ? (
        <ErrorState title="Sin candidatos" detail={error.message} />
      ) : !data || data.items.length === 0 ? (
        <EmptyState title="Sin candidatos" />
      ) : (
        <DataTable columns={columns} rows={data.items} rowKey={(c) => c.candidate_id} dense />
      )}
    </Card>
  );
}

function FoldsTab({ runId }: { runId: string }) {
  const { data, error, isLoading } = useFolds(runId);
  if (isLoading) return <Skeleton className="h-64" />;
  if (error) return <ErrorState title="Sin folds" detail={error.message} />;
  if (!data) return <EmptyState title="Sin artefacto de folds" />;

  const winnerColumns: Column<FoldWinnerModel>[] = [
    { key: "f", header: "Fold", render: (w) => fmtInt(w.fold) },
    {
      key: "w",
      header: "Ganador",
      render: (w) => <span className="font-mono text-xs">{w.winner ?? "—"}</span>,
    },
    {
      key: "ts",
      header: "Sharpe test",
      align: "right",
      render: (w) => <span className={signClass(w.test_sharpe)}>{fmtRatio(w.test_sharpe)}</span>,
    },
    {
      key: "tr",
      header: "Retorno test",
      align: "right",
      render: (w) => (
        <span className={signClass(w.test_total_return)}>
          {fmtSignedPercent(w.test_total_return)}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Particiones walk-forward"
          subtitle={`Regímenes: ${data.regime_inputs.join(", ") || "—"}`}
        />
        <DataTable
          columns={[
            { key: "f", header: "Fold", render: (f) => fmtInt(f.fold) },
            {
              key: "tr",
              header: "Train",
              render: (f) => `${f.train_start?.slice(0, 10)} → ${f.train_end?.slice(0, 10)}`,
            },
            {
              key: "va",
              header: "Val",
              render: (f) => `${f.val_start?.slice(0, 10)} → ${f.val_end?.slice(0, 10)}`,
            },
            {
              key: "te",
              header: "Test",
              render: (f) => `${f.test_start?.slice(0, 10)} → ${f.test_end?.slice(0, 10)}`,
            },
          ]}
          rows={data.folds}
          rowKey={(f) => String(f.fold)}
          dense
        />
      </Card>
      {Object.entries(data.winners).map(([method, winners]) => (
        <Card key={method}>
          <CardHeader title={`Ganadores por fold — ${method}`} />
          <DataTable
            columns={winnerColumns}
            rows={winners}
            rowKey={(w) => `${method}-${w.fold}`}
            dense
          />
        </Card>
      ))}
    </div>
  );
}

function AnalyticsTab({ runId }: { runId: string | null }) {
  const t = useI18n();
  const { data, error, isLoading } = useAnalytics(runId);
  if (!runId) return <EmptyState title={t.common.selectRun} />;
  if (isLoading) return <Skeleton className="h-72" />;
  if (error) return <ErrorState title="Sin analytics" detail={error.message} />;
  if (!data) return <EmptyState title="Sin artefacto analytics" />;

  return (
    <>
      <ConvergencePanel
        series={data.convergence}
        folds={data.convergence_folds}
        title="Convergencia"
        subtitle="Mejor fitness tras cada evaluación única dentro de un fold. Cada fold se busca de forma independiente, así que las trazas no son comparables entre folds."
        emptyTitle="Sin historial de convergencia"
        foldLabel="Fold externo"
      />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Diversidad GA" />
          {data.ga_diversity.length === 0 ? (
            <EmptyState title="Sin diversidad GA" />
          ) : (
            <DiversityChart data={data.ga_diversity} />
          )}
        </Card>
        <Card>
          <CardHeader title="Linaje GA" />
          {data.ga_lineage.length === 0 ? (
            <EmptyState title="Sin linaje" />
          ) : (
            <DataTable
              columns={[
                { key: "g", header: "Gen", render: (r) => String(r.generation ?? "—") },
                {
                  key: "c",
                  header: "Hijo",
                  render: (r) => (
                    <span className="font-mono text-xs">{String(r.child ?? "—")}</span>
                  ),
                },
              ]}
              rows={data.ga_lineage.slice(0, 40)}
              rowKey={(_r, i) => String(i)}
              dense
            />
          )}
        </Card>
      </div>
    </>
  );
}

export default function ExperimentosPage() {
  const t = useI18n();
  return (
    <PageShell title={t.sections.experimentos.title}>
      <Suspense fallback={<Skeleton className="h-72" />}>
        <ExperimentosInner />
      </Suspense>
    </PageShell>
  );
}
