import { Illustration } from "@/components/guia/Illustration";
import { Bars } from "@/components/guia/figures/Bars";
import { PDots } from "@/components/guia/figures/PDots";
import { Sparkline } from "@/components/guia/figures/Sparkline";
import { Timeline } from "@/components/guia/figures/Timeline";
import { InterpretationBox } from "@/components/education/InterpretationBox";
import { Card, CardHeader } from "@/components/ui/Card";
import {
  bhFigure,
  curveFittingSeries,
  dataMiningFigure,
  deflatedBars,
  fineTuningRows,
  holmFigure,
  hyperparameterBars,
  leakageRows,
  multipleTestingFigure,
  overfittingSeries,
  pboBars,
  pHackingFigure,
  selectionBiasBars,
  snoopingRows,
} from "@/lib/guia";
import { useI18n, type Dictionary } from "@/lib/i18n";
import { es } from "@/lib/i18n/es";

type ConceptId = keyof typeof es.guia.concepts.items;
type FigureId = keyof typeof es.guia.figures;

interface ConceptSpec {
  id: ConceptId;
  figureId: FigureId;
  figure: React.ReactNode;
}

const buildConcepts = (t: Dictionary): ConceptSpec[] => [
  { id: "mineria", figureId: "dataMining", figure: <PDots figure={dataMiningFigure()} /> },
  {
    id: "snooping",
    figureId: "snooping",
    figure: <Timeline rows={snoopingRows()} rowLabels={t.guia.figures.snooping.rows} />,
  },
  { id: "curva", figureId: "curveFitting", figure: <Sparkline series={curveFittingSeries()} /> },
  { id: "hiper", figureId: "hyperparameter", figure: <Bars bars={hyperparameterBars()} /> },
  {
    id: "fineTuning",
    figureId: "fineTuning",
    figure: <Timeline rows={fineTuningRows()} rowLabels={t.guia.figures.fineTuning.rows} />,
  },
  {
    id: "sobreajuste",
    figureId: "overfitting",
    figure: <Sparkline series={overfittingSeries()} />,
  },
  {
    id: "multiples",
    figureId: "multipleTesting",
    figure: <PDots figure={multipleTestingFigure()} />,
  },
  { id: "seleccion", figureId: "selectionBias", figure: <Bars bars={selectionBiasBars()} /> },
  { id: "pHacking", figureId: "pHacking", figure: <PDots figure={pHackingFigure()} /> },
  {
    id: "leakage",
    figureId: "leakage",
    figure: <Timeline rows={leakageRows()} rowLabels={t.guia.figures.leakage.rows} />,
  },
  { id: "pbo", figureId: "pbo", figure: <Bars bars={pboBars()} /> },
  { id: "deflated", figureId: "deflated", figure: <Bars bars={deflatedBars()} /> },
  { id: "holm", figureId: "holm", figure: <PDots figure={holmFigure()} /> },
  { id: "bh", figureId: "bh", figure: <PDots figure={bhFigure()} /> },
];

/**
 * The vocabulary of the thesis, one card per concept, each with a labelled
 * didactic drawing. The fine-tuning clarification sits above the grid because
 * the two ideas it separates are the ones readers conflate most often.
 */
export function ConceptCards() {
  const t = useI18n();
  const concepts = buildConcepts(t);
  return (
    <Card>
      <CardHeader title={t.guia.concepts.title} subtitle={t.guia.concepts.subtitle} />

      <InterpretationBox tone="warning" title={t.guia.concepts.fineTuningTitle}>
        <p>{t.guia.concepts.fineTuningBody}</p>
        <p className="mt-2">{t.guia.concepts.fineTuningBody2}</p>
      </InterpretationBox>

      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
        {concepts.map((spec) => {
          const concept = t.guia.concepts.items[spec.id];
          const figure = t.guia.figures[spec.figureId];
          return (
            <article
              key={spec.id}
              className="rounded-card border border-border bg-surface-2 p-4"
              data-guide-concept={spec.id}
            >
              <h3 className="text-sm font-semibold text-fg">{concept.term}</h3>
              <dl className="mt-2 space-y-2">
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-accent">
                    {t.guia.concepts.whatIs}
                  </dt>
                  <dd className="mt-1 text-sm text-muted">{concept.plain}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-accent">
                    {t.guia.concepts.whyMatters}
                  </dt>
                  <dd className="mt-1 text-sm text-muted">{concept.matters}</dd>
                </div>
              </dl>
              <div className="mt-3">
                <Illustration title={figure.title} caption={figure.caption}>
                  {spec.figure}
                </Illustration>
              </div>
            </article>
          );
        })}
      </div>
    </Card>
  );
}
