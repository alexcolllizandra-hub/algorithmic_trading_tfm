"use client";

import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { EmptyState } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { DataTable, type Column } from "@/components/ui/Table";
import { useI18n } from "@/lib/i18n";
import type { StudyFamilySummary } from "@/lib/api-types";
import { cn } from "@/lib/cn";
import { fmtInt, fmtNumber, fmtSignedPercent, signClass } from "@/lib/format";
import {
  ALL,
  NO_FILTERS,
  distinctValues,
  filterFamilies,
  sortFamilies,
  type SortDirection,
  type StudySortKey,
} from "@/lib/study";

function SortHeader({
  label,
  columnKey,
  activeKey,
  direction,
  onSort,
}: {
  label: string;
  columnKey: StudySortKey;
  activeKey: StudySortKey;
  direction: SortDirection;
  onSort: (key: StudySortKey) => void;
}) {
  const t = useI18n();
  const active = activeKey === columnKey;
  return (
    <button
      type="button"
      onClick={() => onSort(columnKey)}
      aria-label={`${label} (${direction === "asc" ? t.study.table.sortAsc : t.study.table.sortDesc})`}
      className={cn(
        "inline-flex items-center gap-1 uppercase tracking-wide hover:text-fg",
        active && "text-accent"
      )}
    >
      {label}
      <span aria-hidden className="text-[10px]">
        {active ? (direction === "asc" ? "\u25B2" : "\u25BC") : "\u21C5"}
      </span>
    </button>
  );
}

export function MasterTable({
  families,
  selectedKey,
  onSelect,
}: {
  families: StudyFamilySummary[];
  selectedKey: string | null;
  onSelect: (key: string) => void;
}) {
  const t = useI18n();
  const [filters, setFilters] = useState(NO_FILTERS);
  const [sortKey, setSortKey] = useState<StudySortKey>("total_return");
  const [direction, setDirection] = useState<SortDirection>("desc");

  const rows = useMemo(
    () => sortFamilies(filterFamilies(families, filters), sortKey, direction),
    [families, filters, sortKey, direction]
  );

  const onSort = (key: StudySortKey) => {
    if (key === sortKey) {
      setDirection((d) => (d === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(key);
    setDirection(key === "p_value" ? "asc" : "desc");
  };

  const options = (field: keyof StudyFamilySummary) => [
    { value: ALL, label: t.study.table.all },
    ...distinctValues(families, field).map((v) => ({ value: v, label: v })),
  ];

  const columns: Column<StudyFamilySummary>[] = [
    {
      key: "family",
      header: t.study.table.family,
      render: (r) => <span className="font-medium text-fg">{r.family}</span>,
    },
    { key: "gate", header: t.study.table.gate, render: (r) => <Badge>{r.gate}</Badge> },
    { key: "symbol", header: t.study.table.symbol, render: (r) => r.symbol },
    {
      key: "total_return",
      header: (
        <SortHeader
          label={t.study.table.totalReturn}
          columnKey="total_return"
          activeKey={sortKey}
          direction={direction}
          onSort={onSort}
        />
      ),
      align: "right",
      render: (r) => (
        <span className={signClass(r.total_return)}>{fmtSignedPercent(r.total_return)}</span>
      ),
    },
    {
      key: "sharpe",
      header: (
        <SortHeader
          label={t.study.table.sharpe}
          columnKey="sharpe"
          activeKey={sortKey}
          direction={direction}
          onSort={onSort}
        />
      ),
      align: "right",
      render: (r) => <span className={signClass(r.sharpe)}>{fmtNumber(r.sharpe, 2)}</span>,
    },
    {
      key: "max_drawdown",
      header: t.study.table.maxDrawdown,
      align: "right",
      render: (r) => (
        <span className={signClass(r.max_drawdown)}>{fmtSignedPercent(r.max_drawdown)}</span>
      ),
    },
    {
      key: "p_value",
      header: (
        <SortHeader
          label={t.study.table.pValue}
          columnKey="p_value"
          activeKey={sortKey}
          direction={direction}
          onSort={onSort}
        />
      ),
      align: "right",
      render: (r) => fmtNumber(r.p_value, 4),
    },
    {
      key: "holm",
      header: t.study.table.holm,
      align: "right",
      render: (r) => fmtNumber(r.holm_adjusted_p, 3),
    },
    {
      key: "bh",
      header: t.study.table.bh,
      align: "right",
      render: (r) => fmtNumber(r.bh_adjusted_p, 4),
    },
    {
      key: "verdict",
      header: t.study.table.verdict,
      render: (r) => <StatusBadge status={r.verdict} />,
    },
    {
      key: "open",
      header: "",
      align: "right",
      render: (r) => (
        <button
          type="button"
          onClick={() => onSelect(r.key)}
          className="rounded border border-border px-2 py-0.5 text-xs text-accent hover:bg-accent/10"
        >
          {t.study.table.open}
        </button>
      ),
    },
  ];

  return (
    <Card>
      <CardHeader title={t.study.table.title} subtitle={t.study.table.subtitle} />

      <div className="mb-4 flex flex-wrap items-end gap-4">
        <Select
          id="study-gate"
          label={t.study.table.filterGate}
          value={filters.gate}
          options={options("gate")}
          onChange={(gate) => setFilters((f) => ({ ...f, gate }))}
        />
        <Select
          id="study-symbol"
          label={t.study.table.filterSymbol}
          value={filters.symbol}
          options={options("symbol")}
          onChange={(symbol) => setFilters((f) => ({ ...f, symbol }))}
        />
        <Select
          id="study-verdict"
          label={t.study.table.filterVerdict}
          value={filters.verdict}
          options={options("verdict")}
          onChange={(verdict) => setFilters((f) => ({ ...f, verdict }))}
        />
        <p className="tabular text-xs text-muted">
          {t.study.table.shown
            .replace("{n}", fmtInt(rows.length))
            .replace("{total}", fmtInt(families.length))}
        </p>
      </div>

      {rows.length === 0 ? (
        <EmptyState title={t.study.table.empty} />
      ) : (
        <DataTable
          columns={columns}
          rows={rows}
          rowKey={(r) => r.key}
          dense
          onRowClick={(r) => onSelect(r.key)}
          isRowSelected={(r) => r.key === selectedKey}
        />
      )}

      <p className="mt-3 text-xs text-muted">{t.study.table.nullNote}</p>
    </Card>
  );
}
