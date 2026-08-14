"use client";

import { GuideDataState, NotServed, type StudyState } from "@/components/guia/GuideDataState";
import { Illustration } from "@/components/guia/Illustration";
import { Bars } from "@/components/guia/figures/Bars";
import { Timeline } from "@/components/guia/figures/Timeline";
import { SeedEquityChart } from "@/components/charts/SeedEquityChart";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { EmptyState } from "@/components/ui/States";
import { StatCard } from "@/components/ui/StatCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { DataTable, type Column } from "@/components/ui/Table";
import type { StudySeedResult } from "@/lib/api-types";
import { fmtInt, fmtNumber, fmtSignedPercent, signClass } from "@/lib/format";
import {
  bestFamilyRow,
  costCriterionRows,
  costLadderBars,
  foldRowLabels,
  purgeEmbargoRows,
  splitTimelineRows,
  walkForwardRows,
  type CostCriterionRow,
} from "@/lib/guia";
import { useStudyFamily } from "@/lib/hooks";
import { es } from "@/lib/i18n/es";
import { seedReturnSpread } from "@/lib/study";

const WALK_FORWARD_FOLDS = 4;

const seedColumns: Column<StudySeedResult>[] = [
  {
    key: "seed",
    header: es.study.detail.seedColumn,
    render: (s) => <span className="font-mono text-xs">{fmtInt(s.seed)}</span>,
  },
  {
    key: "ret",
    header: es.study.table.totalReturn,
    align: "right",
    render: (s) => (
      <span className={signClass(s.total_return)}>{fmtSignedPercent(s.total_return)}</span>
    ),
  },
  {
    key: "sharpe",
    header: es.study.table.sharpe,
    align: "right",
    render: (s) => <span className={signClass(s.sharpe)}>{fmtNumber(s.sharpe, 2)}</span>,
  },
  {
    key: "dd",
    header: es.study.table.maxDrawdown,
    align: "right",
    render: (s) => (
      <span className={signClass(s.max_drawdown)}>{fmtSignedPercent(s.max_drawdown)}</span>
    ),
  },
];

const costColumns: Column<CostCriterionRow>[] = [
  {
    key: "family",
    header: es.study.table.family,
    render: (r) => <span className="font-medium text-fg">{r.family}</span>,
  },
  { key: "symbol", header: es.study.table.symbol, render: (r) => r.symbol },
  {
    key: "passed",
    header: es.guia.labels.criterionPassed,
    align: "right",
    render: (r) => (
      <span className={r.met ? "text-positive" : "text-negative"}>
        {fmtInt(r.passed)}/{fmtInt(r.of)}
      </span>
    ),
  },
  {
    key: "required",
    header: es.guia.labels.criterionRequired,
    align: "right",
    render: (r) => `${fmtInt(r.required)}/${fmtInt(r.of)}`,
  },
  {
    key: "met",
    header: es.study.table.verdict,
    align: "right",
    render: (r) => (
      <Badge tone={r.met ? "positive" : "negative"}>
        {r.met ? es.study.corrections.yes : es.study.corrections.no}
      </Badge>
    ),
  },
];

export function ParticionesPanel({ state }: { state: StudyState }) {
  const { summary } = state;
  return (
    <div className="space-y-4">
      <Illustration title={es.guia.figures.splits.title} caption={es.guia.figures.splits.caption}>
        <Timeline rows={splitTimelineRows()} rowLabels={es.guia.figures.splits.rows} />
      </Illustration>

      {summary ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <StatCard
            label={es.guia.labels.holdoutState}
            value={<StatusBadge status={summary.holdout_opened ? "EXECUTED" : "HOLDOUT_LOCKED"} />}
            sub={summary.holdout_opened ? undefined : es.guia.labels.holdoutOpenedFalse}
          />
          <StatCard
            label={es.study.headline.rowsLabel}
            value={fmtInt(summary.families.length)}
            sub={es.study.headline.units}
          />
        </div>
      ) : (
        <GuideDataState error={state.error} isLoading={state.isLoading} />
      )}
    </div>
  );
}

export function WalkForwardPanel() {
  return (
    <div className="space-y-4">
      <Illustration
        title={es.guia.figures.walkForward.title}
        caption={es.guia.figures.walkForward.caption}
      >
        <Timeline
          rows={walkForwardRows(WALK_FORWARD_FOLDS)}
          rowLabels={foldRowLabels(WALK_FORWARD_FOLDS, es.guia.figures.walkForward.foldLabel)}
        />
      </Illustration>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <NotServed label={es.guia.labels.foldsNotServed} hint={es.guia.labels.seeMethodology} />
      </div>
    </div>
  );
}

export function PurgeEmbargoPanel() {
  return (
    <div className="space-y-4">
      <Illustration
        title={es.guia.figures.purgeEmbargo.title}
        caption={es.guia.figures.purgeEmbargo.caption}
      >
        <Timeline rows={purgeEmbargoRows()} rowLabels={es.guia.figures.purgeEmbargo.rows} />
      </Illustration>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <NotServed label={es.guia.labels.purgeNotServed} hint={es.guia.labels.seeMethodology} />
      </div>
    </div>
  );
}

export function SemillasFoldsPanel({
  state,
  familyKey,
  onSelectFamily,
}: {
  state: StudyState;
  familyKey: string | null;
  onSelectFamily: (key: string) => void;
}) {
  const families = state.summary?.families ?? [];
  const fallbackKey = state.summary ? (bestFamilyRow(state.summary)?.key ?? null) : null;
  const effectiveKey = familyKey ?? fallbackKey;
  const { data: detail, error, isLoading } = useStudyFamily(effectiveKey);
  const spread = detail ? seedReturnSpread(detail) : null;

  return (
    <div className="space-y-4">
      {families.length > 0 && (
        <Select
          id="guia-family"
          label={es.guia.labels.chooseFamily}
          value={effectiveKey ?? ""}
          options={families.map((f) => ({ value: f.key, label: `${f.family} · ${f.symbol}` }))}
          onChange={onSelectFamily}
        />
      )}

      {detail ? (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard label={es.study.table.seeds} value={fmtInt(detail.n_seeds)} />
            <StatCard label={es.study.detail.bars} value={fmtInt(detail.n_bars)} />
            <StatCard label={es.study.table.gate} value={detail.gate} />
          </div>

          <SeedEquityChart detail={detail} height={280} />

          {spread && (
            <p className="text-sm text-fg">
              {es.study.detail.seedSpread
                .replace("{min}", fmtSignedPercent(spread.min))
                .replace("{max}", fmtSignedPercent(spread.max))}
            </p>
          )}

          <div>
            <CardHeader title={es.study.detail.seedTableTitle} />
            {detail.seeds.length > 0 ? (
              <DataTable
                columns={seedColumns}
                rows={[...detail.seeds].sort((a, b) => a.seed - b.seed)}
                rowKey={(s) => String(s.seed)}
                dense
              />
            ) : (
              <EmptyState title={es.common.noData} />
            )}
          </div>
        </>
      ) : (
        <GuideDataState error={state.error ?? error} isLoading={state.isLoading || isLoading} />
      )}
    </div>
  );
}

export function CostesPanel({ state }: { state: StudyState }) {
  const rows = state.summary ? costCriterionRows(state.summary.families) : [];

  return (
    <div className="space-y-4">
      <Illustration
        title={es.guia.figures.costLadder.title}
        caption={es.guia.figures.costLadder.caption}
      >
        <Bars bars={costLadderBars()} />
      </Illustration>

      <Card className="bg-surface-2">
        <CardHeader
          title={es.guia.labels.costCriterionTitle}
          subtitle={es.guia.labels.costCriterionSubtitle}
        />
        {state.summary == null ? (
          <GuideDataState error={state.error} isLoading={state.isLoading} />
        ) : rows.length > 0 ? (
          <DataTable columns={costColumns} rows={rows} rowKey={(r) => r.key} dense />
        ) : (
          <EmptyState title={es.guia.labels.costCriterionEmpty} hint={es.guia.data.notServedHint} />
        )}
      </Card>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <NotServed label={es.guia.labels.costModelNotServed} />
      </div>
    </div>
  );
}
