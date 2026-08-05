"use client";

import { PageShell } from "@/components/layout/PageShell";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { API_BASE } from "@/lib/api";
import { useHealth } from "@/lib/hooks";

type Status = "implemented" | "planned" | "unavailable";

const STATUS_TONE: Record<Status, "positive" | "accent" | "neutral"> = {
  implemented: "positive",
  planned: "accent",
  unavailable: "neutral",
};

const COMPONENTS: { name: string; status: Status; note: string }[] = [
  {
    name: "Data pipeline & provenance audit",
    status: "implemented",
    note: "Binance USDT-M, checksum-verified manifests",
  },
  {
    name: "Causal feature engine",
    status: "implemented",
    note: "registry + causal builders + leakage tests",
  },
  {
    name: "Market regimes (threshold/kmeans/gmm)",
    status: "implemented",
    note: "fit on train only",
  },
  {
    name: "Strategies (momentum/breakout/mean-reversion)",
    status: "implemented",
    note: "shared interface",
  },
  { name: "Cost/funding-aware backtester", status: "implemented", note: "next-bar execution" },
  {
    name: "Walk-forward validation",
    status: "implemented",
    note: "purge + embargo + frozen holdout",
  },
  { name: "Random Search / Genetic Algorithm", status: "implemented", note: "fair shared budget" },
  { name: "Quantitative API (FastAPI)", status: "implemented", note: "read-only v1" },
  { name: "Research platform (this UI)", status: "implemented", note: "Next.js + TS" },
  { name: "Triple-barrier & meta-labeling", status: "planned", note: "future phase" },
  {
    name: "Async job execution / paper trading",
    status: "planned",
    note: "requires safety controls",
  },
  {
    name: "MLflow / Grafana / Prometheus",
    status: "planned",
    note: "ports reserved, not deployed",
  },
  {
    name: "Final holdout evaluation",
    status: "unavailable",
    note: "frozen until development is complete",
  },
];

const PORTS: { service: string; port: number; state: Status; note: string }[] = [
  { service: "Web platform", port: 3000, state: "implemented", note: "Next.js" },
  { service: "Quantitative API", port: 8000, state: "implemented", note: "FastAPI" },
  { service: "MLflow", port: 5000, state: "planned", note: "reserved" },
  { service: "PostgreSQL", port: 5432, state: "planned", note: "reserved (internal)" },
  { service: "Redis", port: 6379, state: "planned", note: "reserved (internal)" },
  { service: "Grafana", port: 3001, state: "planned", note: "reserved" },
  { service: "Prometheus", port: 9090, state: "planned", note: "reserved" },
];

export default function SystemPage() {
  const { data, error } = useHealth();
  const online = !error && data?.status === "ok";

  return (
    <PageShell title="Architecture / System Status">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader title="Service health" />
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-muted">Quantitative API</dt>
              <dd>
                <Badge tone={online ? "positive" : "negative"}>
                  {online ? "online" : "offline"}
                </Badge>
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">API base</dt>
              <dd className="font-mono text-xs">{API_BASE}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">Environment</dt>
              <dd>{data?.environment ?? "—"}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">Runs indexed</dt>
              <dd className="tabular">{data?.runs_available ?? "—"}</dd>
            </div>
          </dl>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader
            title="Data flow"
            subtitle="Single source of truth: the run-artifact directory."
          />
          <ol className="space-y-2 text-sm text-muted">
            <li>
              1. Binance USDT-M dumps → validated/processed parquet + committed manifests
              (checksums).
            </li>
            <li>2. Causal features → regimes (train-only) → strategies → next-bar backtester.</li>
            <li>
              3. Walk-forward RS/GA search → per-run artifacts (candidates, folds, winners, equity,
              trades).
            </li>
            <li>4. FastAPI adapts artifacts → versioned JSON → this read-only React platform.</li>
          </ol>
        </Card>
      </div>

      <Card>
        <CardHeader title="Components" />
        <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
          {COMPONENTS.map((c) => (
            <div
              key={c.name}
              className="flex items-center justify-between rounded-md border border-border bg-surface-2 px-3 py-2"
            >
              <div>
                <div className="text-sm">{c.name}</div>
                <div className="text-xs text-muted">{c.note}</div>
              </div>
              <Badge tone={STATUS_TONE[c.status]}>{c.status}</Badge>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <CardHeader
          title="Service ports"
          subtitle="Reserved services are documented but not deployed in this phase."
        />
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          {PORTS.map((p) => (
            <div key={p.service} className="rounded-md border border-border bg-surface-2 px-3 py-2">
              <div className="flex items-center justify-between">
                <span className="text-sm">{p.service}</span>
                <Badge tone={STATUS_TONE[p.state]}>{p.state}</Badge>
              </div>
              <div className="mt-1 font-mono text-xs text-muted">
                :{p.port} · {p.note}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </PageShell>
  );
}
