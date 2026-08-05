import { cn } from "@/lib/cn";

type Tone = "info" | "warning" | "error";

const TONE_CLASS: Record<Tone, string> = {
  info: "border-accent/40 bg-accent/10 text-fg",
  warning: "border-warn/50 bg-warn/10 text-warn",
  error: "border-negative/40 bg-negative/10 text-negative",
};

export function InterpretationBox({
  tone = "info",
  title,
  children,
}: {
  tone?: Tone;
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <div role="note" className={cn("rounded-card border px-4 py-3 text-sm", TONE_CLASS[tone])}>
      {title && <p className="mb-1 font-semibold">{title}</p>}
      <div>{children}</div>
    </div>
  );
}
