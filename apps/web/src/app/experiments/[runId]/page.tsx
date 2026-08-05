"use client";

import Link from "next/link";
import { useState } from "react";

import { ComparisonBars } from "@/components/charts/ComparisonBars";
import { PageShell } from "@/components/layout/PageShell";
import { Badge, RunKindBadge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { ExploratoryBanner } from "@/components/ui/ExploratoryBanner";
import { DataTable, type Column } from "@/components/ui/Table";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/States";
import { InfoTip } from "@/components/ui/Tooltip";
import type { CandidateModel, FoldWinnerModel, MethodComparison } from "@/lib/api-types";
import { fmtInt, fmtRatio, fmtSignedPercent, signClass } from "@/lib/format";
import { metricHelp } from "@/lib/metrics";
import { useCandidates, useComparison, useFolds, useRun } from "@/lib/hooks";

type Tab = "comparison" | "candidates" | "folds";
type Method = "random_search" | "genetic_algorithm";

export default function RunDetailPage({ params }: { params: { runId: string } }) {
  const runId = decodeURIComponent(params.runId);
  const [tab, setTab] = useState<Tab>("comparison");
  const { data: run, error, isLoading } = useRun(runId);

  return (
    <PageShell title="Experiment detail">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link href="/experiments" className="text-sm text-accent hover:underline">
            ← Experiments
          </Link>
          <span className="font-mono text-sm">{runId}</span>
          {run && <RunKindBadge kind={run.kind} />}
        </div>
      </div>

      <ExploratoryBanner kind={run?.kind} />

      {isLoading ? (
        <Skeleton className="h-40" />
      ) : error ? (
        <ErrorState title="Run not found" detail={error.message} />
      ) : (
        <>
          <div className="flex gap-1 border-b border-border">
            {(["comparison", "candidates", "folds"] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-4 py-2 text-sm capitalize ${
                  tab === t ? "border-b-2 border-accent text-fg" : "text-muted hover:text-fg"
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          {tab === "comparison" && <ComparisonTab runId={runId} />}
          {tab === "candidates" && (
            <CandidatesTab runId={runId} methods={run?.available_methods ?? []} />
          )}
          {tab === "folds" && <FoldsTab runId={runId} />}
        </>
      )}
    </PageShell>
  );
}

function ComparisonTab({ runId }: { runId: string }) {
  const { data, error, isLoading } = useComparison(runId);
  if (isLoading) return <Skeleton className="h-64" />;
  if (error) return <ErrorState title="No comparison" detail={error.message} />;
  if (!data) return <EmptyState title="No comparison artifact" />;

  const columns: Column<MethodComparison>[] = [
    { key: "method", header: "Method", render: (m) => m.method },
    { key: "evaluated", header: "Evaluated", align: "right", render: (m) => fmtInt(m.evaluated) },
    { key: "feasible", header: "Feasible", align: "right", render: (m) => fmtInt(m.feasible) },
    {
      key: "val",
      header: "Best val fitness",
      align: "right",
      render: (m) => fmtRatio(m.best_val_fitness),
    },
    {
      key: "oos",
      header: "Mean OOS test Sharpe",
      align: "right",
      render: (m) => (
        <span className={signClass(m.mean_test_sharpe)}>{fmtRatio(m.mean_test_sharpe)}</span>
      ),
    },
    {
      key: "ret",
      header: "Mean OOS return",
      align: "right",
      render: (m) => (
        <span className={signClass(m.mean_test_total_return)}>
          {fmtSignedPercent(m.mean_test_total_return)}
        </span>
      ),
    },
    {
      key: "winners",
      header: "Fold winners",
      align: "right",
      render: (m) => fmtInt(m.n_fold_winners),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader
            title="Method comparison"
            subtitle={data.comparison_metric ?? undefined}
            right={
              data.best_out_of_sample_method ? (
                <Badge tone="accent">Best OOS: {data.best_out_of_sample_method}</Badge>
              ) : undefined
            }
          />
          <DataTable columns={columns} rows={data.methods} rowKey={(m) => m.method} />
        </Card>
        <Card>
          <CardHeader
            title="Out-of-sample Sharpe"
            subtitle="Aggregated test Sharpe of per-fold winners"
          />
          <ComparisonBars methods={data.methods} />
        </Card>
      </div>

      <Card>
        <CardHeader
          title={
            <span className="inline-flex items-center">
              Fair-budget verification
              <InfoTip text={metricHelp("budget") ?? ""} label="budget" />
            </span>
          }
          subtitle={data.fair_budget.definition ?? undefined}
          right={
            <Badge tone={data.fair_budget.ok ? "positive" : "negative"}>
              {data.fair_budget.ok ? "MATCHED" : "MISMATCH"}
            </Badge>
          }
        />
        <DataTable
          columns={[
            { key: "m", header: "Method", render: (r) => r.method },
            { key: "b", header: "Budget", align: "right", render: (r) => fmtInt(r.budget) },
            { key: "p", header: "Proposed", align: "right", render: (r) => fmtInt(r.proposed) },
            { key: "i", header: "Invalid", align: "right", render: (r) => fmtInt(r.invalid) },
            { key: "d", header: "Duplicate", align: "right", render: (r) => fmtInt(r.duplicate) },
            { key: "c", header: "Cached", align: "right", render: (r) => fmtInt(r.cached) },
            { key: "e", header: "Evaluated", align: "right", render: (r) => fmtInt(r.evaluated) },
            {
              key: "ok",
              header: "Within budget",
              align: "center",
              render: (r) => (
                <Badge tone={r.within_budget ? "positive" : "negative"}>
                  {r.within_budget ? "yes" : "no"}
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
      header: "Candidate",
      render: (c) => <span className="font-mono text-xs">{c.candidate_id}</span>,
    },
    {
      key: "status",
      header: "Status",
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
      header: "Mean val Sharpe",
      align: "right",
      render: (c) => fmtRatio(c.mean_val_sharpe),
    },
    { key: "np", header: "Params", align: "right", render: (c) => fmtInt(c.n_active_params) },
    {
      key: "p",
      header: "Parameters",
      render: (c) => (
        <code className="text-xs text-muted">
          {Object.entries(c.params)
            .map(([k, v]) => `${k}=${String(v)}`)
            .join("  ")}
        </code>
      ),
    },
  ];

  return (
    <Card>
      <CardHeader
        title="Candidate ranking"
        subtitle="Ranked by objective fitness (validation). Test metrics never inform ranking."
        right={
          <div className="flex gap-1">
            {available.map((mth) => (
              <button
                key={mth}
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
        <ErrorState title="No candidates" detail={error.message} />
      ) : !data || data.items.length === 0 ? (
        <EmptyState title="No candidates for this method" />
      ) : (
        <DataTable columns={columns} rows={data.items} rowKey={(c) => c.candidate_id} dense />
      )}
    </Card>
  );
}

function FoldsTab({ runId }: { runId: string }) {
  const { data, error, isLoading } = useFolds(runId);
  if (isLoading) return <Skeleton className="h-64" />;
  if (error) return <ErrorState title="No folds" detail={error.message} />;
  if (!data) return <EmptyState title="No fold artifact" />;

  const foldColumns: Column<(typeof data.folds)[number]>[] = [
    { key: "f", header: "Fold", render: (f) => fmtInt(f.fold) },
    {
      key: "tr",
      header: "Train",
      render: (f) => `${f.train_start?.slice(0, 10)} → ${f.train_end?.slice(0, 10)}`,
    },
    {
      key: "va",
      header: "Validation",
      render: (f) => `${f.val_start?.slice(0, 10)} → ${f.val_end?.slice(0, 10)}`,
    },
    {
      key: "te",
      header: "Test",
      render: (f) => `${f.test_start?.slice(0, 10)} → ${f.test_end?.slice(0, 10)}`,
    },
    { key: "pu", header: "Purge", align: "right", render: (f) => fmtInt(f.purge_bars) },
    { key: "em", header: "Embargo", align: "right", render: (f) => fmtInt(f.embargo_bars) },
  ];

  const winnerColumns: Column<FoldWinnerModel>[] = [
    { key: "f", header: "Fold", render: (w) => fmtInt(w.fold) },
    {
      key: "w",
      header: "Winner",
      render: (w) => <span className="font-mono text-xs">{w.winner ?? "—"}</span>,
    },
    { key: "vs", header: "Val Sharpe", align: "right", render: (w) => fmtRatio(w.val_sharpe) },
    {
      key: "ts",
      header: "Test Sharpe",
      align: "right",
      render: (w) => <span className={signClass(w.test_sharpe)}>{fmtRatio(w.test_sharpe)}</span>,
    },
    {
      key: "tr",
      header: "Test return",
      align: "right",
      render: (w) => (
        <span className={signClass(w.test_total_return)}>
          {fmtSignedPercent(w.test_total_return)}
        </span>
      ),
    },
    { key: "nt", header: "Trades", align: "right", render: (w) => fmtInt(w.test_n_trades) },
  ];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Walk-forward partitions"
          subtitle={`Regime inputs: ${data.regime_inputs.join(", ") || "—"}`}
        />
        <DataTable columns={foldColumns} rows={data.folds} rowKey={(f) => String(f.fold)} dense />
      </Card>
      {Object.entries(data.winners).map(([method, winners]) => (
        <Card key={method}>
          <CardHeader
            title={`Fold winners — ${method}`}
            subtitle="Selected on validation; scored once on test."
          />
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
