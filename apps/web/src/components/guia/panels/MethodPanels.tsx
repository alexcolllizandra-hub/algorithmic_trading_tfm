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
import { useI18n, type Dictionary } from "@/lib/i18n";
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
import { seedReturnSpread } from "@/lib/study";

const WALK_FORWARD_FOLDS = 4;

const seedColumns = (t: Dictionary): Column<StudySeedResult>[] => [
  {
    key: "seed",
    header: t.study.detail.seedColumn,
    render: (s) => <span className="font-mono text-xs">{fmtInt(s.seed)}</span>,
  },
  {
    key: "ret",
    header: t.study.table.totalReturn,
    align: "right",
    render: (s) => (
      <span className={signClass(s.total_return)}>{fmtSignedPercent(s.total_return)}</span>
    ),
  },
  {
    key: "sharpe",
    header: t.study.table.sharpe,
    align: "right",
    render: (s) => <span className={signClass(s.sharpe)}>{fmtNumber(s.sharpe, 2)}</span>,
  },
  {
    key: "dd",
    header: t.study.table.maxDrawdown,
    align: "right",
    render: (s) => (
      <span className={signClass(s.max_drawdown)}>{fmtSignedPercent(s.max_drawdown)}</span>
    ),
  },
];

const costColumns = (t: Dictionary): Column<CostCriterionRow>[] => [
  {
    key: "family",
    header: t.study.table.family,
    render: (r) => <span className="font-medium text-fg">{r.family}</span>,
  },
  { key: "symbol", header: t.study.table.symbol, render: (r) => r.symbol },
  {
    key: "passed",
    header: t.guia.labels.criterionPassed,
    align: "right",
    render: (r) => (
      <span className={r.met ? "text-positive" : "text-negative"}>
        {fmtInt(r.passed)}/{fmtInt(r.of)}
      </span>
    ),
  },
  {
    key: "required",
    header: t.guia.labels.criterionRequired,
    align: "right",
    render: (r) => `${fmtInt(r.required)}/${fmtInt(r.of)}`,
  },
  {
    key: "met",
    header: t.study.table.verdict,
    align: "right",
    render: (r) => (
      <Badge tone={r.met ? "positive" : "negative"}>
        {r.met ? t.study.corrections.yes : t.study.corrections.no}
      </Badge>
    ),
  },
];

export function ParticionesPanel({ state }: { state: StudyState }) {
  const t = useI18n();
  const { summary } = state;
  return (
    <div className="space-y-4">
      <Illustration title={t.guia.figures.splits.title} caption={t.guia.figures.splits.caption}>
        <Timeline rows={splitTimelineRows()} rowLabels={t.guia.figures.splits.rows} />
      </Illustration>

      {summary ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <StatCard
            label={t.guia.labels.holdoutState}
            value={<StatusBadge status={summary.holdout_opened ? "EXECUTED" : "HOLDOUT_LOCKED"} />}
            sub={summary.holdout_opened ? undefined : t.guia.labels.holdoutOpenedFalse}
          />
          <StatCard
            label={t.study.headline.rowsLabel}
            value={fmtInt(summary.families.length)}
            sub={t.study.headline.units}
          />
        </div>
      ) : (
        <GuideDataState error={state.error} isLoading={state.isLoading} />
      )}
    </div>
  );
}

export function WalkForwardPanel() {
  const t = useI18n();
  return (
    <div className="space-y-4">
      <Illustration
        title={t.guia.figures.walkForward.title}
        caption={t.guia.figures.walkForward.caption}
      >
        <Timeline
          rows={walkForwardRows(WALK_FORWARD_FOLDS)}
          rowLabels={foldRowLabels(WALK_FORWARD_FOLDS, t.guia.figures.walkForward.foldLabel)}
        />
      </Illustration>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <NotServed label={t.guia.labels.foldsNotServed} hint={t.guia.labels.seeMethodology} />
      </div>
    </div>
  );
}

export function PurgeEmbargoPanel() {
  const t = useI18n();
  return (
    <div className="space-y-4">
      <Illustration
        title={t.guia.figures.purgeEmbargo.title}
        caption={t.guia.figures.purgeEmbargo.caption}
      >
        <Timeline rows={purgeEmbargoRows()} rowLabels={t.guia.figures.purgeEmbargo.rows} />
      </Illustration>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <NotServed label={t.guia.labels.purgeNotServed} hint={t.guia.labels.seeMethodology} />
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
  const t = useI18n();
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
          label={t.guia.labels.chooseFamily}
          value={effectiveKey ?? ""}
          options={families.map((f) => ({ value: f.key, label: `${f.family} · ${f.symbol}` }))}
          onChange={onSelectFamily}
        />
      )}

      {detail ? (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard label={t.study.table.seeds} value={fmtInt(detail.n_seeds)} />
            <StatCard label={t.study.detail.bars} value={fmtInt(detail.n_bars)} />
            <StatCard label={t.study.table.gate} value={detail.gate} />
          </div>

          <SeedEquityChart detail={detail} height={280} />

          {spread && (
            <p className="text-sm text-fg">
              {t.study.detail.seedSpread
                .replace("{min}", fmtSignedPercent(spread.min))
                .replace("{max}", fmtSignedPercent(spread.max))}
            </p>
          )}

          <div>
            <CardHeader title={t.study.detail.seedTableTitle} />
            {detail.seeds.length > 0 ? (
              <DataTable
                columns={seedColumns(t)}
                rows={[...detail.seeds].sort((a, b) => a.seed - b.seed)}
                rowKey={(s) => String(s.seed)}
                dense
              />
            ) : (
              <EmptyState title={t.common.noData} />
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
  const t = useI18n();
  const rows = state.summary ? costCriterionRows(state.summary.families) : [];

  return (
    <div className="space-y-4">
      <Illustration
        title={t.guia.figures.costLadder.title}
        caption={t.guia.figures.costLadder.caption}
      >
        <Bars bars={costLadderBars()} />
      </Illustration>

      <Card className="bg-surface-2">
        <CardHeader
          title={t.guia.labels.costCriterionTitle}
          subtitle={t.guia.labels.costCriterionSubtitle}
        />
        {state.summary == null ? (
          <GuideDataState error={state.error} isLoading={state.isLoading} />
        ) : rows.length > 0 ? (
          <DataTable columns={costColumns(t)} rows={rows} rowKey={(r) => r.key} dense />
        ) : (
          <EmptyState title={t.guia.labels.costCriterionEmpty} hint={t.guia.data.notServedHint} />
        )}
      </Card>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <NotServed label={t.guia.labels.costModelNotServed} />
      </div>
    </div>
  );
}
