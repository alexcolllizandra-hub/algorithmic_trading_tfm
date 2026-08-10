"use client";

import { Suspense } from "react";

import { DiversityChart } from "@/components/charts/DiversityChart";
import { ConvergencePanel } from "@/components/ConvergencePanel";
import { PageShell } from "@/components/layout/PageShell";
import { RunPicker, useSelectedRun } from "@/components/RunPicker";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/Table";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/States";
import { fmtRatio } from "@/lib/format";
import { useAnalytics } from "@/lib/hooks";

function AnalyticsInner() {
  const runId = useSelectedRun();
  const { data, error, isLoading } = useAnalytics(runId);

  return (
    <div className="space-y-6">
      <RunPicker selected={runId} />

      {!runId ? (
        <EmptyState title="Select a run" />
      ) : isLoading ? (
        <Skeleton className="h-72" />
      ) : error ? (
        <ErrorState title="No analytics" detail={error.message} />
      ) : !data ? (
        <EmptyState title="No analytics artifact" />
      ) : (
        <>
          <ConvergencePanel
            series={data.convergence}
            folds={data.convergence_folds}
            title="Convergence"
            subtitle="Best fitness after each unique evaluation, within one outer fold. Each fold is searched independently, so traces are not comparable across folds."
            emptyTitle="No convergence history"
            foldLabel="Outer fold"
          />

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader title="GA population diversity" subtitle="Per generation" />
              {data.ga_diversity.length === 0 ? (
                <EmptyState title="No GA diversity (single-method run?)" />
              ) : (
                <DiversityChart data={data.ga_diversity} />
              )}
            </Card>
            <Card>
              <CardHeader title="GA lineage" subtitle="Parent → offspring per generation" />
              {data.ga_lineage.length === 0 ? (
                <EmptyState title="No lineage recorded" />
              ) : (
                <DataTable
                  columns={[
                    { key: "g", header: "Gen", render: (r) => String(r.generation ?? "—") },
                    {
                      key: "c",
                      header: "Child",
                      render: (r) => (
                        <span className="font-mono text-xs">{String(r.child ?? "—")}</span>
                      ),
                    },
                    {
                      key: "p",
                      header: "Parents",
                      render: (r) => (
                        <span className="font-mono text-xs text-muted">
                          {Array.isArray(r.parents) ? (r.parents as string[]).join(", ") : "—"}
                        </span>
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

          <Card>
            <CardHeader title="Best candidate per generation" />
            {data.ga_generation_best.length === 0 ? (
              <EmptyState title="No per-generation best recorded" />
            ) : (
              <DataTable
                columns={[
                  { key: "g", header: "Gen", render: (r) => String(r.generation ?? "—") },
                  {
                    key: "id",
                    header: "Best candidate",
                    render: (r) => (
                      <span className="font-mono text-xs">
                        {String(r.best_candidate_id ?? "—")}
                      </span>
                    ),
                  },
                  {
                    key: "f",
                    header: "Fitness",
                    align: "right",
                    render: (r) => fmtRatio(Number(r.best_fitness)),
                  },
                ]}
                rows={data.ga_generation_best}
                rowKey={(_r, i) => String(i)}
                dense
              />
            )}
          </Card>
        </>
      )}
    </div>
  );
}

export default function AnalyticsPage() {
  return (
    <PageShell title="Search Analytics">
      <Suspense fallback={<Skeleton className="h-72" />}>
        <AnalyticsInner />
      </Suspense>
    </PageShell>
  );
}
