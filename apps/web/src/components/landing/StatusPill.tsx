"use client";

import type { PhaseStatus } from "@/components/landing/content";
import { useLandingCopy } from "@/components/landing/copy";
import { cn } from "@/lib/cn";

const TONE: Record<PhaseStatus, string> = {
  done: "border-positive/40 bg-positive/10 text-positive",
  "in-review": "border-accent/40 bg-accent/10 text-accent",
  blocked: "border-warn/40 bg-warn/10 text-warn",
  planned: "border-border bg-surface-2 text-muted",
};

export function StatusPill({ status, className }: { status: PhaseStatus; className?: string }) {
  const c = useLandingCopy();
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        TONE[status],
        className
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />
      {c.pipeline.statusLabel[status]}
    </span>
  );
}
