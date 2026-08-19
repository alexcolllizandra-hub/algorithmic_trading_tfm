"use client";

import { CriteriaBars } from "@/components/charts/CriteriaBars";
import { MonteCarloFan } from "@/components/charts/MonteCarloFan";
import { SeedEquityChart } from "@/components/charts/SeedEquityChart";
import { StudyUnavailable } from "@/components/study/StudyUnavailable";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState, Skeleton } from "@/components/ui/States";
import { StatCard } from "@/components/ui/StatCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { DataTable, type Column } from "@/components/ui/Table";
import { useI18n, type Dictionary } from "@/lib/i18n";
import type { StudyFamilySummary, StudySeedResult } from "@/lib/api-types";
import { fmtInt, fmtNumber, fmtPercent, fmtSignedPercent, signClass } from "@/lib/format";
import { useStudyFamily } from "@/lib/hooks";
import {
  crossAssetRows,
  seedReturnSpread,
  terminalDistribution,
  type TerminalRow,
} from "@/lib/study";

const seedColumns = (t: Dictionary): Column<StudySeedResult>[] => [
  {
    key: "seed",
    header: t.study.detail.seedColumn,
    render: (s) => <span className="font-mono text-xs">{fmtInt(s.seed)}</span>,
  },
  {
    key: "ret",
    header: t.study.table.totalReturn,
    align: "right",
    render: (s) => (
      <span className={signClass(s.total_return)}>{fmtSignedPercent(s.total_return)}</span>
    ),
  },
  {
    key: "sharpe",
    header: t.study.table.sharpe,
    align: "right",
    render: (s) => <span className={signClass(s.sharpe)}>{fmtNumber(s.sharpe, 2)}</span>,
  },
  {
    key: "dd",
    header: t.study.table.maxDrawdown,
    align: "right",
    render: (s) => (
      <span className={signClass(s.max_drawdown)}>{fmtSignedPercent(s.max_drawdown)}</span>
    ),
  },
  {
    key: "bars",
    header: t.study.detail.bars,
    align: "right",
    render: (s) => fmtInt(s.n_bars),
  },
];

const terminalColumns = (t: Dictionary): Column<TerminalRow>[] => [
  { key: "label", header: "", render: (r) => r.label },
  {
    key: "value",
    header: t.study.table.totalReturn,
    align: "right",
    render: (r) => <span className={signClass(r.value)}>{fmtSignedPercent(r.value)}</span>,
  },
];

export function FamilyDetail({
  familyKey,
  families,
}: {
  familyKey: string;
  families: StudyFamilySummary[];
}) {
  const t = useI18n();
  const { data: detail, error, isLoading } = useStudyFamily(familyKey);

  if (error) return <StudyUnavailable error={error} />;
  if (isLoading || !detail) return <Skeleton className="h-96" />;

  const spread = seedReturnSpread(detail);
  const siblings = crossAssetRows(families, detail.family);
  const mc = detail.monte_carlo;
  const terminal = mc.terminal;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title={`${detail.family} · ${detail.symbol}`}
          subtitle={t.study.detail.hypothesis}
          right={
            <div className="flex flex-wrap items-center gap-2">
              <Badge>{detail.gate}</Badge>
              <StatusBadge status={detail.verdict} />
            </div>
          }
        />
        <p className="text-base text-fg">{detail.thesis || t.common.noData}</p>
        {detail.gate_note && (
          <p className="mt-3 text-sm text-muted">
            <span className="uppercase tracking-wide">{t.study.detail.gateNote}:</span>{" "}
            {detail.gate_note}
          </p>
        )}

        <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
          <StatCard
            label={t.study.table.totalReturn}
            value={fmtSignedPercent(detail.total_return)}
            valueClassName={signClass(detail.total_return)}
            metricKey="total_return"
          />
          <StatCard
            label={t.study.table.sharpe}
            value={fmtNumber(detail.sharpe, 2)}
            valueClassName={signClass(detail.sharpe)}
            metricKey="sharpe"
          />
          <StatCard
            label={t.study.table.maxDrawdown}
            value={fmtSignedPercent(detail.max_drawdown)}
            valueClassName={signClass(detail.max_drawdown)}
            metricKey="max_drawdown"
          />
          <StatCard
            label={t.study.table.pValue}
            value={fmtNumber(detail.p_value, 4)}
            metricKey="p_value"
          />
          <StatCard
            label={t.study.table.holm}
            value={fmtNumber(detail.holm_adjusted_p, 3)}
            metricKey="holm_adjusted_p"
          />
          <StatCard
            label={t.study.detail.buyAndHold}
            value={fmtSignedPercent(detail.buy_and_hold_return)}
            valueClassName={signClass(detail.buy_and_hold_return)}
          />
        </div>
      </Card>

      <Card>
        <CardHeader
          title={t.study.detail.equityTitle}
          subtitle={t.study.detail.equitySubtitle}
          right={
            <span className="text-xs text-muted">
              {fmtInt(detail.n_seeds)} {t.study.table.seeds.toLowerCase()}
            </span>
          }
        />
        <SeedEquityChart detail={detail} />
        {spread && (
          <p className="mt-3 text-sm text-fg">
            {t.study.detail.seedSpread
              .replace("{min}", fmtSignedPercent(spread.min))
              .replace("{max}", fmtSignedPercent(spread.max))}
          </p>
        )}
        <div className="mt-4">
          <CardHeader title={t.study.detail.seedTableTitle} />
          {detail.seeds.length > 0 ? (
            <DataTable
              columns={seedColumns(t)}
              rows={[...detail.seeds].sort((a, b) => a.seed - b.seed)}
              rowKey={(s) => String(s.seed)}
              dense
            />
          ) : (
            <EmptyState title={t.common.noData} />
          )}
        </div>
      </Card>

      <Card>
        <CardHeader
          title={t.study.detail.fanTitle}
          subtitle={t.study.fan.method
            .replace("{method}", mc.method)
            .replace("{paths}", fmtInt(mc.n_paths))
            .replace("{block}", fmtNumber(mc.expected_block_bars, 1))
            .replace("{seed}", String(mc.seed))}
          right={
            <Badge tone="warn">
              {t.study.fan.measuresLabel}: {mc.measures}
            </Badge>
          }
        />
        <MonteCarloFan mc={mc} />
        <p className="mt-3 rounded-md border border-warn/40 bg-warn/10 px-3 py-2 text-xs text-warn">
          {t.study.fan.caption}
        </p>

        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div>
            <CardHeader title={t.study.fan.terminalTitle} />
            <DataTable
              columns={terminalColumns(t)}
              rows={[
                {
                  key: "observed",
                  label: t.study.fan.terminalObserved,
                  value: terminal.observed_total_return,
                },
                ...terminalDistribution(terminal),
              ]}
              rowKey={(r) => r.key}
              dense
            />
          </div>
          <div className="grid grid-cols-2 gap-4 self-start">
            <StatCard
              label={t.study.fan.probabilityPositive}
              value={fmtPercent(terminal.probability_positive, 1)}
            />
            <StatCard label={t.study.detail.bars} value={fmtInt(detail.n_bars)} />
          </div>
        </div>
      </Card>

      <Card>
        <CardHeader
          title={t.study.detail.criteriaTitle}
          subtitle={detail.criteria ? undefined : t.study.detail.criteriaEmpty}
        />
        {detail.criteria ? (
          <CriteriaBars
            criteria={detail.criteria}
            veto={detail.min_trades_veto}
            gloss={t.study.criteria.gloss}
          />
        ) : (
          <EmptyState title={t.common.noData} hint={t.study.detail.criteriaEmpty} />
        )}
      </Card>

      <Card>
        <CardHeader title={t.study.detail.crossAssetTitle} />
        {siblings.length > 1 ? (
          <>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {siblings.map((row) => (
                <div key={row.key} className="rounded-card border border-border bg-surface-2 p-4">
                  <p className="text-xs uppercase tracking-wide text-muted">{row.symbol}</p>
                  <p
                    className={`tabular mt-1 text-2xl font-semibold ${signClass(row.total_return)}`}
                  >
                    {fmtSignedPercent(row.total_return)}
                  </p>
                  <p className="tabular mt-1 text-xs text-muted">
                    {t.study.table.sharpe} {fmtNumber(row.sharpe, 2)} · {t.study.table.pValue}{" "}
                    {fmtNumber(row.p_value, 4)}
                  </p>
                </div>
              ))}
            </div>
            <p className="mt-3 text-sm text-muted">{t.study.detail.crossAssetNote}</p>
          </>
        ) : (
          <EmptyState title={t.study.detail.crossAssetSingle} />
        )}
      </Card>
    </div>
  );
}
