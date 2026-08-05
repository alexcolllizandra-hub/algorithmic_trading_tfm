"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { PageShell } from "@/components/layout/PageShell";
import { Badge, RunKindBadge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { DataTable, type Column } from "@/components/ui/Table";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/States";
import type { RunSummary } from "@/lib/api-types";
import { fmtInt } from "@/lib/format";
import { useRuns } from "@/lib/hooks";

const FAMILIES = ["", "momentum", "breakout", "mean_reversion"];
const KINDS = ["", "development", "synthetic-smoke", "final-holdout"];

export default function ExperimentsPage() {
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
      render: (r) => (
        <Link
          className="font-mono text-xs text-accent hover:underline"
          href={`/experiments/${r.run_id}`}
        >
          {r.run_id}
        </Link>
      ),
    },
    { key: "kind", header: "Type", render: (r) => <RunKindBadge kind={r.kind} /> },
    { key: "family", header: "Family", render: (r) => r.family },
    { key: "symbol", header: "Symbol", render: (r) => `${r.symbol} ${r.timeframe}` },
    { key: "seed", header: "Seed", align: "right", render: (r) => fmtInt(r.seed) },
    { key: "folds", header: "Folds", align: "right", render: (r) => fmtInt(r.n_folds) },
    { key: "budget", header: "Budget", align: "right", render: (r) => fmtInt(r.budget) },
    {
      key: "best",
      header: "Best OOS",
      render: (r) => (r.best_method ? <Badge tone="accent">{r.best_method}</Badge> : "—"),
    },
  ];

  return (
    <PageShell title="Experiments">
      <Card>
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col gap-1">
            <label htmlFor="f-family" className="text-xs text-muted">
              Strategy family
            </label>
            <select
              id="f-family"
              value={family}
              onChange={(e) => setFamily(e.target.value)}
              className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm"
            >
              {FAMILIES.map((f) => (
                <option key={f} value={f}>
                  {f || "All families"}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="f-kind" className="text-xs text-muted">
              Run type
            </label>
            <select
              id="f-kind"
              value={kind}
              onChange={(e) => setKind(e.target.value)}
              className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm"
            >
              {KINDS.map((k) => (
                <option key={k} value={k}>
                  {k || "All types"}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-1 flex-col gap-1">
            <label htmlFor="f-query" className="text-xs text-muted">
              Search run id
            </label>
            <input
              id="f-query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="search_momentum_…"
              className="w-full rounded-md border border-border bg-surface px-3 py-1.5 text-sm"
            />
          </div>
          <span className="text-sm text-muted">{rows.length} runs</span>
        </div>
      </Card>

      {isLoading ? (
        <Skeleton className="h-64" />
      ) : error ? (
        <ErrorState title="Could not load runs" detail={error.message} />
      ) : rows.length === 0 ? (
        <EmptyState title="No runs match the filters" />
      ) : (
        <DataTable columns={columns} rows={rows} rowKey={(r) => r.run_id} />
      )}
    </PageShell>
  );
}
