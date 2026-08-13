"use client";

import { Badge } from "@/components/ui/Badge";
import type { StudyCriterion, StudyMinTradesVeto } from "@/lib/api-types";
import { cn } from "@/lib/cn";
import { fmtInt } from "@/lib/format";
import { es } from "@/lib/i18n/es";
import { criterionPercent } from "@/lib/study";

function Bar({
  passed,
  of,
  required,
  met,
}: {
  passed: number;
  of: number;
  required: number;
  met: boolean;
}) {
  const width = criterionPercent(passed, of);
  const marker = criterionPercent(required, of);
  return (
    <div className="relative h-2.5 w-full overflow-hidden rounded-full bg-surface-2">
      <div
        className={cn("h-full rounded-full", met ? "bg-positive" : "bg-negative")}
        style={{ width: `${width}%` }}
      />
      <span
        aria-hidden
        title={`${es.study.criteria.required} ${required}/${of}`}
        className="absolute top-0 h-full w-px bg-fg/70"
        style={{ left: `${marker}%` }}
      />
    </div>
  );
}

/**
 * The promotion criteria as they were scored across seeds, plus the minimum
 * trades veto rendered apart from them — it is a veto, not a criterion.
 */
export function CriteriaBars({
  criteria,
  veto,
  gloss,
}: {
  criteria: StudyCriterion[];
  veto?: StudyMinTradesVeto | null;
  gloss?: Record<string, string>;
}) {
  return (
    <div className="space-y-4">
      <ul className="space-y-3">
        {criteria.map((criterion) => (
          <li key={criterion.key} className="space-y-1.5">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <span className="text-sm text-fg">{criterion.label}</span>
              <span className="flex items-center gap-2 text-xs">
                <span className={cn("tabular", criterion.met ? "text-positive" : "text-negative")}>
                  {fmtInt(criterion.passed)}/{fmtInt(criterion.of)}
                </span>
                <span className="tabular text-muted">
                  {es.study.criteria.required} {fmtInt(criterion.required)}/{fmtInt(criterion.of)}
                </span>
              </span>
            </div>
            <Bar
              passed={criterion.passed}
              of={criterion.of}
              required={criterion.required}
              met={criterion.met}
            />
            {gloss?.[criterion.key] && <p className="text-xs text-muted">{gloss[criterion.key]}</p>}
          </li>
        ))}
      </ul>

      {veto && (
        <div className="rounded-md border border-dashed border-border bg-surface-2 px-3 py-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-sm text-fg">
              {es.study.criteria.vetoLabel}
              <Badge tone={veto.triggered ? "negative" : "neutral"} className="ml-2">
                {veto.triggered ? es.study.criteria.vetoTriggered : es.study.criteria.vetoClear}
              </Badge>
            </span>
            <span className="tabular text-xs text-muted">
              {fmtInt(veto.passed)}/{fmtInt(veto.of)}
            </span>
          </div>
          <p className="mt-2 text-xs text-muted">{es.study.criteria.vetoNote}</p>
        </div>
      )}
    </div>
  );
}
