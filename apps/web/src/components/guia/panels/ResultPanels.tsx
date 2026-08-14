"use client";

import { GuideDataState, type StudyState } from "@/components/guia/GuideDataState";
import { Illustration } from "@/components/guia/Illustration";
import { Bars } from "@/components/guia/figures/Bars";
import { InterpretationBox } from "@/components/education/InterpretationBox";
import { CorrectionsPanel } from "@/components/study/CorrectionsPanel";
import { HoldoutPanel } from "@/components/study/HoldoutPanel";
import { MasterTable } from "@/components/study/MasterTable";
import { RegimePanel } from "@/components/study/RegimePanel";
import { Badge } from "@/components/ui/Badge";
import { CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/States";
import { StatCard } from "@/components/ui/StatCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { DataTable, type Column } from "@/components/ui/Table";
import type { StudyFamilySummary } from "@/lib/api-types";
import { fmtInt, fmtNumber, fmtPercent, fmtSignedPercent, signClass } from "@/lib/format";
import { bestFamilyRow, selectionBiasBars, spuriousRows, type SpuriousRow } from "@/lib/guia";
import { es } from "@/lib/i18n/es";
import { crossAssetRows } from "@/lib/study";

const inventoryColumns: Column<StudyFamilySummary>[] = [
  {
    key: "family",
    header: es.study.table.family,
    render: (r) => <span className="font-medium text-fg">{r.family}</span>,
  },
  { key: "gate", header: es.study.table.gate, render: (r) => <Badge>{r.gate}</Badge> },
  { key: "symbol", header: es.study.table.symbol, render: (r) => r.symbol },
  {
    key: "seeds",
    header: es.study.table.seeds,
    align: "right",
    render: (r) => fmtInt(r.n_seeds),
  },
  {
    key: "thesis",
    header: es.study.detail.hypothesis,
    render: (r) => <span className="text-muted">{r.thesis || es.common.noData}</span>,
  },
];

const spuriousColumns: Column<SpuriousRow>[] = [
  { key: "rule", header: es.guia.labels.spuriousRule, render: (r) => r.rule },
  {
    key: "trials",
    header: es.study.corrections.trials,
    align: "right",
    render: (r) => fmtInt(r.nTrials),
  },
  {
    key: "deflated",
    header: es.study.corrections.deflated,
    align: "right",
    render: (r) => fmtNumber(r.deflated, 4),
  },
  {
    key: "spurious",
    header: es.study.corrections.spurious,
    align: "right",
    render: (r) => fmtPercent(r.probability, 2),
  },
];

export function EstrategiasProbadasPanel({ state }: { state: StudyState }) {
  const { summary } = state;
  if (!summary) return <GuideDataState error={state.error} isLoading={state.isLoading} />;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label={es.study.headline.families} value={fmtInt(summary.study.n_families)} />
        <StatCard label={es.study.headline.rowsLabel} value={fmtInt(summary.families.length)} />
        <StatCard label={es.study.headline.units} value={fmtInt(summary.study.n_units)} />
      </div>

      <div>
        <CardHeader
          title={es.guia.labels.inventoryTitle}
          subtitle={es.guia.labels.inventorySubtitle}
        />
        <DataTable columns={inventoryColumns} rows={summary.families} rowKey={(r) => r.key} dense />
      </div>
    </div>
  );
}

export function ResultadosPanel({
  state,
  familyKey,
  onSelectFamily,
}: {
  state: StudyState;
  familyKey: string | null;
  onSelectFamily: (key: string) => void;
}) {
  const { summary } = state;
  if (!summary) return <GuideDataState error={state.error} isLoading={state.isLoading} />;

  return (
    <div className="space-y-4">
      <MasterTable families={summary.families} selectedKey={familyKey} onSelect={onSelectFamily} />
      <p className="text-xs text-muted">{es.guia.labels.resultsNote}</p>
      <CorrectionsPanel study={summary.study} />
    </div>
  );
}

export function RechazoPanel({ state }: { state: StudyState }) {
  const { summary } = state;
  const best = summary ? bestFamilyRow(summary) : null;
  const siblings = summary && best ? crossAssetRows(summary.families, best.family) : [];
  const pbo = summary?.study.pbo?.pbo;
  const rows = summary ? spuriousRows(summary.study) : [];

  return (
    <div className="space-y-4">
      <CardHeader title={es.guia.labels.reasonsTitle} />
      <ol className="grid grid-cols-1 gap-3 xl:grid-cols-3">
        {[
          { title: es.guia.labels.reasonBest, text: es.guia.labels.reasonBestText },
          { title: es.guia.labels.reasonAsset, text: es.guia.labels.reasonAssetText },
          { title: es.guia.labels.reasonSplit, text: es.guia.labels.reasonSplitText },
        ].map((reason) => (
          <li key={reason.title} className="rounded-card border border-border bg-surface-2 p-4">
            <p className="text-sm font-semibold text-fg">{reason.title}</p>
            <p className="mt-2 text-sm text-muted">{reason.text}</p>
          </li>
        ))}
      </ol>

      <Illustration
        title={es.guia.figures.selectionBias.title}
        caption={es.guia.figures.selectionBias.caption}
      >
        <Bars bars={selectionBiasBars()} />
      </Illustration>

      {summary ? (
        <>
          <div>
            <CardHeader title={es.study.detail.crossAssetTitle} />
            {siblings.length > 1 ? (
              <>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  {siblings.map((row) => (
                    <div
                      key={row.key}
                      className="rounded-card border border-border bg-surface-2 p-4"
                    >
                      <p className="text-xs uppercase tracking-wide text-muted">
                        {row.family} · {row.symbol}
                      </p>
                      <p
                        className={`tabular mt-1 text-2xl font-semibold ${signClass(row.total_return)}`}
                      >
                        {fmtSignedPercent(row.total_return)}
                      </p>
                      <p className="tabular mt-1 text-xs text-muted">
                        {es.study.table.sharpe} {fmtNumber(row.sharpe, 2)} · {es.study.table.pValue}{" "}
                        {fmtNumber(row.p_value, 4)}
                      </p>
                    </div>
                  ))}
                </div>
                <p className="mt-3 text-sm text-muted">{es.study.detail.crossAssetNote}</p>
              </>
            ) : (
              <EmptyState title={es.study.detail.crossAssetSingle} />
            )}
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <StatCard
              label={es.study.headline.pbo}
              value={
                pbo != null && Number.isFinite(pbo) ? (
                  fmtNumber(pbo, 3)
                ) : (
                  <StatusBadge status={null} />
                )
              }
              sub={es.study.headline.pboSub}
              metricKey="pbo"
            />
            <StatCard
              label={es.study.headline.survivors}
              value={fmtInt(summary.study.holm.n_rejected)}
              sub={es.study.headline.survivorsSub.replace(
                "{alpha}",
                fmtNumber(summary.study.alpha, 2)
              )}
              metricKey="holm_adjusted_p"
            />
          </div>

          <div>
            <CardHeader
              title={es.guia.labels.spuriousTitle}
              subtitle={es.study.corrections.deflatedCaption}
            />
            {rows.length > 0 ? (
              <DataTable columns={spuriousColumns} rows={rows} rowKey={(r) => r.rule} dense />
            ) : (
              <EmptyState title={es.common.noData} />
            )}
          </div>
        </>
      ) : (
        <GuideDataState error={state.error} isLoading={state.isLoading} />
      )}

      <p className="text-sm text-muted">{es.guia.labels.regimeQuestion}</p>
      <RegimePanel />
    </div>
  );
}

export function ConclusionPanel({ state }: { state: StudyState }) {
  const { summary } = state;

  return (
    <div className="space-y-4">
      {summary ? (
        <InterpretationBox title={es.study.corrections.conclusionTitle}>
          <p>{summary.study.conclusion}</p>
        </InterpretationBox>
      ) : (
        <GuideDataState error={state.error} isLoading={state.isLoading} />
      )}

      <InterpretationBox tone="warning" title={es.study.holdout.lockedTitle}>
        <p>{es.guia.labels.holdoutWithheld}</p>
      </InterpretationBox>

      <HoldoutPanel />
    </div>
  );
}
