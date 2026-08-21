"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { SectionIntro } from "@/components/education/SectionIntro";
import { PageShell } from "@/components/layout/PageShell";
import { RunPicker, useSelectedRun } from "@/components/RunPicker";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState, ErrorState, PartialNotice, Skeleton } from "@/components/ui/States";
import { useI18n } from "@/lib/i18n";
import { useRb } from "@/lib/i18n/runBrowser";
import { API_BASE } from "@/lib/api";
import { useArtifacts, useHealth } from "@/lib/hooks";

type Tab = "artifacts" | "system";

function JsonBlock({ value }: { value: unknown }) {
  if (value == null) return <PartialNotice>Artefacto ausente o ilegible.</PartialNotice>;
  return (
    <pre className="max-h-80 overflow-auto rounded-md border border-border bg-surface-2 p-3 text-xs">
      <code>{JSON.stringify(value, null, 2)}</code>
    </pre>
  );
}

function ArtifactsTab() {
  const rb = useRb();
  const t = useI18n();
  const runId = useSelectedRun();
  const { data, error, isLoading } = useArtifacts(runId);

  const failedTotal = data
    ? Object.values(data.failed_candidates).reduce((a, arr) => a + arr.length, 0)
    : 0;

  return (
    <div className="space-y-6">
      <RunPicker selected={runId} />
      {!runId ? (
        <EmptyState title={t.common.selectRun} />
      ) : isLoading ? (
        <Skeleton className="h-72" />
      ) : error ? (
        <ErrorState title={rb.diagNoArtifacts} detail={error.message} />
      ) : !data ? (
        <EmptyState title={rb.diagNoBundle} />
      ) : (
        <>
          {data.warnings.length > 0 && (
            <Card>
              <CardHeader title={rb.diagWarnings} />
              <ul className="list-inside list-disc space-y-1 text-sm text-warn">
                {data.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </Card>
          )}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader title={rb.diagDatasetManifests} />
              <JsonBlock value={data.dataset_manifests} />
            </Card>
            <Card>
              <CardHeader title={rb.diagFeatureManifest} />
              <JsonBlock value={data.feature_manifest} />
            </Card>
            <Card>
              <CardHeader title={rb.diagSearchSpace} />
              <JsonBlock value={data.search_space} />
            </Card>
            <Card>
              <CardHeader title={rb.diagObjective} />
              <JsonBlock value={data.objective} />
            </Card>
            <Card>
              <CardHeader title={rb.diagEnvironment} />
              <JsonBlock value={data.environment} />
            </Card>
            <Card>
              <CardHeader title={rb.diagGitState} />
              <JsonBlock value={data.git_state} />
            </Card>
          </div>
          <Card>
            <CardHeader
              title={rb.diagFailedCandidates}
              right={<Badge tone={failedTotal ? "warn" : "positive"}>{failedTotal}</Badge>}
            />
            {failedTotal === 0 ? (
              <EmptyState title={rb.diagNoFailedCandidates} />
            ) : (
              <JsonBlock value={data.failed_candidates} />
            )}
          </Card>
          <Card>
            <CardHeader
              title={rb.diagFiles}
              subtitle={`${data.files.length} en el directorio del run`}
            />
            <div className="flex flex-wrap gap-2">
              {data.files.map((f) => (
                <span
                  key={f}
                  className="rounded-md border border-border bg-surface-2 px-2 py-1 font-mono text-xs text-muted"
                >
                  {f}
                </span>
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

type Status = "implemented" | "planned" | "unavailable";

const STATUS_TONE: Record<Status, "positive" | "accent" | "neutral"> = {
  implemented: "positive",
  planned: "accent",
  unavailable: "neutral",
};

const COMPONENTS: { name: string; status: Status; note: string }[] = [
  {
    name: "Pipeline de datos y auditoría",
    status: "implemented",
    note: "Binance USDT-M, manifiestos SHA-256",
  },
  {
    name: "Motor de features causales",
    status: "implemented",
    note: "registry + tests de leakage",
  },
  { name: "Regímenes de mercado", status: "implemented", note: "ajuste solo en train" },
  {
    name: "Estrategias interpretables",
    status: "implemented",
    note: "momentum / breakout / mean-reversion",
  },
  { name: "Backtester con costes", status: "implemented", note: "ejecución next-bar" },
  { name: "Walk-forward", status: "implemented", note: "purge + embargo + holdout" },
  { name: "Random Search / GA", status: "implemented", note: "presupuesto equitativo" },
  { name: "API cuantitativa (FastAPI)", status: "implemented", note: "v1 solo lectura" },
  { name: "Plataforma web (esta UI)", status: "implemented", note: "Next.js + TypeScript" },
  { name: "Triple-barrier y meta-labeling", status: "planned", note: "fase futura" },
  { name: "Evaluación holdout final", status: "unavailable", note: "lectura retenida" },
];

function SystemTab() {
  const t = useI18n();
  const { data, error } = useHealth();
  const online = !error && data?.status === "ok";

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader title="Salud del servicio" />
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-muted">API cuantitativa</dt>
              <dd>
                <Badge tone={online ? "positive" : "negative"}>
                  {online ? t.app.apiOnline : t.app.apiOffline}
                </Badge>
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">API base</dt>
              <dd className="font-mono text-xs">{API_BASE}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">Entorno</dt>
              <dd>{data?.environment ?? "—"}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">Runs indexados</dt>
              <dd className="tabular">{data?.runs_available ?? "—"}</dd>
            </div>
          </dl>
        </Card>
        <Card className="lg:col-span-2">
          <CardHeader title="Flujo de datos" />
          <ol className="space-y-2 text-sm text-muted">
            <li>1. Dumps Binance → parquet validado + manifiestos con checksums.</li>
            <li>2. Features causales → regímenes (solo train) → estrategias → backtester.</li>
            <li>3. Búsqueda RS/GA walk-forward → artefactos por run.</li>
            <li>4. FastAPI adapta artefactos → JSON versionado → esta plataforma.</li>
          </ol>
        </Card>
      </div>
      <Card>
        <CardHeader title="Componentes" />
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
    </div>
  );
}

function DiagnosticoInner() {
  const t = useI18n();
  const params = useSearchParams();
  const router = useRouter();
  const tab = (params.get("tab") as Tab) || "artifacts";
  const s = t.sections.diagnostico;

  const setTab = (t: Tab) => {
    const sp = new URLSearchParams(params.toString());
    sp.set("tab", t);
    router.replace(`/diagnostico?${sp.toString()}`);
  };

  return (
    <div className="space-y-6">
      <SectionIntro title={s.title} subtitle={s.subtitle} questions={s} />
      <div className="flex gap-1 border-b border-border">
        {(
          [
            ["artifacts", "Artefactos"],
            ["system", "Sistema"],
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
      {tab === "artifacts" ? <ArtifactsTab /> : <SystemTab />}
    </div>
  );
}

export default function DiagnosticoPage() {
  const t = useI18n();
  return (
    <PageShell title={t.sections.diagnostico.title}>
      <Suspense fallback={<Skeleton className="h-72" />}>
        <DiagnosticoInner />
      </Suspense>
    </PageShell>
  );
}
