"use client";

// Panel home, static-first (phase 1 of the restructure): the study's verdict,
// phase flow, key numbers and section shortcuts all come from committed
// static exports and render with no API. The live block appears only when
// the local API actually responds; when it is down the page shows a one-line
// hint instead of an error state.

import Link from "next/link";

import { HowToRead } from "@/components/education/HowToRead";
import { InterpretationBox } from "@/components/education/InterpretationBox";
import { SectionIntro } from "@/components/education/SectionIntro";
import { PageShell } from "@/components/layout/PageShell";
import { navGroups } from "@/components/layout/nav";
import { useLandingExtra } from "@/components/landing/charts/extra";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { ExploratoryBanner } from "@/components/ui/ExploratoryBanner";
import { StatCard } from "@/components/ui/StatCard";
import { useEvidence } from "@/lib/evidence";
import { fmtInt } from "@/lib/format";
import { useI18n, useIntlLocale, type Dictionary } from "@/lib/i18n";
import { useHealth, useResearchSummary } from "@/lib/hooks";

const PHASES = (t: Dictionary) => Object.values(t.phases);

function VerdictCard() {
  const t = useI18n();
  const { data } = useEvidence();
  if (!data) return null;
  const study = data.study;

  const tiles = [
    { v: String(study.n_families), l: t.panelHome.families },
    { v: String(study.holm_rejected), l: t.panelHome.survive, accent: true },
    {
      v: study.smallest_raw_p.toFixed(2),
      l: t.panelHome.pValue.replace("{alpha}", String(study.alpha)),
    },
    { v: study.pbo.toFixed(3), l: t.panelHome.pbo },
  ];

  return (
    <Card>
      <CardHeader title={t.panelHome.verdictTitle} subtitle={t.panelHome.verdictSubtitle} />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {tiles.map((tile) => (
          <div
            key={tile.l}
            className={`rounded-md border p-4 ${
              tile.accent ? "border-accent/40 bg-accent/5" : "border-border bg-surface-2"
            }`}
          >
            <p
              className={`tabular text-2xl font-semibold tracking-tight ${
                tile.accent ? "text-accent" : ""
              }`}
            >
              {tile.v}
            </p>
            <p className="mt-1 text-xs leading-snug text-muted">{tile.l}</p>
          </div>
        ))}
      </div>
      <div className="mt-4">
        <Link href="/resultados" className="text-sm text-accent hover:underline">
          {t.panelHome.verdictLink}
        </Link>
      </div>
    </Card>
  );
}

function StaticNumbers() {
  const t = useI18n();
  const intl = useIntlLocale();
  const { data: extra } = useLandingExtra();
  if (!extra?.totals) return null;

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
      <StatCard label={t.panelHome.statBars} value={extra.totals.bars_total.toLocaleString(intl)} />
      <StatCard label={t.panelHome.statRuns} value={extra.totals.runs_total.toLocaleString(intl)} />
      <StatCard label={t.panelHome.statFamilies} value={String(extra.totals.families_registered)} />
      <StatCard
        label={t.panelHome.statRotations}
        value={extra.null_distribution.n_rotations.toLocaleString(intl)}
      />
    </div>
  );
}

function QuickLinks() {
  const t = useI18n();
  const groups = navGroups(t).filter((group) => group.key === "study" || group.key === "explore");
  const items = groups.flatMap((group) => group.items);

  return (
    <Card>
      <CardHeader title={t.panelHome.quickTitle} subtitle={t.panelHome.quickSubtitle} />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="flex gap-3 rounded-md border border-border bg-surface-2 px-4 py-3 transition-colors hover:border-accent/40"
          >
            <span className="text-lg text-accent" aria-hidden>
              {item.icon}
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-medium">{item.label}</span>
              <span className="block truncate text-xs text-muted">{item.description}</span>
            </span>
          </Link>
        ))}
      </div>
    </Card>
  );
}

/** Rendered only when the local API answers; otherwise a one-line hint. */
function LiveBlock() {
  const t = useI18n();
  const { data: summary, error } = useResearchSummary();
  const { data: health } = useHealth();

  if (error || !summary) {
    return <p className="font-mono text-xs leading-relaxed text-muted">{t.panelHome.apiHint}</p>;
  }

  return (
    <Card>
      <CardHeader
        title={t.panelHome.liveTitle}
        subtitle={t.panelHome.liveSubtitle}
        right={
          <Badge tone={health?.status === "ok" ? "positive" : "neutral"}>
            {health?.status ?? "—"}
          </Badge>
        }
      />
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label={t.panelHome.liveRunsTotal} value={fmtInt(summary.runs_total)} />
        <StatCard label={t.panelHome.liveRunsDev} value={fmtInt(summary.runs_development)} />
        <StatCard
          label={t.panelHome.liveRunsSynthetic}
          value={fmtInt(summary.runs_synthetic)}
          sub={t.panelHome.liveRunsSyntheticSub}
        />
        <StatCard
          label={t.panelHome.liveHoldout}
          value={summary.holdout_start?.slice(0, 10) ?? "—"}
          sub={t.panelHome.liveHoldoutSub}
        />
      </div>

      {summary.pilot_run_id && (
        <div className="mt-6 rounded-md border border-border bg-surface-2 p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-semibold">{t.panelHome.pilotTitle}</p>
            <Badge tone="accent">{summary.pilot_run_id}</Badge>
          </div>
          <dl className="grid grid-cols-2 gap-3 text-sm md:grid-cols-6">
            <div>
              <dt className="text-muted">{t.panelHome.pilotSymbol}</dt>
              <dd>
                {summary.pilot_symbol} {summary.pilot_timeframe}
              </dd>
            </div>
            <div className="col-span-2">
              <dt className="text-muted">{t.panelHome.pilotInterval}</dt>
              <dd className="font-mono text-xs">{summary.pilot_interval ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-muted">{t.panelHome.pilotBudget}</dt>
              <dd className="tabular">{fmtInt(summary.pilot_budget)}</dd>
            </div>
            <div>
              <dt className="text-muted">{t.panelHome.pilotFolds}</dt>
              <dd className="tabular">{fmtInt(summary.pilot_folds)}</dd>
            </div>
            <div>
              <dt className="text-muted">{t.panelHome.pilotSeed}</dt>
              <dd className="tabular">{fmtInt(summary.pilot_seed)}</dd>
            </div>
          </dl>
          <div className="mt-3">
            <Link
              href={`/experimentos?run=${encodeURIComponent(summary.pilot_run_id)}`}
              className="text-sm text-accent hover:underline"
            >
              {t.panelHome.pilotLink}
            </Link>
          </div>
        </div>
      )}
    </Card>
  );
}

export default function OverviewPage() {
  const t = useI18n();
  const s = t.sections.overview;

  return (
    <PageShell title={s.title}>
      <SectionIntro title={s.title} subtitle={s.subtitle} questions={s} />

      <ExploratoryBanner message={t.warnings.exploratory} />

      <VerdictCard />

      <Card>
        <CardHeader title={t.timeline.title} subtitle={t.sections.overview.comoInterpretar} />
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

      <StaticNumbers />

      <QuickLinks />

      <InterpretationBox tone="warning" title="Holdout">
        {t.warnings.holdoutLocked}
      </InterpretationBox>

      <LiveBlock />

      <InterpretationBox tone="info">
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
