"use client";

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
import { es } from "@/lib/i18n/es";
import { useStudySummary } from "@/lib/hooks";

function EstudioInner() {
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
          <CardHeader title={es.study.detail.hypothesis} />
          <EmptyState title={es.study.detail.empty} />
        </Card>
      )}

      <CorrectionsPanel study={summary.study} />
      <RegimePanel />
      <HoldoutPanel />
    </div>
  );
}

export default function EstudioPage() {
  const s = es.sections.estudio;
  return (
    <PageShell title={s.title}>
      <SectionIntro title={s.title} subtitle={s.subtitle} questions={s} />
      <EstudioInner />
      <HowToRead>
        <p>{s.porQueAnswer}</p>
        <p>{es.study.fan.caption}</p>
        <p>{es.study.corrections.pboCaption}</p>
        <p>{es.study.holdout.deliberateAbsence}</p>
      </HowToRead>
    </PageShell>
  );
}
