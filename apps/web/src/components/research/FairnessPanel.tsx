"use client";

import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type Column } from "@/components/ui/Table";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/States";
import type { ValidityCheck, ValidityWarning } from "@/lib/api-types";
import { fmtInt } from "@/lib/format";
import { es } from "@/lib/i18n/es";
import { useValidity } from "@/lib/hooks";

const STATUS_TONE: Record<ValidityCheck["status"], "positive" | "warn" | "negative"> = {
  pass: "positive",
  warn: "warn",
  fail: "negative",
};

const STATUS_LABEL: Record<ValidityCheck["status"], string> = {
  pass: es.validity.statusPass,
  warn: es.validity.statusWarn,
  fail: es.validity.statusFail,
};

const SEV_TONE: Record<ValidityWarning["severity"], "accent" | "warn" | "negative"> = {
  info: "accent",
  warn: "warn",
  error: "negative",
};

export function FairnessPanel({ runId }: { runId: string | null }) {
  const { data, error, isLoading } = useValidity(runId);

  const checkColumns: Column<ValidityCheck>[] = [
    { key: "label", header: "Check", render: (c) => c.label_es },
    {
      key: "status",
      header: "Estado",
      render: (c) => <Badge tone={STATUS_TONE[c.status]}>{STATUS_LABEL[c.status]}</Badge>,
    },
    {
      key: "detail",
      header: "Detalle",
      render: (c) => <span className="text-sm text-muted">{c.detail_es}</span>,
    },
  ];

  if (!runId) return <EmptyState title={es.common.selectRun} />;
  if (isLoading) return <Skeleton className="h-48" />;
  if (error) return <ErrorState title="No se pudo cargar validez" detail={error.message} />;
  if (!data) return <EmptyState title="Sin datos de validez" />;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader
          title={es.validity.title}
          subtitle={es.validity.subtitle}
          right={
            data.equal_effective_evaluations != null ? (
              <Badge tone={data.equal_effective_evaluations ? "positive" : "negative"}>
                {es.validity.equalEvaluations}: {data.equal_effective_evaluations ? "sí" : "no"}
              </Badge>
            ) : undefined
          }
        />
        <div className="mb-4 grid grid-cols-2 gap-4 md:grid-cols-4">
          <Stat label="Budget" value={fmtInt(data.budget)} />
          <Stat label="RS evaluados" value={fmtInt(data.random_search_evaluated)} />
          <Stat label="GA evaluados" value={fmtInt(data.genetic_algorithm_evaluated)} />
          <Stat label="Tipo run" value={data.kind} />
        </div>
        <DataTable columns={checkColumns} rows={data.checks} rowKey={(c) => c.id} dense />
      </Card>

      {data.warnings.length > 0 && (
        <Card>
          <CardHeader title="Advertencias" />
          <ul className="space-y-2">
            {data.warnings.map((w) => (
              <li
                key={w.code}
                className="flex items-start gap-2 rounded-md border border-border bg-surface-2 px-3 py-2 text-sm"
              >
                <Badge tone={SEV_TONE[w.severity]}>{w.severity}</Badge>
                <span className="text-muted">{w.message_es}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-md border border-border bg-surface-2 px-3 py-2">
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
      <div className="tabular mt-1 text-sm font-medium">{value}</div>
    </div>
  );
}
