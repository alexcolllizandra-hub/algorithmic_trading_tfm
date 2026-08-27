"use client";

import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import useSWR from "swr";

import { PageShell } from "@/components/layout/PageShell";
import { SectionIntro } from "@/components/education/SectionIntro";
import { ExploratoryBanner } from "@/components/ui/ExploratoryBanner";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/States";
import { useI18n, type Dictionary } from "@/lib/i18n";
import { fmtInt, fmtNumber, fmtSignedPercent, signClass } from "@/lib/format";

/* ------------------------------------------------------------------------- *
 * Static-export types. Everything here mirrors what
 * scripts/export_strategy_explorer.py writes; there is no other source.
 * ------------------------------------------------------------------------- */

interface StudyHeadline {
  median_total_return: number | null;
  median_sharpe: number | null;
  median_max_drawdown: number | null;
  buy_and_hold_return: number | null;
}

interface StudyIndexEntry {
  family: string;
  round: string;
  verdict: string | null;
  thesis: string | null;
  file: string;
  assets: string[];
  n_seeds: number;
  headline: Record<string, StudyHeadline>;
}

interface StrategyIndex {
  generated_at: string;
  code_commit: string | null;
  engine: string;
  note: string;
  studies: StudyIndexEntry[];
}

interface SeedEntry {
  seed: number;
  metrics: Record<string, number | null>;
  curve: number[];
}

interface AssetBlock {
  oos_start: string;
  oos_end: string;
  n_bars: number;
  buy_and_hold: { total_return: number | null; sharpe: number | null; max_drawdown: number | null };
  seeds: SeedEntry[];
  average_curve: number[];
  average_metrics: Record<string, number>;
  closure: { thesis?: string | null; verdict?: string | null; p_value?: number | null } | null;
}

interface FamilyFile {
  family: string;
  round: string;
  per_asset: Record<string, AssetBlock>;
}

const loadJson = async (path: string) => {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${response.status} ${path}`);
  return response.json();
};

const METRIC_ORDER = [
  "total_return",
  "ann_return",
  "ann_volatility",
  "sharpe",
  "sortino",
  "calmar",
  "max_drawdown",
  "time_in_drawdown",
  "hit_rate",
  "n_trades",
  "exposure",
  "turnover",
  "var_95",
  "expected_shortfall_95",
  "skewness",
  "excess_kurtosis",
] as const;

const PERCENT_METRICS = new Set([
  "total_return",
  "ann_return",
  "max_drawdown",
  "time_in_drawdown",
  "hit_rate",
  "exposure",
]);

function verdictLabel(
  verdict: string | null,
  t: Dictionary
): { text: string; tone: "negative" | "warn" } {
  if (verdict === "EVALUATED_POST_CLOSURE_NOT_PROMOTABLE") {
    return { text: t.explorer.verdictNotPromotable, tone: "warn" };
  }
  return { text: t.explorer.verdictRejected, tone: "negative" };
}

function fmtMetric(key: string, value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  if (key === "n_trades" || key === "turnover") return fmtInt(value);
  if (PERCENT_METRICS.has(key)) return fmtSignedPercent(value, 1);
  return fmtNumber(value, 3);
}

/* ------------------------------------------------------------------------- */

function FamilyTable({
  studies,
  selected,
  onSelect,
}: {
  studies: StudyIndexEntry[];
  selected: string;
  onSelect: (family: string) => void;
}) {
  const t = useI18n();
  const rounds = useMemo(() => [...new Set(studies.map((s) => s.round))], [studies]);

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-muted">
            <th className="px-3 py-2 font-medium">{t.explorer.tableFamily}</th>
            <th className="px-3 py-2 font-medium">{t.explorer.tableRound}</th>
            <th className="px-3 py-2 text-right font-medium">{t.explorer.tableMedianReturn}</th>
            <th className="px-3 py-2 text-right font-medium">{t.explorer.tableMedianSharpe}</th>
            <th className="px-3 py-2 text-right font-medium">{t.explorer.tableBh}</th>
            <th className="px-3 py-2 text-right font-medium">{t.explorer.tableVerdict}</th>
          </tr>
        </thead>
        {rounds.map((round) => (
          <tbody key={round}>
            {studies
              .filter((s) => s.round === round)
              .map((s) => {
                const head = s.headline.BTCUSDT ?? Object.values(s.headline)[0];
                const verdict = verdictLabel(s.verdict, t);
                const active = s.family === selected;
                return (
                  <tr
                    key={s.family}
                    onClick={() => onSelect(s.family)}
                    className={`cursor-pointer border-b border-border/50 transition-colors last:border-0 ${
                      active ? "bg-accent/10" : "hover:bg-surface-2"
                    }`}
                  >
                    <td className="px-3 py-2 font-medium">{s.family}</td>
                    <td className="px-3 py-2 text-muted">{s.round}</td>
                    <td
                      className={`px-3 py-2 text-right tabular-nums ${signClass(
                        head?.median_total_return ?? null
                      )}`}
                    >
                      {fmtMetric("total_return", head?.median_total_return)}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-muted">
                      {fmtNumber(head?.median_sharpe ?? null, 2)}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-muted">
                      {fmtMetric("total_return", head?.buy_and_hold_return)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <Badge tone={verdict.tone}>{verdict.text}</Badge>
                    </td>
                  </tr>
                );
              })}
          </tbody>
        ))}
      </table>
    </div>
  );
}

function EquityChart({ asset, seed }: { asset: AssetBlock; seed: number | "average" }) {
  const t = useI18n();

  const data = useMemo(() => {
    const average = asset.average_curve;
    const selected =
      seed === "average" ? null : (asset.seeds.find((s) => s.seed === seed)?.curve ?? null);
    const length = average.length;
    const barsPerPoint = asset.n_bars / Math.max(length - 1, 1);
    return average.map((value, i) => ({
      bar: Math.round(i * barsPerPoint),
      average: value,
      selected: selected?.[i] ?? null,
    }));
  }, [asset, seed]);

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
        <XAxis
          dataKey="bar"
          tick={{ fontSize: 11 }}
          stroke="var(--muted)"
          tickFormatter={(v) => fmtInt(v)}
        />
        <YAxis
          tick={{ fontSize: 11 }}
          stroke="var(--muted)"
          width={52}
          tickFormatter={(v) => fmtNumber(v, 2)}
          domain={["auto", "auto"]}
        />
        <Tooltip
          formatter={(value: number, name: string) => [
            fmtNumber(value, 4),
            name === "average" ? t.explorer.averageSeeds : `${t.explorer.pickSeed} ${seed}`,
          ]}
          labelFormatter={(label) => `bar ${fmtInt(Number(label))}`}
        />
        <ReferenceLine y={1} stroke="var(--muted)" strokeDasharray="4 3" />
        <Line
          type="monotone"
          dataKey="average"
          stroke="var(--accent)"
          strokeWidth={2.4}
          dot={false}
          isAnimationActive={false}
        />
        {seed !== "average" && (
          <Line
            type="monotone"
            dataKey="selected"
            stroke="#D55E00"
            strokeWidth={1.4}
            dot={false}
            isAnimationActive={false}
          />
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}

function FamilyDetailBlock({ entry }: { entry: StudyIndexEntry }) {
  const t = useI18n();
  const { data, error } = useSWR<FamilyFile>(entry.file, loadJson);
  const [assetKey, setAssetKey] = useState<string>("BTCUSDT");
  const [seed, setSeed] = useState<number | "average">("average");

  if (error) return <ErrorState title={t.explorer.loadError} />;
  if (!data) return <Skeleton className="h-96" />;

  const asset = data.per_asset[assetKey] ?? Object.values(data.per_asset)[0];
  const verdict = verdictLabel(entry.verdict, t);
  const metricsSource =
    seed === "average"
      ? asset.average_metrics
      : (asset.seeds.find((s) => s.seed === seed)?.metrics ?? {});

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h3 className="text-xl font-semibold tracking-tight">{entry.family}</h3>
            <p className="mt-1 text-sm text-muted">
              {t.explorer.round} {entry.round} · {entry.n_seeds} seeds
            </p>
          </div>
          <Badge tone={verdict.tone}>{verdict.text}</Badge>
        </div>
        <p className="mt-4 text-sm leading-relaxed text-muted">
          <span className="mr-2 font-medium text-fg">{t.explorer.thesis}:</span>
          {entry.thesis ?? t.explorer.thesisMissing}
        </p>
      </Card>

      <Card>
        <CardHeader
          title={t.explorer.equityTitle}
          subtitle={t.explorer.equitySubtitle
            .replace("{start}", asset.oos_start.slice(0, 10))
            .replace("{end}", asset.oos_end.slice(0, 10))
            .replace("{bars}", fmtInt(asset.n_bars))
            .replace("{engine}", "random_search")}
        />
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1 rounded-md border border-border p-0.5">
            {entry.assets.map((sym) => (
              <button
                key={sym}
                type="button"
                onClick={() => setAssetKey(sym)}
                aria-pressed={assetKey === sym}
                className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                  assetKey === sym
                    ? "bg-accent text-accent-fg"
                    : "text-muted hover:bg-surface-2 hover:text-fg"
                }`}
              >
                {sym.replace("USDT", "")}
              </button>
            ))}
          </div>
          <label className="flex items-center gap-2 text-xs text-muted">
            {t.explorer.pickSeed}
            <select
              value={String(seed)}
              onChange={(event) =>
                setSeed(event.target.value === "average" ? "average" : Number(event.target.value))
              }
              className="rounded-md border border-border bg-surface px-2 py-1 text-xs text-fg"
            >
              <option value="average">{t.explorer.averageSeeds}</option>
              {asset.seeds.map((s) => (
                <option key={s.seed} value={s.seed}>
                  {s.seed}
                </option>
              ))}
            </select>
          </label>
          <span className="text-xs text-muted">
            {t.explorer.buyAndHold}:{" "}
            <span className={signClass(asset.buy_and_hold.total_return)}>
              {fmtMetric("total_return", asset.buy_and_hold.total_return)}
            </span>
          </span>
        </div>
        <EquityChart asset={asset} seed={seed} />
      </Card>

      <Card>
        <CardHeader title={t.explorer.metricsTitle} subtitle={t.explorer.metricsSubtitle} />
        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3 lg:grid-cols-4">
          {METRIC_ORDER.map((key) => (
            <div key={key} className="rounded-md border border-border/60 bg-surface-2/50 px-3 py-2">
              <dt className="text-[11px] uppercase tracking-wide text-muted">
                {t.explorer.metric[key]}
              </dt>
              <dd
                className={`mt-1 text-sm font-medium tabular-nums ${
                  key === "total_return" || key === "ann_return"
                    ? signClass((metricsSource as Record<string, number | null>)[key] ?? null)
                    : "text-fg"
                }`}
              >
                {fmtMetric(key, (metricsSource as Record<string, number | null>)[key])}
              </dd>
            </div>
          ))}
        </dl>
      </Card>
    </div>
  );
}

export default function EstrategiasPage() {
  const t = useI18n();
  const { data, error, isLoading } = useSWR<StrategyIndex>("/data/strategies/index.json", loadJson);
  const [family, setFamily] = useState<string | null>(null);

  const selected = data?.studies.find((s) => s.family === family) ?? data?.studies[0] ?? null;

  return (
    <PageShell title={t.explorer.title}>
      <SectionIntro
        title={t.explorer.title}
        subtitle={t.explorer.subtitle}
        questions={{
          que: t.explorer.que,
          queAnswer: t.explorer.queAnswer,
          porQue: t.explorer.porQue,
          porQueAnswer: t.explorer.porQueAnswer,
          comoInterpretar: t.explorer.comoInterpretar,
          comoInterpretarAnswer: t.explorer.comoInterpretarAnswer,
          queConcluir: t.explorer.queConcluir,
          queConcluirAnswer: t.explorer.queConcluirAnswer,
        }}
      />

      <ExploratoryBanner message={t.explorer.banner} />

      {isLoading && <Skeleton className="h-64" />}
      {error && <ErrorState title={t.explorer.loadError} />}
      {data && data.studies.length === 0 && <EmptyState title={t.common.noData} />}

      {data && selected && (
        <div className="space-y-6">
          <Card>
            <CardHeader title={t.explorer.pickFamily} subtitle={data.note} />
            <FamilyTable studies={data.studies} selected={selected.family} onSelect={setFamily} />
          </Card>
          <FamilyDetailBlock key={selected.family} entry={selected} />
        </div>
      )}
    </PageShell>
  );
}
