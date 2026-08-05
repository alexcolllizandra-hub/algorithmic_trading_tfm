"use client";

import { HowToRead } from "@/components/education/HowToRead";
import { InterpretationBox } from "@/components/education/InterpretationBox";
import { SectionIntro } from "@/components/education/SectionIntro";
import { PageShell } from "@/components/layout/PageShell";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type Column } from "@/components/ui/Table";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/States";
import type { FeatureDocModel, StrategyDocModel } from "@/lib/api-types";
import { fmtInt } from "@/lib/format";
import { es } from "@/lib/i18n/es";
import { useMethodology } from "@/lib/hooks";

export default function MetodologiaPage() {
  const { data, error, isLoading } = useMethodology();
  const s = es.sections.metodologia;

  const featureColumns: Column<FeatureDocModel>[] = [
    {
      key: "name",
      header: "Feature",
      render: (f) => <span className="font-mono text-xs">{f.name}</span>,
    },
    { key: "family", header: "Familia", render: (f) => f.family },
    {
      key: "formula",
      header: "Fórmula",
      render: (f) => <code className="text-xs">{f.formula}</code>,
    },
    { key: "lag", header: "Lag", align: "right", render: (f) => fmtInt(f.lag_bars) },
    { key: "warm", header: "Warm-up", align: "right", render: (f) => fmtInt(f.warmup_bars) },
    {
      key: "interp",
      header: "Interpretación",
      render: (f) => <span className="text-xs text-muted">{f.interpretation_es}</span>,
    },
  ];

  const strategyColumns: Column<StrategyDocModel>[] = [
    { key: "family", header: "Familia", render: (s) => <Badge tone="accent">{s.family}</Badge> },
    { key: "name", header: "Nombre", render: (s) => s.name_es },
    {
      key: "hyp",
      header: "Hipótesis",
      render: (s) => <span className="text-sm text-muted">{s.hypothesis_es}</span>,
    },
    { key: "status", header: "Estado", render: (s) => s.status },
    {
      key: "params",
      header: "Parámetros",
      render: (s) => (
        <span className="font-mono text-xs text-muted">{s.parameters.join(", ")}</span>
      ),
    },
  ];

  return (
    <PageShell title={s.title}>
      <SectionIntro title={s.title} subtitle={s.subtitle} questions={s} />

      <Card>
        <CardHeader title="Flujo de datos" subtitle="Pipeline reproducible de extremo a extremo" />
        <div className="rounded-md border border-border bg-surface-2 p-4">
          <pre className="overflow-x-auto text-xs text-muted">{`
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│ Binance     │───▶│ Validación + │───▶│ Features    │───▶│ Regímenes    │
│ USDT-M raw  │    │ manifiestos  │    │ causales    │    │ (solo train) │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
                                                                  │
┌─────────────┐    ┌──────────────┐    ┌─────────────┐           ▼
│ Artefactos  │◀───│ RS / GA      │◀───│ Backtest    │◀── Estrategias
│ por run     │    │ walk-forward │    │ next-bar    │   interpretables
└─────────────┘    └──────────────┘    └─────────────┘
       │
       ▼
  FastAPI → plataforma (solo lectura)
          `}</pre>
        </div>
      </Card>

      <Card>
        <CardHeader
          title="Catálogo de features causales"
          subtitle={data?.source_run_id ? `Fuente: ${data.source_run_id}` : undefined}
        />
        {isLoading ? (
          <Skeleton className="h-48" />
        ) : error ? (
          <ErrorState title="Sin metodología" detail={error.message} />
        ) : !data || data.features.length === 0 ? (
          <EmptyState title="Sin features documentados" />
        ) : (
          <DataTable columns={featureColumns} rows={data.features} rowKey={(f) => f.name} dense />
        )}
      </Card>

      <Card>
        <CardHeader title="Familias de estrategia" />
        {isLoading ? (
          <Skeleton className="h-32" />
        ) : !data || data.strategies.length === 0 ? (
          <EmptyState title="Sin estrategias documentadas" />
        ) : (
          <DataTable columns={strategyColumns} rows={data.strategies} rowKey={(s) => s.family} />
        )}
      </Card>

      <Card>
        <CardHeader title="Validación walk-forward" />
        <div className="space-y-3 text-sm text-muted">
          <p>
            Particiones <strong>estrictamente cronológicas</strong> en folds train / validación /
            test. Entre ventanas se aplican barras de <em>purge</em> y <em>embargo</em> para evitar
            leakage temporal.
          </p>
          <p>
            El candidato ganador de cada fold se elige usando solo métricas de validación; la
            ventana test se evalúa una sola vez. El holdout final permanece bloqueado hasta el
            informe definitivo.
          </p>
          <ul className="list-inside list-disc space-y-1">
            <li>RS y GA comparten presupuesto equitativo de evaluaciones.</li>
            <li>Costes de transacción y funding incluidos en el backtest.</li>
            <li>Señales ejecutadas en la barra siguiente (next-bar).</li>
          </ul>
        </div>
      </Card>

      <HowToRead>
        <p>{es.glossary.causalFeature.definition}</p>
        <p>{es.glossary.nextBar.definition}</p>
        <p>{es.glossary.walkForward.definition}</p>
      </HowToRead>

      <InterpretationBox tone="info">{s.queConcluirAnswer}</InterpretationBox>
    </PageShell>
  );
}
