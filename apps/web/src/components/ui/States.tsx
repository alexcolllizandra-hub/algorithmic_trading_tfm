import { cn } from "@/lib/cn";

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("skeleton h-4 w-full", className)} aria-hidden />;
}

export function SkeletonCard() {
  return (
    <div className="rounded-card border border-border bg-surface p-5">
      <Skeleton className="mb-3 h-3 w-24" />
      <Skeleton className="mb-2 h-8 w-40" />
      <Skeleton className="h-3 w-32" />
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: React.ReactNode }) {
  return (
    <div className="rounded-card border border-dashed border-border bg-surface/50 p-8 text-center">
      <p className="font-medium text-fg">{title}</p>
      {hint && <p className="mx-auto mt-2 max-w-md text-sm text-muted">{hint}</p>}
    </div>
  );
}

export function ErrorState({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="rounded-card border border-negative/40 bg-negative/10 p-6" role="alert">
      <p className="font-medium text-negative">{title}</p>
      {detail && <p className="mt-1 text-sm text-negative/90">{detail}</p>}
    </div>
  );
}

export function PartialNotice({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-md border border-warn/40 bg-warn/10 px-3 py-2 text-xs text-warn">
      {children}
    </div>
  );
}
