"use client";

// Collapsed annex with the frozen matplotlib EDA figures — the artifacts the
// thesis cites. Served by the optional local API; when it is offline the
// annex degrades to a one-line hint instead of an error state.

import { API_BASE } from "@/lib/api";
import type { EdaFigureModel } from "@/lib/api-types";
import { Badge } from "@/components/ui/Badge";
import { useEdaFigures } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n";

function FigureGallery({ figures }: { figures: EdaFigureModel[] }) {
  return (
    <div className="mt-4 grid grid-cols-1 gap-6 lg:grid-cols-2">
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

export function EdaFigureAnnex() {
  const t = useI18n();
  const { data, error } = useEdaFigures({ limit: 200 });
  const figures = data?.items ?? [];

  return (
    <details className="rounded-card border border-border bg-surface p-6">
      <summary className="cursor-pointer select-none">
        <span className="text-base font-semibold">{t.eda.annexTitle}</span>
        <span className="ml-3 text-sm text-muted">
          {figures.length > 0 ? t.eda.annexOpen.replace("{n}", String(figures.length)) : ""}
        </span>
        <p className="mt-1.5 text-sm font-normal text-muted">{t.eda.annexSubtitle}</p>
      </summary>
      {error || figures.length === 0 ? (
        <p className="mt-4 rounded-md border border-border bg-surface-2 px-4 py-3 font-mono text-xs text-muted">
          {t.eda.annexApiNote}
        </p>
      ) : (
        <FigureGallery figures={figures} />
      )}
    </details>
  );
}
