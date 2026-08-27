"use client";

import { useMemo, useState } from "react";

import { StudyUnavailable } from "@/components/study/StudyUnavailable";
import { Card, CardHeader } from "@/components/ui/Card";
import { ExploratoryBanner } from "@/components/ui/ExploratoryBanner";
import { Select } from "@/components/ui/Select";
import { EmptyState, Skeleton } from "@/components/ui/States";
import { StatCard } from "@/components/ui/StatCard";
import { DataTable, type Column } from "@/components/ui/Table";
import type { StudyRegimeCell } from "@/lib/api-types";
import { fmtInt, fmtNumber, fmtPercent, fmtSignedPercent, signClass } from "@/lib/format";
import { useStudyRegimes } from "@/lib/hooks";
import { useI18n, type Dictionary } from "@/lib/i18n";
import { ALL } from "@/lib/study";

const buildColumns = (t: Dictionary): Column<StudyRegimeCell>[] => [
  {
    key: "family",
    header: t.study.table.family,
    render: (c) => <span className="font-medium text-fg">{c.family}</span>,
  },
  { key: "gate", header: t.study.table.gate, render: (c) => c.gate ?? "—" },
  { key: "dimension", header: t.study.regimes.dimension, render: (c) => c.dimension ?? "—" },
  { key: "regime", header: t.study.regimes.regime, render: (c) => c.regime ?? "—" },
  {
    key: "bars",
    header: t.study.detail.bars,
    align: "right",
    render: (c) => fmtInt(c.n_bars),
  },
  {
    key: "share",
    header: t.study.regimes.shareOfBars,
    align: "right",
    render: (c) => fmtPercent(c.share_of_bars, 1),
  },
  {
    key: "ret",
    header: t.study.table.totalReturn,
    align: "right",
    render: (c) => (
      <span className={signClass(c.total_return)}>{fmtSignedPercent(c.total_return)}</span>
    ),
  },
  {
    key: "sharpe",
    header: t.study.table.sharpe,
    align: "right",
    render: (c) => (
      <span className={signClass(c.sharpe_annualised)}>{fmtNumber(c.sharpe_annualised, 2)}</span>
    ),
  },
  {
    key: "p",
    header: t.study.table.pValue,
    align: "right",
    render: (c) => fmtNumber(c.p_value, 4),
  },
];

const distinct = (cells: StudyRegimeCell[], field: keyof StudyRegimeCell) => {
  const seen = new Set<string>();
  for (const cell of cells) {
    const value = cell[field];
    if (typeof value === "string" && value.length > 0) seen.add(value);
  }
  return [...seen].sort((a, b) => a.localeCompare(b));
};

export function RegimePanel() {
  const t = useI18n();
  const columns = buildColumns(t);
  const { data, error, isLoading } = useStudyRegimes();
  const [family, setFamily] = useState(ALL);
  const [dimension, setDimension] = useState(ALL);

  const cells = useMemo(() => data?.cells ?? [], [data]);
  const rows = useMemo(
    () =>
      cells.filter(
        (c) =>
          (family === ALL || c.family === family) &&
          (dimension === ALL || c.dimension === dimension)
      ),
    [cells, family, dimension]
  );

  if (error) return <StudyUnavailable error={error} />;
  if (isLoading || !data) return <Skeleton className="h-72" />;

  const correction = data.correction ?? {};
  const survivors = correction.survivors ?? [];

  return (
    <Card>
      <CardHeader title={t.study.regimes.title} subtitle={t.study.regimes.subtitle} />

      <ExploratoryBanner message={t.study.regimes.banner} />

      <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label={t.study.regimes.cells} value={fmtInt(correction.n_cells)} />
        <StatCard label={t.study.regimes.testable} value={fmtInt(correction.n_testable_cells)} />
        <StatCard
          label={t.study.regimes.excluded}
          value={fmtInt(correction.n_excluded_small_cells)}
          sub={`${t.study.regimes.minBars}: ${fmtInt(correction.min_cell_bars)}`}
        />
        <StatCard label={t.study.regimes.survivors} value={fmtInt(survivors.length)} />
      </div>

      <div className="mt-4 flex flex-wrap items-end gap-4">
        <Select
          id="regime-family"
          label={t.study.regimes.filterFamily}
          value={family}
          options={[
            { value: ALL, label: t.study.table.all },
            ...distinct(cells, "family").map((v) => ({ value: v, label: v })),
          ]}
          onChange={setFamily}
        />
        <Select
          id="regime-dimension"
          label={t.study.regimes.filterDimension}
          value={dimension}
          options={[
            { value: ALL, label: t.study.table.all },
            ...distinct(cells, "dimension").map((v) => ({ value: v, label: v })),
          ]}
          onChange={setDimension}
        />
        <p className="tabular text-xs text-muted">
          {t.study.table.shown
            .replace("{n}", fmtInt(rows.length))
            .replace("{total}", fmtInt(cells.length))}
        </p>
      </div>

      <div className="mt-4">
        {rows.length > 0 ? (
          <DataTable
            columns={columns}
            rows={rows}
            rowKey={(c, i) => `${c.family}-${c.dimension}-${c.regime}-${i}`}
            dense
          />
        ) : (
          <EmptyState title={t.study.regimes.empty} />
        )}
      </div>

      {data.conclusion && <p className="mt-4 text-sm text-muted">{data.conclusion}</p>}

      <div className="mt-4">
        <CardHeader title={t.study.regimes.candidateTitle} />
        {data.candidate ? (
          <pre className="overflow-x-auto rounded-md border border-border bg-surface-2 p-3 text-xs text-muted">
            {JSON.stringify(data.candidate, null, 2)}
          </pre>
        ) : (
          <EmptyState title={t.study.regimes.noCandidate} />
        )}
      </div>
    </Card>
  );
}
