import { useI18n, type Dictionary } from "@/lib/i18n";
import { cn } from "@/lib/cn";
import {
  sparkDomain,
  sparkPath,
  sparkProject,
  type SeriesTone,
  type SparkBox,
  type SparkSeries,
} from "@/lib/guia";

const TONE_CLASS: Record<SeriesTone, string> = {
  accent: "text-accent",
  muted: "text-muted",
  positive: "text-positive",
  negative: "text-negative",
};

const BOX: SparkBox = { width: 320, height: 130, pad: 8 };

const SERIES_LABEL = (t: Dictionary): Record<string, string> => t.guia.series;

/**
 * Tiny line/scatter drawing for the didactic figures. No axis values are
 * printed: only the shape of the curves carries meaning here.
 */
export function Sparkline({ series }: { series: SparkSeries[] }) {
  const t = useI18n();
  const domain = sparkDomain(series);

  return (
    <div className="space-y-2">
      <svg
        viewBox={`0 0 ${BOX.width} ${BOX.height}`}
        className="h-auto w-full rounded-md border border-border bg-surface"
        role="presentation"
        aria-hidden
      >
        {series.map((s) =>
          s.kind === "line" ? (
            <path
              key={s.key}
              d={sparkPath(s.points, BOX, domain)}
              fill="none"
              stroke="currentColor"
              strokeWidth={s.dashed ? 1.5 : 2}
              strokeDasharray={s.dashed ? "4 3" : undefined}
              className={TONE_CLASS[s.tone]}
            />
          ) : (
            <g key={s.key} className={TONE_CLASS[s.tone]} fill="currentColor">
              {s.points.map((point, i) => {
                const { x, y } = sparkProject(point, BOX, domain);
                return <circle key={`${s.key}-${i}`} cx={x} cy={y} r={2.5} />;
              })}
            </g>
          )
        )}
      </svg>

      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
        {series.map((s) => (
          <li key={s.key} className="inline-flex items-center gap-2">
            <span
              aria-hidden
              className={cn(
                "h-0.5 w-6 rounded",
                s.tone === "accent" && "bg-accent",
                s.tone === "muted" && "bg-muted",
                s.tone === "positive" && "bg-positive",
                s.tone === "negative" && "bg-negative"
              )}
            />
            {SERIES_LABEL(t)[s.key] ?? s.key}
          </li>
        ))}
      </ul>
    </div>
  );
}
