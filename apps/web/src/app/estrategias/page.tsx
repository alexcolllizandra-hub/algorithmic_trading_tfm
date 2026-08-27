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

interface FoldWinner {
  fold: number | null;
  params: Record<string, unknown>;
  val_sharpe: number | null;
  test_sharpe: number | null;
  test_return: number | null;
  n_trades: number | null;
}

interface SeedEntry {
  seed: number;
  metrics: Record<string, number | null>;
  curve: number[];
  fold_winners?: FoldWinner[];
}

interface MonteCarloBlock {
  method: string;
  block_bars: number;
  n_paths: number;
  seed: number;
  source_seed: number;
  observed_total_return: number;
  observed_percentile: number;
  probability_positive: number;
  terminal_quantiles: Record<string, number>;
}

interface AssetBlock {
  oos_start: string;
  oos_end: string;
  n_bars: number;
  buy_and_hold: {
    total_return: number | null;
    sharpe: number | null;
    max_drawdown: number | null;
    curve?: number[];
  };
  curve_times?: string[];
  seeds: SeedEntry[];
  average_curve: number[];
  average_metrics: Record<string, number>;
  monte_carlo?: MonteCarloBlock;
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

// CSS variables in globals.css hold raw RGB triplets meant for rgb(var(--x));
// passing var(--x) straight to an SVG stroke yields an invalid color and an
// invisible line, so every chart color goes through rgb() here.
const CHART = {
  grid: "rgb(var(--border))",
  axis: "rgb(var(--muted))",
  average: "rgb(var(--accent))",
  seed: "#D55E00",
  benchmark: "rgb(var(--muted))",
};

function EquityChart({ asset, seed }: { asset: AssetBlock; seed: number | "average" }) {
  const t = useI18n();

  const data = useMemo(() => {
    const average = asset.average_curve;
    const selected =
      seed === "average" ? null : (asset.seeds.find((s) => s.seed === seed)?.curve ?? null);
    const bh = asset.buy_and_hold.curve ?? null;
    const times = asset.curve_times ?? null;
    const length = average.length;
    const barsPerPoint = asset.n_bars / Math.max(length - 1, 1);
    return average.map((value, i) => ({
      t: times?.[i] ?? `bar ${fmtInt(Math.round(i * barsPerPoint))}`,
      average: value,
      selected: selected?.[i] ?? null,
      benchmark: bh?.[i] ?? null,
    }));
  }, [asset, seed]);

  const seriesLabel = (name: string) =>
    name === "average"
      ? t.explorer.averageLine
      : name === "benchmark"
        ? t.explorer.benchmarkLine
        : t.explorer.seedLine.replace("{seed}", String(seed));

  return (
    <ResponsiveContainer width="100%" height={340}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} vertical={false} />
        <XAxis
          dataKey="t"
          tick={{ fontSize: 11, fill: CHART.axis }}
          stroke={CHART.axis}
          minTickGap={48}
          tickFormatter={(v: string) => (v.startsWith("bar ") ? v : v.slice(0, 7))}
        />
        <YAxis
          tick={{ fontSize: 11, fill: CHART.axis }}
          stroke={CHART.axis}
          width={52}
          tickFormatter={(v) => fmtNumber(v, 2)}
          domain={["auto", "auto"]}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "rgb(var(--surface))",
            border: "1px solid rgb(var(--border))",
            borderRadius: 8,
            color: "rgb(var(--fg))",
          }}
          formatter={(value: number, name: string) => [fmtNumber(value, 4), seriesLabel(name)]}
          labelFormatter={(label: string) => label}
        />
        <ReferenceLine y={1} stroke={CHART.axis} strokeDasharray="4 3" />
        <Line
          type="monotone"
          dataKey="benchmark"
          stroke={CHART.benchmark}
          strokeWidth={1.6}
          strokeDasharray="6 4"
          dot={false}
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="average"
          stroke={CHART.average}
          strokeWidth={2.4}
          dot={false}
          isAnimationActive={false}
        />
        {seed !== "average" && (
          <Line
            type="monotone"
            dataKey="selected"
            stroke={CHART.seed}
            strokeWidth={1.6}
            dot={false}
            isAnimationActive={false}
          />
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}

function ChartLegend({ seed }: { seed: number | "average" }) {
  const t = useI18n();
  const item = (color: string, dashed: boolean, label: string) => (
    <span className="flex items-center gap-1.5 text-xs text-muted">
      <svg width="22" height="8" aria-hidden>
        <line
          x1="1"
          y1="4"
          x2="21"
          y2="4"
          stroke={color}
          strokeWidth="2.4"
          strokeDasharray={dashed ? "5 3" : undefined}
        />
      </svg>
      {label}
    </span>
  );
  return (
    <div className="mt-2 flex flex-wrap items-center gap-4">
      {item(CHART.average, false, t.explorer.averageLine)}
      {seed !== "average" &&
        item(CHART.seed, false, t.explorer.seedLine.replace("{seed}", String(seed)))}
      {item(CHART.benchmark, true, t.explorer.benchmarkLine)}
    </div>
  );
}

/** Median / min / max of one metric across the seeds (nulls dropped). */
function seedAggregate(
  seeds: SeedEntry[],
  key: string
): { median: number; min: number; max: number } | null {
  const vals = seeds
    .map((s) => s.metrics[key])
    .filter((v): v is number => v != null && !Number.isNaN(v))
    .sort((a, b) => a - b);
  if (vals.length === 0) return null;
  const mid = Math.floor(vals.length / 2);
  const median = vals.length % 2 ? vals[mid] : (vals[mid - 1] + vals[mid]) / 2;
  return { median, min: vals[0], max: vals[vals.length - 1] };
}

const fmtParams = (params: Record<string, unknown>): string =>
  Object.entries(params)
    .map(([k, v]) => `${k}=${Array.isArray(v) ? v.join("+") : String(v)}`)
    .join(" · ");

function FamilyDetailBlock({ entry }: { entry: StudyIndexEntry }) {
  const t = useI18n();
  const { data, error } = useSWR<FamilyFile>(entry.file, loadJson);
  const [assetKey, setAssetKey] = useState<string>("BTCUSDT");
  const [seed, setSeed] = useState<number | "average">("average");

  if (error) return <ErrorState title={t.explorer.loadError} />;
  if (!data) return <Skeleton className="h-96" />;

  const asset = data.per_asset[assetKey] ?? Object.values(data.per_asset)[0];
  const verdict = verdictLabel(entry.verdict, t);
  const seedsByReturn = [...asset.seeds].sort(
    (a, b) => (a.metrics.total_return ?? 0) - (b.metrics.total_return ?? 0)
  );
  const worstSeed = seedsByReturn[0]?.seed;
  const bestSeed = seedsByReturn[seedsByReturn.length - 1]?.seed;
  const selectedSeed = seed === "average" ? null : asset.seeds.find((s) => s.seed === seed);
  const metricsSource = seed === "average" ? null : (selectedSeed?.metrics ?? {});
  const allWinners = asset.seeds.flatMap((s) => s.fold_winners ?? []);
  const mc = asset.monte_carlo;

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
              {seedsByReturn.map((s) => (
                <option key={s.seed} value={s.seed}>
                  {s.seed} · {fmtMetric("total_return", s.metrics.total_return)}
                </option>
              ))}
            </select>
          </label>
          {bestSeed != null && worstSeed != null && (
            <div className="flex items-center gap-1 rounded-md border border-border p-0.5">
              <button
                type="button"
                onClick={() => setSeed(bestSeed)}
                aria-pressed={seed === bestSeed}
                className={`rounded px-2 py-1 text-xs transition-colors ${
                  seed === bestSeed
                    ? "bg-accent text-accent-fg"
                    : "text-muted hover:bg-surface-2 hover:text-fg"
                }`}
              >
                {t.explorer.bestSeed}
              </button>
              <button
                type="button"
                onClick={() => setSeed(worstSeed)}
                aria-pressed={seed === worstSeed}
                className={`rounded px-2 py-1 text-xs transition-colors ${
                  seed === worstSeed
                    ? "bg-accent text-accent-fg"
                    : "text-muted hover:bg-surface-2 hover:text-fg"
                }`}
              >
                {t.explorer.worstSeed}
              </button>
            </div>
          )}
          <span className="text-xs text-muted">
            {t.explorer.buyAndHold}:{" "}
            <span className={signClass(asset.buy_and_hold.total_return)}>
              {fmtMetric("total_return", asset.buy_and_hold.total_return)}
            </span>
          </span>
        </div>
        <EquityChart asset={asset} seed={seed} />
        <ChartLegend seed={seed} />
      </Card>

      <Card>
        <CardHeader
          title={t.explorer.metricsTitle}
          subtitle={
            seed === "average"
              ? `${t.explorer.metricsSubtitle} ${t.explorer.medianNote}`
              : t.explorer.metricsSubtitle
          }
        />
        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3 lg:grid-cols-4">
          {METRIC_ORDER.map((key) => {
            const agg = seed === "average" ? seedAggregate(asset.seeds, key) : null;
            const value =
              seed === "average"
                ? (agg?.median ?? null)
                : ((metricsSource as Record<string, number | null>)[key] ?? null);
            const title =
              agg != null
                ? `${t.explorer.medianAcrossSeeds.replace("{n}", String(asset.seeds.length))} · ${fmtMetric(key, agg.min)} … ${fmtMetric(key, agg.max)}`
                : undefined;
            return (
              <div
                key={key}
                title={title}
                className="rounded-md border border-border/60 bg-surface-2/50 px-3 py-2"
              >
                <dt className="text-[11px] uppercase tracking-wide text-muted">
                  {t.explorer.metric[key]}
                </dt>
                <dd
                  className={`mt-1 text-sm font-medium tabular-nums ${
                    key === "total_return" || key === "ann_return"
                      ? signClass(value)
                      : "text-fg"
                  }`}
                >
                  {fmtMetric(key, value)}
                </dd>
              </div>
            );
          })}
        </dl>
      </Card>

      <Card>
        <CardHeader
          title={t.explorer.configTitle}
          subtitle={
            selectedSeed
              ? t.explorer.configSubtitleSeed.replace("{seed}", String(selectedSeed.seed))
              : t.explorer.configSubtitleAverage.replace("{n}", fmtInt(allWinners.length))
          }
        />
        {selectedSeed?.fold_winners?.length ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-muted">
                  <th className="px-3 py-2 font-medium">{t.explorer.configFold}</th>
                  <th className="px-3 py-2 font-medium">{t.explorer.configParams}</th>
                  <th className="px-3 py-2 text-right font-medium">{t.explorer.configValSharpe}</th>
                  <th className="px-3 py-2 text-right font-medium">
                    {t.explorer.configTestSharpe}
                  </th>
                  <th className="px-3 py-2 text-right font-medium">
                    {t.explorer.configTestReturn}
                  </th>
                  <th className="px-3 py-2 text-right font-medium">{t.explorer.configTrades}</th>
                </tr>
              </thead>
              <tbody>
                {selectedSeed.fold_winners.map((w) => (
                  <tr key={String(w.fold)} className="border-b border-border/50 last:border-0">
                    <td className="px-3 py-2 tabular-nums text-muted">{w.fold}</td>
                    <td className="px-3 py-2 font-mono text-xs">{fmtParams(w.params)}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-muted">
                      {fmtNumber(w.val_sharpe, 2)}
                    </td>
                    <td className={`px-3 py-2 text-right tabular-nums ${signClass(w.test_sharpe)}`}>
                      {fmtNumber(w.test_sharpe, 2)}
                    </td>
                    <td className={`px-3 py-2 text-right tabular-nums ${signClass(w.test_return)}`}>
                      {fmtMetric("total_return", w.test_return)}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-muted">
                      {w.n_trades == null ? "—" : fmtInt(w.n_trades)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : allWinners.length > 0 ? (
          <ParamFrequencyTable winners={allWinners} />
        ) : (
          <EmptyState title={t.common.noData} />
        )}
      </Card>

      {mc && (
        <Card>
          <CardHeader
            title={t.explorer.mcTitle}
            subtitle={t.explorer.mcSubtitle
              .replace("{block}", fmtInt(mc.block_bars))
              .replace("{paths}", fmtInt(mc.n_paths))
              .replace("{seed}", String(mc.source_seed))}
          />
          <div className="grid gap-4 lg:grid-cols-[1fr_auto]">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[420px] text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-muted">
                    <th className="px-3 py-2 font-medium">{t.explorer.mcQuantile}</th>
                    <th className="px-3 py-2 text-right font-medium">
                      {t.explorer.mcTotalReturn}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(mc.terminal_quantiles).map(([q, v]) => (
                    <tr key={q} className="border-b border-border/50 last:border-0">
                      <td className="px-3 py-2 font-mono text-xs uppercase text-muted">{q}</td>
                      <td className={`px-3 py-2 text-right tabular-nums ${signClass(v)}`}>
                        {fmtMetric("total_return", v)}
                      </td>
                    </tr>
                  ))}
                  <tr className="border-t border-border">
                    <td className="px-3 py-2 text-xs font-medium">{t.explorer.mcObserved}</td>
                    <td
                      className={`px-3 py-2 text-right font-medium tabular-nums ${signClass(mc.observed_total_return)}`}
                    >
                      {fmtMetric("total_return", mc.observed_total_return)}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="flex flex-col gap-3 self-start">
              <div className="rounded-md border border-border/60 bg-surface-2/50 px-4 py-3">
                <p className="text-[11px] uppercase tracking-wide text-muted">
                  {t.explorer.mcPercentile}
                </p>
                <p className="tabular mt-1 text-xl font-semibold">
                  {fmtNumber(mc.observed_percentile, 2)}
                </p>
              </div>
              <div className="rounded-md border border-border/60 bg-surface-2/50 px-4 py-3">
                <p className="text-[11px] uppercase tracking-wide text-muted">
                  {t.explorer.mcProbPositive}
                </p>
                <p className="tabular mt-1 text-xl font-semibold">
                  {fmtMetric("hit_rate", mc.probability_positive)}
                </p>
              </div>
            </div>
          </div>
          <p className="mt-3 rounded-md border border-warn/40 bg-warn/10 px-3 py-2 text-xs text-warn">
            {t.explorer.mcNote}
          </p>
        </Card>
      )}
    </div>
  );
}

/** Which parameter values the search kept choosing, across every seed's folds. */
function ParamFrequencyTable({ winners }: { winners: FoldWinner[] }) {
  const t = useI18n();
  const rows = useMemo(() => {
    const counts = new Map<string, Map<string, number>>();
    for (const w of winners) {
      for (const [param, raw] of Object.entries(w.params)) {
        const value = Array.isArray(raw) ? raw.join("+") : String(raw);
        const inner = counts.get(param) ?? new Map<string, number>();
        inner.set(value, (inner.get(value) ?? 0) + 1);
        counts.set(param, inner);
      }
    }
    return [...counts.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([param, inner]) => ({
        param,
        top: [...inner.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3),
      }));
  }, [winners]);

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[480px] text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-muted">
            <th className="px-3 py-2 font-medium">{t.explorer.configParam}</th>
            <th className="px-3 py-2 font-medium">{t.explorer.configTopValues}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.param} className="border-b border-border/50 last:border-0">
              <td className="px-3 py-2 font-mono text-xs">{row.param}</td>
              <td className="px-3 py-2 text-xs text-muted">
                {row.top.map(([value, n], i) => (
                  <span key={value}>
                    {i > 0 && " · "}
                    <span className="font-mono text-fg">{value}</span> ({n})
                  </span>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
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
