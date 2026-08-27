"use client";

import { InterpretationBox } from "@/components/education/InterpretationBox";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/States";
import { StatCard } from "@/components/ui/StatCard";
import { DataTable, type Column } from "@/components/ui/Table";
import type {
  StudyAdjustment,
  StudyCorrections,
  StudyDeflatedSharpeEntry,
  StudySensitivityRow,
} from "@/lib/api-types";
import { useI18n, type Dictionary } from "@/lib/i18n";
import { fmtInt, fmtNumber, fmtPercent } from "@/lib/format";
import { gaugePercent } from "@/lib/study";

interface AdjustedRow {
  family: string;
  holm: number | null;
  bh: number | null;
}

interface DeflatedRow extends StudyDeflatedSharpeEntry {
  rule: string;
}

interface SensitivityRow extends StudySensitivityRow {
  rule: string;
}

function adjustedRows(holm: StudyAdjustment, bh: StudyAdjustment): AdjustedRow[] {
  const holmValues = holm.adjusted_p_values ?? {};
  const bhValues = bh.adjusted_p_values ?? {};
  const names = [...new Set([...Object.keys(holmValues), ...Object.keys(bhValues)])];
  return names
    .map((family) => ({
      family,
      holm: holmValues[family] ?? null,
      bh: bhValues[family] ?? null,
    }))
    .sort((a, b) => (a.holm ?? 1) - (b.holm ?? 1) || a.family.localeCompare(b.family));
}

const adjustedColumns = (t: Dictionary): Column<AdjustedRow>[] => [
  { key: "family", header: t.study.corrections.familyColumn, render: (r) => r.family },
  {
    key: "holm",
    header: t.study.table.holm,
    align: "right",
    render: (r) => fmtNumber(r.holm, 3),
  },
  { key: "bh", header: t.study.table.bh, align: "right", render: (r) => fmtNumber(r.bh, 4) },
];

const deflatedColumns = (t: Dictionary): Column<DeflatedRow>[] => [
  { key: "rule", header: t.study.corrections.rule, render: (r) => r.rule },
  {
    key: "n",
    header: t.study.corrections.trials,
    align: "right",
    render: (r) => fmtInt(r.n_trials),
  },
  {
    key: "obs",
    header: t.study.corrections.observedSharpe,
    align: "right",
    render: (r) => fmtNumber(r.observed_sharpe_per_observation, 4),
  },
  {
    key: "bench",
    header: t.study.corrections.benchmark,
    align: "right",
    render: (r) => fmtNumber(r.benchmark_sharpe_per_observation, 4),
  },
  {
    key: "dsr",
    header: t.study.corrections.deflated,
    align: "right",
    render: (r) => fmtNumber(r.deflated_sharpe, 4),
  },
  {
    key: "spurious",
    header: t.study.corrections.spurious,
    align: "right",
    render: (r) => fmtPercent(r.probability_best_is_spurious, 2),
  },
];

const sensitivityColumns = (t: Dictionary): Column<SensitivityRow>[] => [
  { key: "rule", header: t.study.corrections.rule, render: (r) => r.rule },
  {
    key: "n",
    header: t.study.corrections.nTests,
    align: "right",
    render: (r) => fmtInt(r.n_tests),
  },
  {
    key: "thr",
    header: t.study.corrections.threshold,
    align: "right",
    render: (r) => (r.bonferroni_threshold == null ? "—" : r.bonferroni_threshold.toExponential(2)),
  },
  {
    key: "p",
    header: t.study.corrections.smallestP,
    align: "right",
    render: (r) => fmtNumber(r.smallest_raw_p_value, 4),
  },
  {
    key: "survive",
    header: t.study.corrections.anySurvive,
    align: "right",
    render: (r) => (
      <Badge tone={r.any_survive ? "positive" : "negative"}>
        {r.any_survive ? t.study.corrections.yes : t.study.corrections.no}
      </Badge>
    ),
  },
];

/** PBO against the 0.5 line that pure noise produces. */
function PboGauge({ pbo }: { pbo: number }) {
  const t = useI18n();
  return (
    <div className="space-y-2">
      <div className="relative h-4 w-full overflow-hidden rounded-full bg-surface-2">
        <div
          className="h-full rounded-full bg-accent/60"
          style={{ width: `${gaugePercent(pbo)}%` }}
        />
        <span
          aria-hidden
          className="absolute top-0 h-full w-px bg-fg"
          style={{ left: `${gaugePercent(0.5)}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-muted">
        <span>0</span>
        <span>{t.study.corrections.pboNoiseLine}</span>
        <span>1</span>
      </div>
    </div>
  );
}

export function CorrectionsPanel({ study }: { study: StudyCorrections }) {
  const t = useI18n();
  const deflated: DeflatedRow[] = Object.entries(study.deflated_sharpe ?? {}).map(
    ([rule, entry]) => ({ rule, ...entry })
  );
  const sensitivity: SensitivityRow[] = Object.entries(study.sensitivity ?? {}).map(
    ([rule, entry]) => ({ rule, ...entry })
  );
  const rows = adjustedRows(study.holm, study.benjamini_hochberg);
  const pbo = study.pbo?.pbo;

  return (
    <Card>
      <CardHeader title={t.study.corrections.title} subtitle={t.study.corrections.subtitle} />

      <InterpretationBox title={t.study.corrections.conclusionTitle}>
        <p>{study.conclusion}</p>
      </InterpretationBox>

      <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label={`${t.study.corrections.holmTitle} — ${t.study.corrections.rejected}`}
          value={fmtInt(study.holm.n_rejected)}
          sub={`α = ${fmtNumber(study.alpha, 2)}`}
          metricKey="holm_adjusted_p"
        />
        <StatCard
          label={`${t.study.corrections.bhTitle} — ${t.study.corrections.rejected}`}
          value={fmtInt(study.benjamini_hochberg.n_rejected)}
          sub={`α = ${fmtNumber(study.alpha, 2)}`}
          metricKey="bh_adjusted_p"
        />
        <StatCard
          label={t.study.corrections.pboSplits}
          value={fmtInt(study.pbo?.n_splits)}
          sub={`${t.study.corrections.pboConfigurations}: ${fmtInt(study.pbo?.n_configurations)}`}
        />
        <StatCard
          label={t.study.headline.configurations}
          value={fmtInt(study.n_configurations_evaluated)}
          metricKey="n_configurations_evaluated"
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div>
          <CardHeader title={t.study.corrections.pboTitle} />
          {pbo != null && Number.isFinite(pbo) ? (
            <div className="space-y-3">
              <p className="tabular text-3xl font-semibold text-fg">{fmtNumber(pbo, 3)}</p>
              <PboGauge pbo={pbo} />
              <p className="text-xs text-muted">{t.study.corrections.pboCaption}</p>
            </div>
          ) : (
            <EmptyState title={t.study.corrections.pboUnavailable} />
          )}
        </div>

        <div>
          <CardHeader title={t.study.corrections.adjustedTitle} />
          {rows.length > 0 ? (
            <DataTable columns={adjustedColumns(t)} rows={rows} rowKey={(r) => r.family} dense />
          ) : (
            <EmptyState title={t.common.noData} />
          )}
        </div>
      </div>

      <div className="mt-6 space-y-3">
        <CardHeader
          title={t.study.corrections.deflatedTitle}
          subtitle={t.study.corrections.deflatedCaption}
        />
        {deflated.length > 0 ? (
          <DataTable columns={deflatedColumns(t)} rows={deflated} rowKey={(r) => r.rule} dense />
        ) : (
          <EmptyState title={t.common.noData} />
        )}
      </div>

      <div className="mt-6 space-y-3">
        <CardHeader
          title={t.study.corrections.sensitivityTitle}
          subtitle={t.study.corrections.sensitivityCaption}
        />
        {sensitivity.length > 0 ? (
          <DataTable
            columns={sensitivityColumns(t)}
            rows={sensitivity}
            rowKey={(r) => r.rule}
            dense
          />
        ) : (
          <EmptyState title={t.common.noData} />
        )}
      </div>

      <div className="mt-6">
        <CardHeader title={t.study.corrections.criteriaByGate} />
        <dl className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {Object.entries(study.criteria_by_gate ?? {}).map(([gate, text]) => (
            <div key={gate} className="rounded-md border border-border bg-surface-2 px-3 py-2">
              <dt className="text-xs font-semibold uppercase tracking-wide text-accent">{gate}</dt>
              <dd className="mt-1 text-xs text-muted">{text}</dd>
            </div>
          ))}
        </dl>
      </div>
    </Card>
  );
}
