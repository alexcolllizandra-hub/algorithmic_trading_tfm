import { Card } from "@/components/ui/Card";
import { panelAnchor, panelCopy, panelNumber, panelParts, type GuidePanelId } from "@/lib/guia";

/**
 * The four labelled parts every panel of the guide must carry. They are
 * rendered here and only here, so a panel cannot be added without them.
 */
export function PanelParts({ id }: { id: GuidePanelId }) {
  return (
    <dl data-guide-parts className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-2">
      {panelParts(id).map((part) => (
        <div
          key={part.key}
          data-guide-part={part.key}
          className="rounded-md border border-border bg-surface-2 px-4 py-3"
        >
          <dt className="text-xs font-semibold uppercase tracking-wide text-accent">
            {part.label}
          </dt>
          <dd className="mt-2 text-sm text-muted">{part.text}</dd>
        </div>
      ))}
    </dl>
  );
}

/**
 * One numbered panel: its heading, its body (real figures or a labelled
 * illustration) and the four parts appended by construction.
 */
export function GuidePanel({ id, children }: { id: GuidePanelId; children?: React.ReactNode }) {
  const copy = panelCopy(id);
  const anchor = panelAnchor(id);
  const headingId = `${anchor}-title`;

  return (
    <section
      id={anchor}
      data-guide-panel={id}
      aria-labelledby={headingId}
      tabIndex={-1}
      className="scroll-mt-32"
    >
      <Card>
        <div className="mb-4 flex items-start gap-3">
          <span
            aria-hidden
            className="tabular inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-accent/40 bg-accent/10 text-xs font-semibold text-accent"
          >
            {panelNumber(id)}
          </span>
          <h2 id={headingId} className="text-base font-semibold text-fg">
            {copy.title}
          </h2>
        </div>

        {children}

        <PanelParts id={id} />
      </Card>
    </section>
  );
}
