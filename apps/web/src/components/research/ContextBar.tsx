"use client";

import { useI18n } from "@/lib/i18n";
import type { FoldSelection } from "@/lib/api-types";
import { fmtDate } from "@/lib/format";

export function ContextBar({ selection }: { selection: FoldSelection | null }) {
  const t = useI18n();
  if (!selection) return null;

  const period =
    selection.periodStart && selection.periodEnd
      ? `${fmtDate(selection.periodStart)} → ${fmtDate(selection.periodEnd)}`
      : "—";

  return (
    <div className="sticky top-[52px] z-[9] -mx-6 border-b border-border bg-surface/95 px-6 py-2 backdrop-blur">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-1 text-xs">
        <Item label={t.contextBar.run} value={selection.runId} mono />
        <Item label={t.contextBar.method} value={selection.method} />
        <Item label={t.contextBar.fold} value={String(selection.fold)} />
        <Item label={t.contextBar.candidate} value={selection.candidateId ?? "—"} mono />
        <Item label={t.contextBar.period} value={period} />
      </div>
    </div>
  );
}

function Item({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="uppercase tracking-wide text-muted">{label}</span>
      <span className={mono ? "font-mono text-fg" : "text-fg"}>{value}</span>
    </span>
  );
}
