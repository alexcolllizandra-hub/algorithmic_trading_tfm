"use client";

import { useCallback, useEffect, useState } from "react";

import { cn } from "@/lib/cn";
import {
  GUIDE_PANEL_IDS,
  mostVisible,
  panelAnchor,
  panelCopy,
  progressPercent,
  scrollBehaviorFor,
  tocItems,
  type GuidePanelId,
} from "@/lib/guia";
import { es } from "@/lib/i18n/es";

/** Reads the OS motion preference, tolerating environments without matchMedia. */
function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(query.matches);
    const onChange = (event: MediaQueryListEvent) => setReduced(event.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  return reduced;
}

/**
 * Sticky table of contents and progress indicator for the thirteen panels.
 *
 * Scrolling is smooth unless the reader asked for reduced motion, and each jump
 * moves focus to the target panel so keyboard users follow the same path.
 */
export function GuideToc() {
  const [active, setActive] = useState<GuidePanelId>(GUIDE_PANEL_IDS[0]);
  const reducedMotion = usePrefersReducedMotion();
  const items = tocItems();

  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const ratios = new Map<GuidePanelId, number>();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const id = entry.target.getAttribute("data-guide-panel") as GuidePanelId | null;
          if (id) ratios.set(id, entry.intersectionRatio);
        }
        const next = mostVisible(GUIDE_PANEL_IDS.map((id) => ({ id, ratio: ratios.get(id) ?? 0 })));
        if (next) setActive(next);
      },
      { threshold: [0, 0.15, 0.35, 0.6, 0.9] }
    );
    for (const id of GUIDE_PANEL_IDS) {
      const element = document.getElementById(panelAnchor(id));
      if (element) observer.observe(element);
    }
    return () => observer.disconnect();
  }, []);

  const jump = useCallback(
    (id: GuidePanelId) => {
      setActive(id);
      const element = document.getElementById(panelAnchor(id));
      if (!element) return;
      element.scrollIntoView({ behavior: scrollBehaviorFor(reducedMotion), block: "start" });
      element.focus({ preventScroll: true });
    },
    [reducedMotion]
  );

  const progress = progressPercent(active);

  return (
    <nav
      aria-label={es.guia.toc.navLabel}
      className="sticky top-14 z-10 -mx-6 border-b border-border bg-bg/95 px-6 py-3 backdrop-blur"
    >
      <div className="flex flex-wrap items-center gap-3">
        <p className="tabular text-xs font-medium text-fg">
          {es.guia.toc.progress
            .replace("{n}", String(items.find((i) => i.id === active)?.number ?? 1))
            .replace("{total}", String(items.length))}
        </p>
        <div
          role="progressbar"
          aria-label={es.guia.toc.progressLabel}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progress}
          className="h-1.5 min-w-[100px] flex-1 overflow-hidden rounded-full bg-surface-2"
        >
          <div className="h-full rounded-full bg-accent" style={{ width: `${progress}%` }} />
        </div>
      </div>

      <ol className="mt-2 flex flex-wrap gap-1">
        {items.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              onClick={() => jump(item.id)}
              title={item.title}
              aria-label={es.guia.toc.jump
                .replace("{n}", String(item.number))
                .replace("{title}", item.title)}
              aria-current={item.id === active ? "true" : undefined}
              className={cn(
                "tabular h-7 w-7 rounded-md border text-xs transition",
                item.id === active
                  ? "border-accent bg-accent/15 text-accent"
                  : "border-border text-muted hover:bg-surface-2 hover:text-fg"
              )}
            >
              {item.number}
            </button>
          </li>
        ))}
      </ol>

      <p className="mt-1.5 text-xs text-muted">{panelCopy(active).title}</p>
    </nav>
  );
}
