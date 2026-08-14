import { GuideDataState, type StudyState } from "@/components/guia/GuideDataState";
import { Illustration } from "@/components/guia/Illustration";
import { Sparkline } from "@/components/guia/figures/Sparkline";
import { Timeline } from "@/components/guia/figures/Timeline";
import { InterpretationBox } from "@/components/education/InterpretationBox";
import { Badge } from "@/components/ui/Badge";
import { StatCard } from "@/components/ui/StatCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { fmtInt, fmtTimestamp } from "@/lib/format";
import {
  bestFamilyRow,
  developmentHoldoutRows,
  maxOutOfSampleBars,
  nextBarRows,
  strategyRuleSeries,
} from "@/lib/guia";
import { es } from "@/lib/i18n/es";

/** Bar count of the longest out-of-sample row, or a status when absent. */
function OosBarsCard({ state }: { state: StudyState }) {
  const bars = state.summary ? maxOutOfSampleBars(state.summary.families) : null;
  return (
    <StatCard
      label={es.guia.labels.oosBars}
      value={bars == null ? <StatusBadge status={null} /> : fmtInt(bars)}
    />
  );
}

export function PreguntaPanel({ state }: { state: StudyState }) {
  const { summary } = state;
  return (
    <div className="space-y-4">
      <InterpretationBox title={es.guia.labels.question}>
        <p className="text-base font-medium">{es.guia.labels.questionText}</p>
      </InterpretationBox>

      {summary ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <StatCard
            label={es.study.headline.families}
            value={fmtInt(summary.study.n_families)}
            sub={es.study.headline.familiesSub}
          />
          <StatCard
            label={es.study.headline.configurations}
            value={fmtInt(summary.study.n_configurations_evaluated)}
            sub={es.study.headline.configurationsSub}
            metricKey="n_configurations_evaluated"
          />
        </div>
      ) : (
        <GuideDataState error={state.error} isLoading={state.isLoading} />
      )}
    </div>
  );
}

export function DatosPanel({ state }: { state: StudyState }) {
  const { summary } = state;
  return (
    <div className="space-y-4">
      {summary ? (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label={es.guia.labels.assets}
              value={
                <span className="text-base">
                  {summary.primary_symbol} · {summary.secondary_symbol}
                </span>
              }
            />
            <StatCard label={es.guia.labels.timeframe} value={summary.timeframe} />
            <OosBarsCard state={state} />
            <StatCard
              label={es.guia.labels.holdoutState}
              value={
                <StatusBadge status={summary.holdout_opened ? "EXECUTED" : "HOLDOUT_LOCKED"} />
              }
            />
          </div>
          <p className="text-xs text-muted">
            {es.study.headline.generatedAt}: {fmtTimestamp(summary.generated_at)}
          </p>
        </>
      ) : (
        <GuideDataState error={state.error} isLoading={state.isLoading} />
      )}

      <Illustration
        title={es.guia.figures.developmentHoldout.title}
        caption={es.guia.figures.developmentHoldout.caption}
      >
        <Timeline
          rows={developmentHoldoutRows()}
          rowLabels={es.guia.figures.developmentHoldout.rows}
        />
      </Illustration>
    </div>
  );
}

export function EstrategiaPanel({ state }: { state: StudyState }) {
  const row = state.summary ? bestFamilyRow(state.summary) : null;
  return (
    <div className="space-y-4">
      {row ? (
        <div className="rounded-card border border-border bg-surface-2 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-accent">
            {es.guia.labels.exampleFamily}
          </p>
          <p className="mt-2 flex flex-wrap items-center gap-2 text-sm font-medium text-fg">
            <span>
              {row.family} · {row.symbol}
            </span>
            <Badge>{row.gate}</Badge>
          </p>
          <p className="mt-2 text-sm text-muted">{row.thesis || es.common.noData}</p>
        </div>
      ) : (
        <GuideDataState error={state.error} isLoading={state.isLoading} />
      )}

      <Illustration
        title={es.guia.figures.strategyRule.title}
        caption={es.guia.figures.strategyRule.caption}
      >
        <Sparkline series={strategyRuleSeries()} />
      </Illustration>
    </div>
  );
}

export function BacktestPanel({ state }: { state: StudyState }) {
  return (
    <div className="space-y-4">
      <Illustration title={es.guia.figures.nextBar.title} caption={es.guia.figures.nextBar.caption}>
        <Timeline rows={nextBarRows()} rowLabels={es.guia.figures.nextBar.rows} />
      </Illustration>

      {state.summary ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <OosBarsCard state={state} />
          <StatCard
            label={es.study.headline.units}
            value={fmtInt(state.summary.study.n_units)}
            sub={es.study.headline.rowsLabel}
          />
        </div>
      ) : (
        <GuideDataState error={state.error} isLoading={state.isLoading} />
      )}
    </div>
  );
}
