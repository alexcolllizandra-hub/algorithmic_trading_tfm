import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/cn";
import type { PDotFigure } from "@/lib/guia";

/**
 * p-values as dots on a 0..1 axis with the alpha threshold drawn.
 *
 * Dots are staggered by index so overlapping values stay visible; the stagger
 * is deterministic and carries no meaning.
 */
export function PDots({ figure }: { figure: PDotFigure }) {
  const t = useI18n();
  return (
    <div className="space-y-2">
      <div aria-hidden className="relative h-20 w-full rounded-md border border-border bg-surface">
        <span
          className="absolute inset-y-0 w-px bg-warn"
          style={{ left: `${figure.alpha * 100}%` }}
        />
        {figure.dots.map((dot, i) => (
          <span
            key={dot.key}
            className={cn(
              "absolute h-2.5 w-2.5 -translate-x-1/2 rounded-full border",
              dot.rejected ? "border-negative bg-negative" : "border-border bg-muted",
              dot.highlighted && "ring-2 ring-accent"
            )}
            style={{ left: `${dot.p * 100}%`, top: `${10 + (i % 5) * 12}px` }}
          />
        ))}
      </div>

      <div className="flex flex-wrap justify-between gap-2 text-xs text-muted">
        <span>{t.guia.pdots.axisStart}</span>
        <span>{t.guia.pdots.axisEnd}</span>
      </div>

      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
        <li className="inline-flex items-center gap-2">
          <span aria-hidden className="h-3 w-px bg-warn" />
          {t.guia.pdots.threshold}
        </li>
        <li className="inline-flex items-center gap-2">
          <span aria-hidden className="h-2.5 w-2.5 rounded-full bg-negative" />
          {t.guia.pdots.rejected}
        </li>
        <li className="inline-flex items-center gap-2">
          <span aria-hidden className="h-2.5 w-2.5 rounded-full bg-muted" />
          {t.guia.pdots.notRejected}
        </li>
        <li className="inline-flex items-center gap-2">
          <span aria-hidden className="h-2.5 w-2.5 rounded-full bg-muted ring-2 ring-accent" />
          {t.guia.pdots.smallest}
        </li>
      </ul>
    </div>
  );
}
