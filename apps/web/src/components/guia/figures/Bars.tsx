import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/cn";
import { barWidths, type GuideBar, type SeriesTone } from "@/lib/guia";

const TONE_CLASS: Record<SeriesTone, string> = {
  accent: "bg-accent/70",
  muted: "bg-muted/50",
  positive: "bg-positive/70",
  negative: "bg-negative/70",
};

/**
 * Labelled bars whose lengths are relative to the largest one. The magnitudes
 * are invented, so no value is printed next to the bar.
 */
export function Bars({ bars }: { bars: GuideBar[] }) {
  const barLabel: Record<string, string> = useI18n().guia.bars;
  const widths = barWidths(bars);

  return (
    <ul className="space-y-2.5">
      {bars.map((bar, i) => (
        <li key={bar.key} className="space-y-1">
          <p className="text-xs text-muted">{barLabel[bar.key] ?? bar.key}</p>
          <div aria-hidden className="h-3 w-full overflow-hidden rounded-full bg-surface-2">
            <div
              className={cn("h-full rounded-full", TONE_CLASS[bar.tone])}
              style={{ width: `${widths[i]?.pct ?? 0}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
