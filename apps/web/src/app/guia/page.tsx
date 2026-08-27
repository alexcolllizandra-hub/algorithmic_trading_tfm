"use client";

import { useState } from "react";

import { ConceptCards } from "@/components/guia/ConceptCards";
import { GuidePanel } from "@/components/guia/GuidePanel";
import { GuideToc } from "@/components/guia/GuideToc";
import type { StudyState } from "@/components/guia/GuideDataState";
import {
  BacktestPanel,
  DatosPanel,
  EstrategiaPanel,
  PreguntaPanel,
} from "@/components/guia/panels/IntroPanels";
import {
  CostesPanel,
  ParticionesPanel,
  PurgeEmbargoPanel,
  SemillasFoldsPanel,
  WalkForwardPanel,
} from "@/components/guia/panels/MethodPanels";
import {
  ConclusionPanel,
  EstrategiasProbadasPanel,
  RechazoPanel,
  ResultadosPanel,
} from "@/components/guia/panels/ResultPanels";
import { HowToRead } from "@/components/education/HowToRead";
import { SectionIntro } from "@/components/education/SectionIntro";
import { PageShell } from "@/components/layout/PageShell";
import { useI18n } from "@/lib/i18n";
import type { GuidePanelId } from "@/lib/guia";
import { useStudySummary } from "@/lib/hooks";

/**
 * Guided mode: the thesis in thirteen sequential panels, from the plainest
 * framing to the technical one.
 *
 * Every real figure comes from the study endpoints through the shared SWR
 * hooks; every drawing is invented and labelled "ejemplo ilustrativo". The
 * frozen holdout appears as a state only — panel 13 explains what it is and
 * reuses the locked treatment, and no holdout metric is rendered anywhere.
 */
function GuiaInner() {
  const { data: summary, error, isLoading } = useStudySummary();
  const [familyKey, setFamilyKey] = useState<string | null>(null);
  const state: StudyState = { summary, error, isLoading };

  const panels: { id: GuidePanelId; body: React.ReactNode }[] = [
    { id: "pregunta", body: <PreguntaPanel state={state} /> },
    { id: "datos", body: <DatosPanel state={state} /> },
    { id: "estrategia", body: <EstrategiaPanel state={state} /> },
    { id: "backtest", body: <BacktestPanel state={state} /> },
    { id: "particiones", body: <ParticionesPanel state={state} /> },
    { id: "walkForward", body: <WalkForwardPanel /> },
    { id: "purgeEmbargo", body: <PurgeEmbargoPanel /> },
    {
      id: "semillasFolds",
      body: (
        <SemillasFoldsPanel state={state} familyKey={familyKey} onSelectFamily={setFamilyKey} />
      ),
    },
    { id: "costes", body: <CostesPanel state={state} /> },
    { id: "estrategiasProbadas", body: <EstrategiasProbadasPanel state={state} /> },
    {
      id: "resultados",
      body: <ResultadosPanel state={state} familyKey={familyKey} onSelectFamily={setFamilyKey} />,
    },
    { id: "rechazo", body: <RechazoPanel state={state} /> },
    { id: "conclusion", body: <ConclusionPanel state={state} /> },
  ];

  return (
    <>
      <GuideToc />
      <div className="space-y-6">
        {panels.map((panel) => (
          <GuidePanel key={panel.id} id={panel.id}>
            {panel.body}
          </GuidePanel>
        ))}
      </div>
      <ConceptCards />
    </>
  );
}

export default function GuiaPage() {
  const t = useI18n();
  const s = t.sections.guia;
  return (
    <PageShell title={s.title}>
      <SectionIntro title={s.title} subtitle={s.subtitle} questions={s} />
      <GuiaInner />
      <HowToRead>
        <p>{s.comoInterpretarAnswer}</p>
        <p>{t.guia.illustrative.note}</p>
        <p>{t.study.holdout.deliberateAbsence}</p>
      </HowToRead>
    </PageShell>
  );
}
