"use client";

// Strategy laboratory: an in-browser backtest of four study families over the
// real development-partition candles. The engine (src/lib/lab) is a port of
// the Python one; nothing here can touch the holdout (excluded at export) and
// nothing here promotes anything (banner + test-battery disclaimer).

import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ComposedChart,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { PageShell } from "@/components/layout/PageShell";
import { ExploratoryBanner } from "@/components/ui/ExploratoryBanner";
import { Card, CardHeader } from "@/components/ui/Card";
import { ErrorState, Skeleton } from "@/components/ui/States";
import { useI18n, useIntlLocale, type Dictionary } from "@/lib/i18n";
import { fmtInt, fmtNumber, fmtSignedPercent, signClass } from "@/lib/format";
import { useLabData } from "@/lib/lab/data";
import {
  buyAndHold,
  circularShiftTest,
  computeMetrics,
  extractTrades,
  runBacktest,
  type Ledger,
  type Metrics,
  type Trade,
} from "@/lib/lab/engine";
import { STRATEGIES, type StrategyDef, type StrategyId } from "@/lib/lab/strategies";
import { useAttempts } from "@/lib/lab/attempts";
import { WalkForwardSection } from "./WalkForwardSection";

const ACCENT = "var(--accent)";
const CHART = {
  grid: "rgb(148 163 184 / 0.15)",
  axis: "rgb(148 163 184)",
  strategy: "rgb(45 212 191)",
  buyHold: "rgb(148 163 184)",
  negative: "rgb(248 113 113)",
  amber: "rgb(251 191 36)",
};

const N_SHIFTS = 400;
const SIGNAL_WINDOW = 500;

/* ------------------------------------------------------------------------ */
/* Schematic strategy illustrations (labelled as such; not data).            */
/* ------------------------------------------------------------------------ */

function StrategySketch({ id }: { id: StrategyId }) {
  const w = 220;
  const h = 72;
  const common = { width: "100%", viewBox: `0 0 ${w} ${h}`, role: "img" as const };
  const price = "M4,52 C24,48 32,30 52,34 S84,58 104,50 S140,18 164,24 S200,40 216,30";
  if (id === "momentum") {
    return (
      <svg {...common} aria-label="momentum sketch">
        <path d={price} fill="none" stroke={CHART.axis} strokeWidth="1.4" />
        <path
          d="M4,54 C40,50 70,42 110,40 S180,30 216,26"
          fill="none"
          stroke={CHART.strategy}
          strokeWidth="1.6"
        />
        <path
          d="M4,48 C40,50 80,50 120,44 S180,36 216,34"
          fill="none"
          stroke={CHART.amber}
          strokeWidth="1.6"
          strokeDasharray="4 3"
        />
        <circle cx="118" cy="43" r="3.4" fill={CHART.strategy} />
      </svg>
    );
  }
  if (id === "mean_reversion") {
    return (
      <svg {...common} aria-label="mean reversion sketch">
        <line x1="0" y1="36" x2={w} y2="36" stroke={CHART.axis} strokeDasharray="4 3" />
        <line x1="0" y1="16" x2={w} y2="16" stroke={CHART.negative} strokeDasharray="2 3" />
        <line x1="0" y1="56" x2={w} y2="56" stroke={CHART.strategy} strokeDasharray="2 3" />
        <path
          d="M4,36 C20,10 34,10 50,30 S76,62 96,58 S120,12 140,14 S168,60 190,56 S208,40 216,36"
          fill="none"
          stroke={CHART.axis}
          strokeWidth="1.4"
        />
        <circle cx="96" cy="58" r="3.4" fill={CHART.strategy} />
        <circle cx="140" cy="14" r="3.4" fill={CHART.negative} />
      </svg>
    );
  }
  if (id === "breakout") {
    return (
      <svg {...common} aria-label="breakout sketch">
        <line x1="0" y1="24" x2="150" y2="24" stroke={CHART.axis} strokeDasharray="4 3" />
        <line x1="0" y1="52" x2="150" y2="52" stroke={CHART.axis} strokeDasharray="4 3" />
        <path
          d="M4,40 C24,32 40,48 60,40 S100,32 128,42 L150,36 C166,22 186,14 216,10"
          fill="none"
          stroke={CHART.axis}
          strokeWidth="1.4"
        />
        <circle cx="152" cy="24" r="3.4" fill={CHART.strategy} />
      </svg>
    );
  }
  return (
    <svg {...common} aria-label="volatility breakout sketch">
      <line x1="0" y1="24" x2="150" y2="24" stroke={CHART.axis} strokeDasharray="4 3" />
      <rect x="0" y="12" width="150" height="12" fill={CHART.amber} opacity="0.15" />
      <path
        d="M4,42 C24,36 44,46 64,40 S104,34 128,44 L150,34 C168,18 190,10 216,6"
        fill="none"
        stroke={CHART.axis}
        strokeWidth="1.4"
      />
      <circle cx="156" cy="14" r="3.4" fill={CHART.strategy} />
    </svg>
  );
}

/* ------------------------------------------------------------------------ */
/* Result model                                                              */
/* ------------------------------------------------------------------------ */

interface RunResult {
  ledger: Ledger;
  trades: Trade[];
  bh: Ledger;
  splitIdx: number;
  metrics: { inSample: Metrics; outSample: Metrics; full: Metrics; bhOut: Metrics };
  nullTest: { pValue: number; realReturn: number };
  params: Record<string, number | string>;
  symbol: string;
  strategyId: StrategyId;
}

function decimate<T>(items: T[], target: number): T[] {
  if (items.length <= target) return items;
  const step = items.length / target;
  const out: T[] = [];
  for (let i = 0; i < target; i++) out.push(items[Math.floor(i * step)]);
  out.push(items[items.length - 1]);
  return out;
}

const dateFmt = (locale: string) => (unixSeconds: number) =>
  new Date(unixSeconds * 1000).toLocaleDateString(locale, { year: "2-digit", month: "short" });

/* ------------------------------------------------------------------------ */
/* Panels                                                                    */
/* ------------------------------------------------------------------------ */

function EquityPanel({ result, t }: { result: RunResult; t: Dictionary }) {
  const intl = useIntlLocale();
  const rows = useMemo(() => {
    const raw = Array.from(result.ledger.t).map((time, i) => ({
      time,
      equity: result.ledger.equity[i],
      bh: result.bh.equity[i],
      dd: result.ledger.drawdown[i],
    }));
    return decimate(raw, 700);
  }, [result]);
  const splitTime = result.ledger.t[result.splitIdx];

  return (
    <Card>
      <CardHeader title={t.lab.equityTitle} subtitle={t.lab.equitySubtitle} />
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={rows} margin={{ top: 6, right: 12, bottom: 4, left: 4 }}>
          <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="time"
            type="number"
            domain={["dataMin", "dataMax"]}
            tickFormatter={dateFmt(intl)}
            stroke={CHART.axis}
            tick={{ fontSize: 11 }}
          />
          <YAxis
            stroke={CHART.axis}
            tick={{ fontSize: 11 }}
            width={48}
            tickFormatter={(v) => `${Number(v).toFixed(1)}×`}
            domain={["auto", "auto"]}
          />
          <Tooltip
            formatter={(value: number, name: string) => [Number(value).toFixed(3) + "×", name]}
            labelFormatter={(v) => new Date(Number(v) * 1000).toISOString().slice(0, 10)}
            contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--border)" }}
          />
          <ReferenceLine y={1} stroke={CHART.axis} strokeDasharray="4 3" />
          <ReferenceLine x={splitTime} stroke={CHART.amber} strokeDasharray="4 3" />
          <Line
            dataKey="bh"
            name={t.lab.buyHold}
            dot={false}
            stroke={CHART.buyHold}
            strokeWidth={1.2}
            isAnimationActive={false}
          />
          <Line
            dataKey="equity"
            name={t.lab.strategyLabel}
            dot={false}
            stroke={CHART.strategy}
            strokeWidth={1.8}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>

      <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-muted">
        {t.lab.drawdownTitle}
      </p>
      <ResponsiveContainer width="100%" height={110}>
        <AreaChart data={rows} margin={{ top: 4, right: 12, bottom: 0, left: 4 }}>
          <XAxis dataKey="time" hide type="number" domain={["dataMin", "dataMax"]} />
          <YAxis
            stroke={CHART.axis}
            tick={{ fontSize: 10 }}
            width={48}
            tickFormatter={(v) => `${(Number(v) * 100).toFixed(0)}%`}
          />
          <ReferenceLine x={splitTime} stroke={CHART.amber} strokeDasharray="4 3" />
          <Area
            dataKey="dd"
            stroke={CHART.negative}
            fill={CHART.negative}
            fillOpacity={0.25}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </Card>
  );
}

interface MarkerPoint {
  time: number;
  price: number;
  kind: "long" | "short" | "exit";
}

function SignalsPanel({
  result,
  bars,
  t,
}: {
  result: RunResult;
  bars: { t: Float64Array; c: Float64Array };
  t: Dictionary;
}) {
  const intl = useIntlLocale();
  const n = result.ledger.t.length;
  const [center, setCenter] = useState(Math.max(0, n - Math.floor(SIGNAL_WINDOW / 2)));

  const { rows, markers } = useMemo(() => {
    const half = Math.floor(SIGNAL_WINDOW / 2);
    const from = Math.max(0, Math.min(center - half, n - SIGNAL_WINDOW));
    const to = Math.min(n, from + SIGNAL_WINDOW);
    const rows = [] as { time: number; close: number }[];
    for (let i = from; i < to; i++) rows.push({ time: bars.t[i], close: bars.c[i] });
    const markers: MarkerPoint[] = [];
    for (const trade of result.trades) {
      if (trade.entryIndex >= from && trade.entryIndex < to) {
        markers.push({
          time: bars.t[trade.entryIndex],
          price: trade.entryPrice,
          kind: trade.position === 1 ? "long" : "short",
        });
      }
      const exitBar = trade.exitIndex + 1;
      if (trade.exitReason !== "open" && exitBar >= from && exitBar < to) {
        markers.push({
          time: bars.t[exitBar] ?? bars.t[trade.exitIndex],
          price: trade.exitPrice,
          kind: "exit",
        });
      }
    }
    return { rows, markers };
  }, [center, result, bars, n]);

  function markerShape(kind: MarkerPoint["kind"]) {
    function Marker(props: { cx?: number; cy?: number }) {
      const { cx, cy } = props;
      if (cx == null || cy == null) return <g />;
      if (kind === "long") {
        return (
          <path
            d={`M${cx},${cy - 5} L${cx - 4.5},${cy + 3.5} L${cx + 4.5},${cy + 3.5} Z`}
            fill={CHART.strategy}
          />
        );
      }
      if (kind === "short") {
        return (
          <path
            d={`M${cx},${cy + 5} L${cx - 4.5},${cy - 3.5} L${cx + 4.5},${cy - 3.5} Z`}
            fill={CHART.negative}
          />
        );
      }
      return (
        <g stroke={CHART.axis} strokeWidth="1.6">
          <line x1={cx - 3.5} y1={cy - 3.5} x2={cx + 3.5} y2={cy + 3.5} />
          <line x1={cx - 3.5} y1={cy + 3.5} x2={cx + 3.5} y2={cy - 3.5} />
        </g>
      );
    }
    Marker.displayName = `Marker_${kind}`;
    return Marker;
  }

  return (
    <Card>
      <CardHeader
        title={t.lab.signalsTitle}
        subtitle={t.lab.signalsSubtitle.replace("{bars}", String(SIGNAL_WINDOW))}
      />
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={rows} margin={{ top: 6, right: 12, bottom: 4, left: 4 }}>
          <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="time"
            type="number"
            domain={["dataMin", "dataMax"]}
            tickFormatter={dateFmt(intl)}
            stroke={CHART.axis}
            tick={{ fontSize: 11 }}
          />
          <YAxis
            stroke={CHART.axis}
            tick={{ fontSize: 11 }}
            width={64}
            domain={["auto", "auto"]}
            tickFormatter={(v) => Number(v).toLocaleString(intl)}
          />
          <Tooltip
            labelFormatter={(v) => new Date(Number(v) * 1000).toISOString().slice(0, 13) + "h"}
            contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--border)" }}
          />
          <Line
            dataKey="close"
            dot={false}
            stroke={CHART.axis}
            strokeWidth={1.2}
            isAnimationActive={false}
            name="close"
          />
          <Scatter
            data={markers
              .filter((m) => m.kind === "long")
              .map((m) => ({ time: m.time, close: m.price }))}
            dataKey="close"
            shape={markerShape("long")}
            isAnimationActive={false}
          />
          <Scatter
            data={markers
              .filter((m) => m.kind === "short")
              .map((m) => ({ time: m.time, close: m.price }))}
            dataKey="close"
            shape={markerShape("short")}
            isAnimationActive={false}
          />
          <Scatter
            data={markers
              .filter((m) => m.kind === "exit")
              .map((m) => ({ time: m.time, close: m.price }))}
            dataKey="close"
            shape={markerShape("exit")}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
      <label className="mt-3 block text-xs text-muted">
        {t.lab.signalsWindow}
        <input
          type="range"
          min={0}
          max={Math.max(0, n - 1)}
          value={center}
          onChange={(event) => setCenter(Number(event.target.value))}
          className="mt-1 w-full accent-[var(--accent)]"
        />
      </label>
    </Card>
  );
}

function MaeMfePanel({ result, t }: { result: RunResult; t: Dictionary }) {
  const points = useMemo(
    () =>
      result.trades.map((trade) => ({
        mae: trade.mae * 100,
        ret: trade.netReturn * 100,
        side: trade.position,
      })),
    [result]
  );
  const outMetrics = result.metrics.outSample;

  return (
    <Card>
      <CardHeader title={t.lab.maefeTitle} subtitle={t.lab.maefeSubtitle} />
      <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
        <ResponsiveContainer width="100%" height={260}>
          <ScatterChart margin={{ top: 8, right: 12, bottom: 18, left: 4 }}>
            <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" />
            <XAxis
              dataKey="mae"
              type="number"
              name="MAE"
              stroke={CHART.axis}
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => `${Number(v).toFixed(1)}%`}
              label={{
                value: t.lab.maefeX,
                position: "insideBottom",
                offset: -10,
                fill: CHART.axis,
                fontSize: 11,
              }}
            />
            <YAxis
              dataKey="ret"
              type="number"
              stroke={CHART.axis}
              tick={{ fontSize: 11 }}
              width={52}
              tickFormatter={(v) => `${Number(v).toFixed(1)}%`}
              label={{
                value: t.lab.maefeY,
                angle: -90,
                position: "insideLeft",
                fill: CHART.axis,
                fontSize: 11,
              }}
            />
            <Tooltip
              formatter={(value: number) => `${Number(value).toFixed(2)}%`}
              contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--border)" }}
            />
            <ReferenceLine y={0} stroke={CHART.axis} strokeDasharray="4 3" />
            <Scatter
              data={points.filter((p) => p.side === 1)}
              fill={CHART.strategy}
              fillOpacity={0.6}
              isAnimationActive={false}
            />
            <Scatter
              data={points.filter((p) => p.side === -1)}
              fill={CHART.negative}
              fillOpacity={0.6}
              isAnimationActive={false}
            />
          </ScatterChart>
        </ResponsiveContainer>

        <div className="flex flex-col justify-center gap-3">
          <div className="grid grid-cols-2 gap-3">
            <Tile
              label={t.lab.medianMae}
              value={fmtSignedPercent(-outMetrics.median_mae, 2)}
              tone="bad"
            />
            <Tile
              label={t.lab.medianMfe}
              value={fmtSignedPercent(outMetrics.median_mfe, 2)}
              tone="good"
            />
            <Tile label={t.lab.eRatio} value={fmtNumber(outMetrics.e_ratio, 2)} />
            <Tile label={t.lab.meanDuration} value={fmtNumber(outMetrics.mean_duration_bars, 1)} />
          </div>
          <p className="text-xs leading-relaxed text-muted">{t.lab.eRatioNote}</p>
        </div>
      </div>
    </Card>
  );
}

function Tile({ label, value, tone }: { label: string; value: string; tone?: "good" | "bad" }) {
  return (
    <div className="rounded-md border border-border bg-surface-2 px-3 py-2.5">
      <p
        className={`tabular text-lg font-semibold ${
          tone === "good" ? "text-positive" : tone === "bad" ? "text-negative" : ""
        }`}
      >
        {value}
      </p>
      <p className="mt-0.5 text-[11px] leading-snug text-muted">{label}</p>
    </div>
  );
}

const PCT_KEYS = new Set([
  "total_return",
  "ann_return",
  "ann_volatility",
  "max_drawdown",
  "time_in_drawdown",
  "hit_rate",
  "exposure",
  "var_95",
  "expected_shortfall_95",
  "expectancy",
  "trade_hit_rate",
  "median_mae",
  "median_mfe",
  "ulcer_index",
]);

function MetricsTable({ result, t }: { result: RunResult; t: Dictionary }) {
  const rows: { key: keyof Metrics; label: string }[] = [
    { key: "total_return", label: t.explorer.metric.total_return },
    { key: "ann_return", label: t.explorer.metric.ann_return },
    { key: "ann_volatility", label: t.explorer.metric.ann_volatility },
    { key: "sharpe", label: t.explorer.metric.sharpe },
    { key: "sortino", label: t.explorer.metric.sortino },
    { key: "calmar", label: t.explorer.metric.calmar },
    { key: "max_drawdown", label: t.explorer.metric.max_drawdown },
    { key: "time_in_drawdown", label: t.explorer.metric.time_in_drawdown },
    { key: "ulcer_index", label: t.lab.ulcer },
    { key: "hit_rate", label: t.explorer.metric.hit_rate },
    { key: "exposure", label: t.explorer.metric.exposure },
    { key: "turnover", label: t.explorer.metric.turnover },
    { key: "n_trades_closed", label: t.lab.nTradesClosed },
    { key: "trade_hit_rate", label: t.lab.tradeHitRate },
    { key: "profit_factor", label: t.lab.profitFactor },
    { key: "expectancy", label: t.lab.expectancy },
    { key: "var_95", label: t.explorer.metric.var_95 },
    { key: "expected_shortfall_95", label: t.explorer.metric.expected_shortfall_95 },
    { key: "longest_win_streak", label: t.lab.winStreak },
    { key: "longest_loss_streak", label: t.lab.lossStreak },
  ];

  const fmt = (key: keyof Metrics, m: Metrics) => {
    const value = m[key];
    if (!Number.isFinite(value)) return "∞";
    if (PCT_KEYS.has(key)) return fmtSignedPercent(value, 2);
    if (key === "n_trades_closed" || key.startsWith("longest")) return fmtInt(value);
    return fmtNumber(value, 2);
  };

  const cols = [
    { label: t.lab.phaseIn, m: result.metrics.inSample },
    { label: t.lab.phaseOut, m: result.metrics.outSample, highlight: true },
    { label: t.lab.phaseFull, m: result.metrics.full },
    { label: `${t.lab.buyHold} (${t.lab.phaseOut})`, m: result.metrics.bhOut },
  ];

  return (
    <Card>
      <CardHeader title={t.lab.phasesTitle} subtitle={t.lab.splitNote} />
      <div className="overflow-x-auto">
        <table className="w-full min-w-[680px] text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-muted">
              <th className="py-2 pr-4 font-medium" />
              {cols.map((col) => (
                <th
                  key={col.label}
                  className={`py-2 pr-4 text-right font-medium ${col.highlight ? "text-accent" : ""}`}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {rows.map((row) => (
              <tr key={row.key}>
                <th scope="row" className="py-2 pr-4 text-left font-normal text-muted">
                  {row.label}
                </th>
                {cols.map((col) => (
                  <td
                    key={col.label}
                    className={`tabular py-2 pr-4 text-right ${
                      row.key === "total_return" ? signClass(col.m[row.key]) : ""
                    } ${col.highlight ? "font-medium" : ""}`}
                  >
                    {fmt(row.key, col.m)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function TestsPanel({ result, t }: { result: RunResult; t: Dictionary }) {
  const out = result.metrics.outSample;
  const bh = result.metrics.bhOut;
  const tests = [
    {
      name: t.lab.testReturn,
      desc: t.lab.testReturnDesc,
      pass: out.total_return > 0,
      value: fmtSignedPercent(out.total_return, 2),
    },
    {
      name: t.lab.testSharpe,
      desc: t.lab.testSharpeDesc,
      pass: out.sharpe > 0,
      value: fmtNumber(out.sharpe, 2),
    },
    {
      name: t.lab.testBh,
      desc: t.lab.testBhDesc,
      pass: out.total_return > bh.total_return,
      value: `${fmtSignedPercent(out.total_return, 1)} vs ${fmtSignedPercent(bh.total_return, 1)}`,
    },
    {
      name: t.lab.testNull,
      desc: t.lab.testNullDesc.replace("{n}", String(N_SHIFTS)),
      pass: result.nullTest.pValue < 0.05,
      value: `${t.lab.pValueLabel} = ${fmtNumber(result.nullTest.pValue, 3)}`,
    },
  ];
  const passed = tests.filter((test) => test.pass).length;

  return (
    <Card>
      <CardHeader title={`${t.lab.testsTitle} — ${passed}/4`} subtitle={t.lab.testsSubtitle} />
      <ul className="space-y-3">
        {tests.map((test) => (
          <li
            key={test.name}
            className="flex flex-col gap-1.5 rounded-md border border-border bg-surface-2 px-4 py-3 sm:flex-row sm:items-center sm:gap-4"
          >
            <span
              className={`inline-flex w-fit shrink-0 rounded border px-2 py-0.5 text-[11px] font-semibold ${
                test.pass
                  ? "border-positive/40 bg-positive/10 text-positive"
                  : "border-negative/40 bg-negative/10 text-negative"
              }`}
            >
              {test.pass ? t.lab.pass : t.lab.fail}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">{test.name}</p>
              <p className="mt-0.5 text-xs leading-relaxed text-muted">{test.desc}</p>
            </div>
            <span className="tabular shrink-0 font-mono text-xs text-muted">{test.value}</span>
          </li>
        ))}
      </ul>
      <p className="mt-4 rounded-md border border-warn/40 bg-warn/10 px-4 py-3 text-xs leading-relaxed text-warn">
        {t.lab.testsDisclaimer}
      </p>
    </Card>
  );
}

/* ------------------------------------------------------------------------ */
/* Page                                                                      */
/* ------------------------------------------------------------------------ */

export default function LaboratorioPage() {
  const t = useI18n();
  const intl = useIntlLocale();
  const [symbol, setSymbol] = useState("BTCUSDT");
  const { data, error, isLoading } = useLabData(symbol);

  const [strategyId, setStrategyId] = useState<StrategyId>("momentum");
  const def: StrategyDef = STRATEGIES.find((s) => s.id === strategyId) ?? STRATEGIES[0];

  const [values, setValues] = useState<Record<string, number | string>>(() =>
    Object.fromEntries(STRATEGIES[0].params.map((p) => [p.key, p.default]))
  );
  const [feeBps, setFeeBps] = useState(4);
  const [slipBps, setSlipBps] = useState(1);
  const [splitPct, setSplitPct] = useState(70);
  const [running, setRunning] = useState(false);
  const { add: addAttempts } = useAttempts();
  const [result, setResult] = useState<RunResult | null>(null);

  const pickStrategy = (id: StrategyId) => {
    setStrategyId(id);
    const nextDef = STRATEGIES.find((s) => s.id === id) ?? STRATEGIES[0];
    setValues(Object.fromEntries(nextDef.params.map((p) => [p.key, p.default])));
  };

  const run = () => {
    if (!data) return;
    setRunning(true);
    // Yield one frame so the "running" state paints before the compute burst.
    setTimeout(() => {
      try {
        const costs = { feeBpsPerSide: feeBps, slippageBpsPerSide: slipBps };
        const side = def.run(data.bars, values);
        const ledger = runBacktest(data.bars, side, costs, data.funding);
        const trades = extractTrades(ledger, data.bars);
        const bh = buyAndHold(data.bars, costs, data.funding);
        const n = ledger.net.length;
        const splitIdx = Math.max(1, Math.min(n - 2, Math.floor((splitPct / 100) * n)));
        const bhTrades = extractTrades(bh, data.bars);
        const nullTest = circularShiftTest(ledger, costs, splitIdx, n, N_SHIFTS, 42);
        addAttempts(1);
        setResult({
          ledger,
          trades,
          bh,
          splitIdx,
          metrics: {
            inSample: computeMetrics(ledger, trades, 0, splitIdx),
            outSample: computeMetrics(ledger, trades, splitIdx, n),
            full: computeMetrics(ledger, trades, 0, n),
            bhOut: computeMetrics(bh, bhTrades, splitIdx, n),
          },
          nullTest,
          params: { ...values },
          symbol,
          strategyId,
        });
      } finally {
        setRunning(false);
      }
    }, 30);
  };

  return (
    <PageShell title={t.lab.title}>
      <ExploratoryBanner message={t.lab.banner} />

      <Card>
        <CardHeader title={t.lab.title} subtitle={t.lab.subtitle} />
        <dl className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {[
            { q: t.lab.que, a: t.lab.queAnswer },
            { q: t.lab.comoFunciona, a: t.lab.comoFuncionaAnswer },
            { q: t.lab.queNo, a: t.lab.queNoAnswer },
          ].map(({ q, a }) => (
            <div key={q} className="rounded-md border border-border bg-surface-2 px-4 py-3">
              <dt className="text-xs font-semibold uppercase tracking-wide text-accent">{q}</dt>
              <dd className="mt-2 text-sm text-muted">{a}</dd>
            </div>
          ))}
        </dl>
      </Card>

      {/* Strategy picker with schematic mini-panels. */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {STRATEGIES.map((s) => {
          const copy = t.lab.strategies[s.id];
          const active = s.id === strategyId;
          return (
            <button
              key={s.id}
              type="button"
              onClick={() => pickStrategy(s.id)}
              aria-pressed={active}
              className={`flex h-full flex-col gap-2 rounded-card border p-4 text-left transition-colors ${
                active
                  ? "border-accent/60 bg-surface"
                  : "border-border bg-surface/60 hover:border-accent/30"
              }`}
            >
              <p className="text-sm font-semibold">{copy.name}</p>
              <p className="text-xs text-muted">{copy.tagline}</p>
              <div className="mt-1 rounded-md border border-border bg-surface-2 p-2">
                <StrategySketch id={s.id} />
              </div>
              <p className="text-xs leading-relaxed text-muted">{copy.how}</p>
              <p className="mt-auto pt-1 text-[10px] uppercase tracking-wide text-muted/70">
                {t.lab.exampleCaption}
              </p>
            </button>
          );
        })}
      </div>

      {/* Configuration + run. */}
      <Card>
        <CardHeader title={t.lab.paramsTitle} subtitle={t.lab.studyValuesNote} />
        <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
          <div className="grid gap-4 sm:grid-cols-2">
            {def.params.map((p) => (
              <label key={p.key} className="block text-sm">
                <span className="font-mono text-xs text-muted">{p.key}</span>
                {p.kind === "choice" ? (
                  <select
                    value={String(values[p.key])}
                    onChange={(event) => setValues((v) => ({ ...v, [p.key]: event.target.value }))}
                    className="mt-1 w-full rounded-md border border-border bg-surface-2 px-3 py-2 text-sm"
                  >
                    {p.studyValues.map((option) => (
                      <option key={String(option)} value={String(option)}>
                        {String(option)}
                      </option>
                    ))}
                  </select>
                ) : (
                  <>
                    <input
                      type="number"
                      value={Number(values[p.key])}
                      min={p.min}
                      max={p.max}
                      step={p.step ?? 1}
                      onChange={(event) =>
                        setValues((v) => ({ ...v, [p.key]: Number(event.target.value) }))
                      }
                      className="mt-1 w-full rounded-md border border-border bg-surface-2 px-3 py-2 text-sm"
                    />
                    <span className="mt-1.5 flex flex-wrap gap-1.5">
                      {p.studyValues.map((option) => (
                        <button
                          key={String(option)}
                          type="button"
                          onClick={() => setValues((v) => ({ ...v, [p.key]: Number(option) }))}
                          className={`rounded border px-2 py-0.5 font-mono text-[11px] transition-colors ${
                            Number(values[p.key]) === Number(option)
                              ? "border-accent/60 bg-accent/10 text-accent"
                              : "border-border text-muted hover:text-fg"
                          }`}
                        >
                          {String(option)}
                        </button>
                      ))}
                    </span>
                  </>
                )}
              </label>
            ))}
          </div>

          <div className="space-y-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                {t.lab.pickAsset}
              </p>
              <div className="mt-1.5 inline-flex rounded-md border border-border bg-surface-2 p-1">
                {["BTCUSDT", "ETHUSDT"].map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setSymbol(s)}
                    className={`rounded px-3 py-1 text-sm font-medium transition-colors ${
                      s === symbol ? "bg-[var(--accent)] text-white" : "text-muted hover:text-fg"
                    }`}
                  >
                    {s.replace("USDT", "")}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                {t.lab.costsTitle}
              </p>
              <div className="mt-1.5 grid grid-cols-2 gap-3">
                <label className="block text-xs text-muted">
                  {t.lab.fee}
                  <input
                    type="number"
                    value={feeBps}
                    min={0}
                    max={50}
                    step={0.5}
                    onChange={(event) => setFeeBps(Number(event.target.value))}
                    className="mt-1 w-full rounded-md border border-border bg-surface-2 px-3 py-2 text-sm text-fg"
                  />
                </label>
                <label className="block text-xs text-muted">
                  {t.lab.slippage}
                  <input
                    type="number"
                    value={slipBps}
                    min={0}
                    max={50}
                    step={0.5}
                    onChange={(event) => setSlipBps(Number(event.target.value))}
                    className="mt-1 w-full rounded-md border border-border bg-surface-2 px-3 py-2 text-sm text-fg"
                  />
                </label>
              </div>
              <p className="mt-1.5 text-[11px] text-muted/80">{t.lab.costsNote}</p>
            </div>

            <label className="block text-xs text-muted">
              {t.lab.splitLabel}: <span className="tabular font-medium text-fg">{splitPct}%</span>
              <input
                type="range"
                min={40}
                max={90}
                value={splitPct}
                onChange={(event) => setSplitPct(Number(event.target.value))}
                className="mt-1 w-full accent-[var(--accent)]"
              />
            </label>

            <button
              type="button"
              onClick={run}
              disabled={!data || running}
              className="w-full rounded-md px-4 py-2.5 text-sm font-semibold text-white transition-opacity disabled:opacity-50"
              style={{ background: ACCENT }}
            >
              {running ? t.lab.running : t.lab.run}
            </button>

            {isLoading && <p className="text-xs text-muted">{t.lab.dataLoading}</p>}
            {error && <ErrorState title={t.lab.dataError} />}
            {data && (
              <p className="text-[11px] leading-relaxed text-muted/80">
                {t.lab.dataFootnote
                  .replace("{n}", data.meta.n.toLocaleString(intl))
                  .replace("{start}", data.meta.start.slice(0, 10))
                  .replace("{end}", data.meta.end.slice(0, 10))
                  .replace("{nf}", String(data.funding.t.length))}
              </p>
            )}
          </div>
        </div>
      </Card>

      {running && <Skeleton className="h-72 w-full" />}

      <WalkForwardSection
        data={data}
        strategyId={strategyId}
        costs={{ feeBpsPerSide: feeBps, slippageBpsPerSide: slipBps }}
      />

      {result && data && !running && (
        <>
          <TestsPanel result={result} t={t} />
          <EquityPanel result={result} t={t} />
          <SignalsPanel result={result} bars={data.bars} t={t} />
          <MetricsTable result={result} t={t} />
          <MaeMfePanel result={result} t={t} />
        </>
      )}

      <Card>
        <CardHeader title={t.lab.pretrainedTitle} subtitle={t.lab.pretrainedBody} />
        <a href="/estrategias" className="text-sm font-medium text-accent hover:underline">
          {t.lab.pretrainedLink}
        </a>
      </Card>
    </PageShell>
  );
}
