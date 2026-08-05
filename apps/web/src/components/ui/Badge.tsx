import { cn } from "@/lib/cn";
import type { RunKind } from "@/lib/api-types";

type Tone = "neutral" | "accent" | "positive" | "negative" | "warn";

const TONES: Record<Tone, string> = {
  neutral: "border-border bg-surface-2 text-muted",
  accent: "border-accent/40 bg-accent/15 text-accent",
  positive: "border-positive/40 bg-positive/10 text-positive",
  negative: "border-negative/40 bg-negative/10 text-negative",
  warn: "border-warn/40 bg-warn/10 text-warn",
};

export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: React.ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        TONES[tone],
        className
      )}
    >
      {children}
    </span>
  );
}

const KIND_TONE: Record<RunKind, Tone> = {
  "synthetic-smoke": "warn",
  development: "accent",
  "final-holdout": "negative",
  unknown: "neutral",
};

const KIND_LABEL: Record<RunKind, string> = {
  "synthetic-smoke": "SYNTHETIC SMOKE",
  development: "DEVELOPMENT DATA",
  "final-holdout": "FINAL HOLDOUT",
  unknown: "UNKNOWN",
};

export function RunKindBadge({ kind }: { kind: RunKind }) {
  return <Badge tone={KIND_TONE[kind] ?? "neutral"}>{KIND_LABEL[kind] ?? "UNKNOWN"}</Badge>;
}
