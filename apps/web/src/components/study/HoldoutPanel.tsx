"use client";

import { InterpretationBox } from "@/components/education/InterpretationBox";
import { StudyUnavailable } from "@/components/study/StudyUnavailable";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState, Skeleton } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useI18n } from "@/lib/i18n";
import { useStudyHoldout } from "@/lib/hooks";

/**
 * The frozen partition is UNAUDITED, so this panel is deliberately metric-free:
 * it reports the state of the holdout, never a reading of it. `provenance`,
 * `result` and `buy_and_hold` are part of the contract but are never rendered,
 * populated or not.
 */
export function HoldoutPanel() {
  const t = useI18n();
  const { data, error, isLoading } = useStudyHoldout();

  if (error) return <StudyUnavailable error={error} />;
  if (isLoading || !data) return <Skeleton className="h-72" />;

  // Absent status defaults to the locked state: the conservative reading, never
  // an implicit "open".
  const status = data.status ?? "HOLDOUT_LOCKED";
  const requirements = data.requirements ?? [];

  return (
    <Card>
      <CardHeader
        title={t.study.holdout.title}
        subtitle={t.study.holdout.subtitle}
        right={<StatusBadge status={status} />}
      />

      <InterpretationBox tone="warning" title={t.study.holdout.lockedTitle}>
        <p>{t.study.holdout.lockedBody}</p>
      </InterpretationBox>

      <dl className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="rounded-card border border-border bg-surface-2 px-4 py-3">
          <dt className="text-xs font-semibold uppercase tracking-wide text-accent">
            {t.study.holdout.period}
          </dt>
          <dd className="mt-1 text-sm text-fg">
            {data.period ? data.period : <StatusBadge status={null} />}
          </dd>
        </div>
        <div className="rounded-card border border-border bg-surface-2 px-4 py-3">
          <dt className="text-xs font-semibold uppercase tracking-wide text-accent">
            {t.study.holdout.reason}
          </dt>
          <dd className="mt-1 text-sm text-fg">
            {data.reason ? data.reason : <StatusBadge status={null} />}
          </dd>
        </div>
      </dl>

      <div className="mt-6">
        <CardHeader
          title={t.study.holdout.requirementsTitle}
          subtitle={t.study.holdout.requirementsSubtitle}
        />
        {requirements.length > 0 ? (
          <ul className="space-y-2">
            {requirements.map((requirement) => (
              <li
                key={requirement}
                className="flex items-start gap-3 rounded-md border border-border bg-surface-2 px-3 py-2 text-sm text-fg"
              >
                <span aria-hidden className="mt-0.5 text-xs text-muted">
                  {"\u25A1"}
                </span>
                <span>{requirement}</span>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState
            title={t.study.holdout.requirementsEmpty}
            hint={t.study.holdout.requirementsEmptyHint}
          />
        )}
      </div>

      <p className="mt-4 text-sm text-muted">{t.study.holdout.deliberateAbsence}</p>
    </Card>
  );
}
