import { Badge } from "@/components/ui/Badge";
import { es } from "@/lib/i18n/es";

/**
 * Wrapper for every didactic drawing on the guide.
 *
 * The "ejemplo ilustrativo" badge is not decoration: these figures carry
 * invented values, so they must be impossible to mistake for a result. Nothing
 * inside prints a numeric value.
 */
export function Illustration({
  title,
  caption,
  children,
}: {
  title: string;
  caption: string;
  children: React.ReactNode;
}) {
  return (
    <figure className="rounded-card border border-dashed border-warn/50 bg-warn/5 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-medium text-fg">{title}</span>
        <Badge tone="warn">{es.guia.illustrative.badge}</Badge>
      </div>
      <div className="min-w-0">{children}</div>
      <figcaption className="mt-3 space-y-1 text-xs text-muted">
        <p>{caption}</p>
        <p>{es.guia.illustrative.note}</p>
      </figcaption>
    </figure>
  );
}
