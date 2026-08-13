"use client";

import { Card, CardHeader } from "@/components/ui/Card";
import { StatCard } from "@/components/ui/StatCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { StudySummaryResponse } from "@/lib/api-types";
import { fmtInt, fmtNumber, fmtTimestamp } from "@/lib/format";
import { es } from "@/lib/i18n/es";

/** The honest summary of the study, entirely read from the closure artifact. */
export function Headline({ summary }: { summary: StudySummaryResponse }) {
  const { study } = summary;
  const pbo = study.pbo?.pbo;
  const pboAvailable = pbo != null && Number.isFinite(pbo);

  return (
    <Card>
      <CardHeader
        title={es.study.headline.title}
        subtitle={es.study.headline.subtitle}
        right={
          <div className="text-right text-xs text-muted">
            <p>
              {es.study.headline.generatedAt}: {fmtTimestamp(summary.generated_at)}
            </p>
            {study.source_commit && (
              <p className="font-mono">
                {es.study.headline.commit}: {study.source_commit.slice(0, 12)}
              </p>
            )}
          </div>
        }
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label={es.study.headline.families}
          value={fmtInt(study.n_families)}
          sub={es.study.headline.familiesSub}
        />
        <StatCard
          label={es.study.headline.configurations}
          value={fmtInt(study.n_configurations_evaluated)}
          sub={es.study.headline.configurationsSub}
          metricKey="n_configurations_evaluated"
        />
        <StatCard
          label={es.study.headline.survivors}
          value={fmtInt(study.holm.n_rejected)}
          sub={es.study.headline.survivorsSub.replace("{alpha}", fmtNumber(study.alpha, 2))}
          metricKey="holm_adjusted_p"
        />
        <StatCard
          label={es.study.headline.pbo}
          value={pboAvailable ? fmtNumber(pbo, 3) : <StatusBadge status={null} />}
          sub={es.study.headline.pboSub}
          metricKey="pbo"
        />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label={es.study.headline.rowsLabel} value={fmtInt(summary.families.length)} />
        <StatCard label={es.study.headline.units} value={fmtInt(study.n_units)} />
        <StatCard
          label={es.study.table.symbol}
          value={`${summary.primary_symbol} · ${summary.secondary_symbol}`}
        />
        <StatCard
          label={es.study.headline.bestFamily}
          value={<span className="text-base">{study.best_family}</span>}
        />
      </div>

      <p className="mt-4 text-sm text-muted">{es.study.headline.bestFamilyNote}</p>
    </Card>
  );
}
