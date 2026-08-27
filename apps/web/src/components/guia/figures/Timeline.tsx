import { useI18n, type Dictionary } from "@/lib/i18n";
import { cn } from "@/lib/cn";
import { segmentWidths, timelineLegend, type GuideTimelineRow, type SegmentTone } from "@/lib/guia";

const TONE_CLASS: Record<SegmentTone, string> = {
  train: "bg-accent/30",
  val: "bg-accent/70",
  test: "bg-positive/60",
  holdout: "bg-warn/45",
  development: "bg-accent/25",
  purge: "bg-negative/55",
  embargo: "bg-warn/70",
  signal: "bg-accent/70",
  exec: "bg-positive/70",
  future: "bg-negative/60",
  neutral: "bg-surface-2",
};

const LEGEND = (t: Dictionary): Record<string, string> => t.guia.legend;

/**
 * Segmented time bars: the primitive behind every split, fold, purge and
 * leakage drawing. Widths are proportions of the row, never bar counts.
 */
export function Timeline({
  rows,
  rowLabels,
}: {
  rows: GuideTimelineRow[];
  rowLabels?: Record<string, string>;
}) {
  const t = useI18n();
  return (
    <div className="space-y-3">
      {rows.map((row) => {
        const widths = segmentWidths(row.segments);
        return (
          <div key={row.key}>
            <p className="mb-1 text-xs text-muted">{rowLabels?.[row.key] ?? row.key}</p>
            <div
              aria-hidden
              className="flex h-6 w-full overflow-hidden rounded-md border border-border"
            >
              {row.segments.map((segment, i) => (
                <span
                  key={`${row.key}-${segment.key}`}
                  className={cn("h-full", TONE_CLASS[segment.tone])}
                  style={{ width: `${widths[i]?.pct ?? 0}%` }}
                />
              ))}
            </div>
          </div>
        );
      })}

      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
        {timelineLegend(rows).map((entry) => (
          <li key={entry.key} className="inline-flex items-center gap-2">
            <span
              aria-hidden
              className={cn("h-2.5 w-4 rounded-sm border border-border", TONE_CLASS[entry.tone])}
            />
            {LEGEND(t)[entry.key] ?? entry.key}
          </li>
        ))}
      </ul>
    </div>
  );
}
