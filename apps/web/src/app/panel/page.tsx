"use client";

import Link from "next/link";

import { HowToRead } from "@/components/education/HowToRead";
import { InterpretationBox } from "@/components/education/InterpretationBox";
import { SectionIntro } from "@/components/education/SectionIntro";
import { PageShell } from "@/components/layout/PageShell";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { ExploratoryBanner } from "@/components/ui/ExploratoryBanner";
import { ErrorState, SkeletonCard } from "@/components/ui/States";
import { StatCard } from "@/components/ui/StatCard";
import { useI18n, type Dictionary } from "@/lib/i18n";
import { fmtInt, fmtPercent } from "@/lib/format";
import { useHealth, useMarketCoverage, useResearchSummary } from "@/lib/hooks";

const PHASES = (t: Dictionary) => Object.values(t.phases);

export default function OverviewPage() {
  const t = useI18n();
  const { data: summary, error: summaryError, isLoading } = useResearchSummary();
  const { data: health } = useHealth();
  const { data: coverage } = useMarketCoverage();

  const s = t.sections.overview;

  return (
    <PageShell title={s.title}>
      <SectionIntro title={s.title} subtitle={s.subtitle} questions={s} />

      <ExploratoryBanner message={t.warnings.exploratory} />

      <InterpretationBox tone="warning" title="Holdout">
        {t.warnings.holdoutLocked}
      </InterpretationBox>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {isLoading ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : summaryError ? (
          <div className="col-span-full">
            <ErrorState title="No se pudo cargar el resumen" detail={summaryError.message} />
          </div>
        ) : (
          <>
            <StatCard label="Runs totales" value={fmtInt(summary?.runs_total)} />
            <StatCard label="Runs desarrollo" value={fmtInt(summary?.runs_development)} />
            <StatCard
              label="Runs sintéticos"
              value={fmtInt(summary?.runs_synthetic)}
              sub="no son resultados"
            />
            <StatCard
              label="Holdout"
              value={summary?.holdout_start?.slice(0, 10) ?? "—"}
              sub="partición bloqueada"
            />
          </>
        )}
      </div>

      <Card>
        <CardHeader
          title="Flujo de fases de investigación"
          subtitle="Estado metodológico del pipeline"
        />
        <ol className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
          {PHASES(t).map((phase, i) => (
            <li
              key={phase.id}
              className="flex gap-3 rounded-md border border-border bg-surface-2 px-4 py-3"
            >
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent/15 text-xs font-semibold text-accent">
                {i + 1}
              </span>
              <div>
                <div className="text-sm font-medium">{phase.label}</div>
                <div className="text-xs text-muted">{phase.short}</div>
              </div>
            </li>
          ))}
        </ol>
      </Card>

      {summary?.pilot_run_id && (
        <Card>
          <CardHeader
            title="Run piloto de referencia"
            right={<Badge tone="accent">{summary.pilot_run_id}</Badge>}
          />
          <dl className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
            <div>
              <dt className="text-muted">Símbolo</dt>
              <dd>
                {summary.pilot_symbol} {summary.pilot_timeframe}
              </dd>
            </div>
            <div>
              <dt className="text-muted">Intervalo</dt>
              <dd className="font-mono text-xs">{summary.pilot_interval ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-muted">Budget</dt>
              <dd className="tabular">{fmtInt(summary.pilot_budget)}</dd>
            </div>
            <div>
              <dt className="text-muted">Folds</dt>
              <dd className="tabular">{fmtInt(summary.pilot_folds)}</dd>
            </div>
            <div>
              <dt className="text-muted">Fracción dev</dt>
              <dd className="tabular">
                {summary.pilot_fraction_of_dev_days != null
                  ? fmtPercent(summary.pilot_fraction_of_dev_days)
                  : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-muted">Seed</dt>
              <dd className="tabular">{fmtInt(summary.pilot_seed)}</dd>
            </div>
          </dl>
          <div className="mt-4">
            <Link
              href={`/experimentos?run=${encodeURIComponent(summary.pilot_run_id)}`}
              className="text-sm text-accent hover:underline"
            >
              Ver experimento piloto →
            </Link>
          </div>
        </Card>
      )}

      <Card>
        <CardHeader title="Evidencia disponible" />
        <ul className="grid grid-cols-1 gap-2 text-sm md:grid-cols-2">
          <li className="flex items-center justify-between rounded-md border border-border px-3 py-2">
            <span>Artefactos indexados</span>
            <Badge tone={summary?.artifact_root_exists ? "positive" : "warn"}>
              {summary?.artifact_root_exists ? "presente" : "ausente"}
            </Badge>
          </li>
          <li className="flex items-center justify-between rounded-md border border-border px-3 py-2">
            <span>API cuantitativa</span>
            <Badge tone={health?.status === "ok" ? "positive" : "negative"}>
              {health?.status ?? "—"}
            </Badge>
          </li>
          <li className="flex items-center justify-between rounded-md border border-border px-3 py-2">
            <span>Datasets reales</span>
            <Badge tone="positive">
              {fmtInt(
                coverage?.datasets.filter((d) => d.classification === "REAL_HISTORICAL").length ?? 0
              )}
            </Badge>
          </li>
          <li className="flex items-center justify-between rounded-md border border-border px-3 py-2">
            <span>Dev termina en</span>
            <span className="font-mono text-xs">
              {coverage?.development_end_max?.slice(0, 10) ?? "—"}
            </span>
          </li>
        </ul>
      </Card>

      <InterpretationBox tone="info" title="Conclusión provisional">
        {t.warnings.provisionalConclusion} {t.warnings.noHoldoutRuns}
      </InterpretationBox>

      <HowToRead>
        <p>{t.glossary.holdout.definition}</p>
        <p>{t.glossary.walkForward.definition}</p>
        <p>{t.glossary.fairBudget.definition}</p>
      </HowToRead>
    </PageShell>
  );
}
