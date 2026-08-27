"use client";

import { Card, CardHeader } from "@/components/ui/Card";
import { StatCard } from "@/components/ui/StatCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useI18n } from "@/lib/i18n";
import type { StudySummaryResponse } from "@/lib/api-types";
import { fmtInt, fmtNumber, fmtTimestamp } from "@/lib/format";

/** The honest summary of the study, entirely read from the closure artifact. */
export function Headline({ summary }: { summary: StudySummaryResponse }) {
  const t = useI18n();
  const { study } = summary;
  const pbo = study.pbo?.pbo;
  const pboAvailable = pbo != null && Number.isFinite(pbo);

  return (
    <Card>
      <CardHeader
        title={t.study.headline.title}
        subtitle={t.study.headline.subtitle}
        right={
          <div className="text-right text-xs text-muted">
            <p>
              {t.study.headline.generatedAt}: {fmtTimestamp(summary.generated_at)}
            </p>
            {study.source_commit && (
              <p className="font-mono">
                {t.study.headline.commit}: {study.source_commit.slice(0, 12)}
              </p>
            )}
          </div>
        }
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label={t.study.headline.families}
          value={fmtInt(study.n_families)}
          sub={t.study.headline.familiesSub}
        />
        <StatCard
          label={t.study.headline.configurations}
          value={fmtInt(study.n_configurations_evaluated)}
          sub={t.study.headline.configurationsSub}
          metricKey="n_configurations_evaluated"
        />
        <StatCard
          label={t.study.headline.survivors}
          value={fmtInt(study.holm.n_rejected)}
          sub={t.study.headline.survivorsSub.replace("{alpha}", fmtNumber(study.alpha, 2))}
          metricKey="holm_adjusted_p"
        />
        <StatCard
          label={t.study.headline.pbo}
          value={pboAvailable ? fmtNumber(pbo, 3) : <StatusBadge status={null} />}
          sub={t.study.headline.pboSub}
          metricKey="pbo"
        />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label={t.study.headline.rowsLabel} value={fmtInt(summary.families.length)} />
        <StatCard label={t.study.headline.units} value={fmtInt(study.n_units)} />
        <StatCard
          label={t.study.table.symbol}
          value={`${summary.primary_symbol} · ${summary.secondary_symbol}`}
        />
        <StatCard
          label={t.study.headline.bestFamily}
          value={<span className="text-base">{study.best_family}</span>}
        />
      </div>

      <p className="mt-4 text-sm text-muted">{t.study.headline.bestFamilyNote}</p>
    </Card>
  );
}
