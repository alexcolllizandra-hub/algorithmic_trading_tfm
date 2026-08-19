import { StudyUnavailable } from "@/components/study/StudyUnavailable";
import { StatCard } from "@/components/ui/StatCard";
import { EmptyState, Skeleton } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useI18n } from "@/lib/i18n";
import type { StudySummaryResponse } from "@/lib/api-types";

/** The study payload as the guide receives it, fetched once for every panel. */
export interface StudyState {
  summary: StudySummaryResponse | undefined;
  error?: unknown;
  isLoading?: boolean;
}

/**
 * What a panel shows when the study payload is missing: a load state, the
 * upstream error, or an explicit "no disponible" status. Never a zero.
 */
export function GuideDataState({ error, isLoading }: { error?: unknown; isLoading?: boolean }) {
  const t = useI18n();
  if (error) return <StudyUnavailable error={error} />;
  if (isLoading) return <Skeleton className="h-24" />;
  return (
    <EmptyState
      title={t.guia.data.unavailableTitle}
      hint={
        <span className="inline-flex flex-wrap items-center justify-center gap-2">
          {t.guia.data.unavailableHint}
          <StatusBadge status={null} />
        </span>
      }
    />
  );
}

/**
 * A quantity the guide deliberately does not invent: the study endpoints do not
 * publish it, so the card reports a status and says where the value lives.
 */
export function NotServed({ label, hint }: { label: string; hint?: string }) {
  const t = useI18n();
  return (
    <StatCard
      label={label}
      value={<StatusBadge status={null} />}
      sub={hint ?? t.guia.data.notServedHint}
    />
  );
}
