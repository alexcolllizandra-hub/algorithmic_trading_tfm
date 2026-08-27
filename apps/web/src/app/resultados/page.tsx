"use client";

// Results & study closure, merged (phase 3 of the panel restructure): the
// former /estudio content now lives here as the single results thread —
// families → master table → corrections → regimes → holdout. The old
// per-run fold browser moved into /experimentos (RunPerformanceSection),
// and /estudio redirects here.

import { useState } from "react";

import { HowToRead } from "@/components/education/HowToRead";
import { SectionIntro } from "@/components/education/SectionIntro";
import { PageShell } from "@/components/layout/PageShell";
import { CorrectionsPanel } from "@/components/study/CorrectionsPanel";
import { FamilyDetail } from "@/components/study/FamilyDetail";
import { Headline } from "@/components/study/Headline";
import { HoldoutPanel } from "@/components/study/HoldoutPanel";
import { MasterTable } from "@/components/study/MasterTable";
import { RegimePanel } from "@/components/study/RegimePanel";
import { StudyUnavailable } from "@/components/study/StudyUnavailable";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState, Skeleton } from "@/components/ui/States";
import { useI18n } from "@/lib/i18n";
import { useStudySummary } from "@/lib/hooks";

function ResultadosInner() {
  const t = useI18n();
  const { data: summary, error, isLoading } = useStudySummary();
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  if (error) return <StudyUnavailable error={error} />;
  if (isLoading || !summary) return <Skeleton className="h-96" />;

  return (
    <div className="space-y-6">
      <Headline summary={summary} />

      <MasterTable
        families={summary.families}
        selectedKey={selectedKey}
        onSelect={setSelectedKey}
      />

      {selectedKey ? (
        <FamilyDetail familyKey={selectedKey} families={summary.families} />
      ) : (
        <Card>
          <CardHeader title={t.study.detail.hypothesis} />
          <EmptyState title={t.study.detail.empty} />
        </Card>
      )}

      <CorrectionsPanel study={summary.study} />
      <RegimePanel />
      <HoldoutPanel />
    </div>
  );
}

export default function ResultadosPage() {
  const t = useI18n();
  const s = t.sections.estudio;
  return (
    <PageShell title={s.title}>
      <SectionIntro title={s.title} subtitle={s.subtitle} questions={s} />
      <ResultadosInner />
      <HowToRead>
        <p>{s.porQueAnswer}</p>
        <p>{t.study.fan.caption}</p>
        <p>{t.study.corrections.pboCaption}</p>
        <p>{t.study.holdout.deliberateAbsence}</p>
      </HowToRead>
    </PageShell>
  );
}
