"use client";

import { Suspense, useMemo } from "react";

import { HowToRead } from "@/components/education/HowToRead";
import { InterpretationBox } from "@/components/education/InterpretationBox";
import { SectionIntro } from "@/components/education/SectionIntro";
import { PageShell } from "@/components/layout/PageShell";
import { RunPicker, useSelectedRun } from "@/components/RunPicker";
import { TimelineChart } from "@/components/research/TimelineChart";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type Column } from "@/components/ui/Table";
import { EmptyState, ErrorState, PartialNotice, Skeleton } from "@/components/ui/States";
import { StatCard } from "@/components/ui/StatCard";
import { API_BASE } from "@/lib/api";
import type { DatasetCoverage, EdaFigureModel } from "@/lib/api-types";
import { fmtDate, fmtInt } from "@/lib/format";
import { es } from "@/lib/i18n/es";
import {
  useEdaFigures,
  useEdaSummary,
  useMarketCoverage,
  useResearchSummary,
  useTimeline,
} from "@/lib/hooks";

function DatosEdaInner() {
  const runId = useSelectedRun();
  const { data: research } = useResearchSummary();
  const effectiveRun = runId ?? research?.pilot_run_id ?? null;

  const { data: coverage, error: covError, isLoading: covLoading } = useMarketCoverage();
  const { data: edaSummary } = useEdaSummary();
  const { data: keyFigures } = useEdaFigures({ key_only: true, limit: 12 });
  const { data: allFigures } = useEdaFigures({ limit: 200 });
  const { data: timeline, error: tlError, isLoading: tlLoading } = useTimeline(effectiveRun);

  const klineRows = useMemo(
    () =>
      (coverage?.datasets ?? []).filter(
        (d) => d.stream === "klines" && !d.dataset_id.includes("holdout")
      ),
    [coverage]
  );

  const covColumns: Column<DatasetCoverage>[] = [
    {
      key: "id",
      header: "Dataset",
      render: (d) => <span className="font-mono text-xs">{d.dataset_id}</span>,
    },
    {
      key: "class",
      header: "Autenticidad",
      render: (d) => (
        <Badge tone={d.classification === "REAL_HISTORICAL" ? "positive" : "warn"}>
          {d.classification}
        </Badge>
      ),
    },
    { key: "sym", header: "Símbolo", render: (d) => `${d.symbol ?? "—"} ${d.timeframe ?? ""}` },
    { key: "rows", header: "Filas", align: "right", render: (d) => fmtInt(d.row_count) },
    { key: "min", header: "Desde", render: (d) => fmtDate(d.min_timestamp) },
    { key: "max", header: "Hasta", render: (d) => fmtDate(d.max_timestamp) },
    {
      key: "hold",
      header: "Holdout",
      align: "center",
      render: (d) =>
        d.crosses_holdout ? (
          <Badge tone="negative">cruza</Badge>
        ) : (
          <Badge tone="positive">solo dev</Badge>
        ),
    },
  ];

  const s = es.sections.datosEda;

  return (
    <div className="space-y-6">
      <SectionIntro title={s.title} subtitle={s.subtitle} questions={s} />
      <PartialNotice>{es.warnings.devPartitionOnly}</PartialNotice>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Holdout desde" value={edaSummary?.holdout_start?.slice(0, 10) ?? "—"} />
        <StatCard label="Periodo desarrollo" value={edaSummary?.development_period ?? "—"} />
        <StatCard label="Figuras EDA" value={fmtInt(edaSummary?.n_figures)} />
        <StatCard label="Hallazgos clave" value={fmtInt(edaSummary?.n_key_findings)} />
      </div>

      <Card>
        <CardHeader
          title="Cobertura y autenticidad"
          subtitle={`Holdout: ${coverage?.holdout_start?.slice(0, 10) ?? "—"}`}
        />
        {covLoading ? (
          <Skeleton className="h-48" />
        ) : covError ? (
          <ErrorState title="Sin cobertura" detail={covError.message} />
        ) : klineRows.length === 0 ? (
          <EmptyState title="Sin datasets" />
        ) : (
          <DataTable columns={covColumns} rows={klineRows} rowKey={(d) => d.dataset_id} dense />
        )}
      </Card>

      <Card>
        <CardHeader title={es.timeline.title} subtitle="Seleccione un run para ver particiones" />
        <RunPicker selected={effectiveRun} />
        {tlLoading ? (
          <Skeleton className="mt-4 h-48" />
        ) : tlError ? (
          <div className="mt-4">
            <ErrorState title="Sin cronología" detail={tlError.message} />
          </div>
        ) : timeline ? (
          <div className="mt-4">
            <TimelineChart data={timeline} />
          </div>
        ) : (
          <EmptyState title={es.common.selectRun} />
        )}
      </Card>

      <Card>
        <CardHeader
          title={es.common.keyFindings}
          subtitle={`${keyFigures?.items.length ?? 0} figuras destacadas`}
        />
        {keyFigures && keyFigures.items.length > 0 ? (
          <FigureGallery figures={keyFigures.items} />
        ) : (
          <EmptyState title="Sin hallazgos clave indexados" />
        )}
        <div className="mt-4">
          <a href="#galeria-completa" className="text-sm text-accent hover:underline">
            {es.common.viewAll} ↓
          </a>
        </div>
      </Card>

      <div id="galeria-completa">
        <Card>
          <CardHeader
            title={es.common.fullGallery}
            subtitle={`${allFigures?.items.length ?? 0} figuras · temas: ${edaSummary?.themes.join(", ") ?? "—"}`}
          />
          {allFigures && allFigures.items.length > 0 ? (
            <FigureGallery figures={allFigures.items} />
          ) : (
            <EmptyState title="Sin figuras EDA" />
          )}
        </Card>
      </div>

      <HowToRead>
        <p>{es.glossary.pilot.definition}</p>
        <p>{es.glossary.holdout.definition}</p>
      </HowToRead>

      <InterpretationBox tone="info">{s.queConcluirAnswer}</InterpretationBox>
    </div>
  );
}

function FigureGallery({ figures }: { figures: EdaFigureModel[] }) {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {figures.map((fig) => (
        <figure key={fig.figure_id} className="rounded-md border border-border bg-surface-2 p-3">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <Badge tone={fig.is_key_finding ? "accent" : "neutral"}>{fig.theme_label_es}</Badge>
            {fig.is_key_finding && <Badge tone="positive">clave</Badge>}
          </div>
          <figcaption className="mb-2 text-sm font-medium">{fig.title_es}</figcaption>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={`${API_BASE}/eda/figures/${fig.figure_id}`}
            alt={fig.title_es}
            className="w-full rounded border border-border bg-bg"
            loading="lazy"
          />
          <p className="mt-2 text-xs text-muted">{fig.finding_es}</p>
          <p className="mt-1 text-xs text-muted">{fig.interpretation_es}</p>
        </figure>
      ))}
    </div>
  );
}

export default function DatosEdaPage() {
  return (
    <PageShell title={es.sections.datosEda.title}>
      <Suspense fallback={<Skeleton className="h-72" />}>
        <DatosEdaInner />
      </Suspense>
    </PageShell>
  );
}
