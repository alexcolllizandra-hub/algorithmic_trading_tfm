"use client";

// Strategy laboratory: an in-browser backtest of four study families over the
// real development-partition candles. The engine (src/lib/lab) is a port of
// the Python one; nothing here can touch the holdout (excluded at export) and
// nothing here promotes anything (banner + test-battery disclaimer).

import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
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
import { paramSummary, useHistory, type HistoryEntry } from "@/lib/lab/history";
import {
  applyExitOverlay,
  applyRegimeGate,
  applyTrendGate,
  regimeLabels,
  type Regime,
} from "@/lib/lab/exits";
import {
  bootstrapSharpeCI,
  perturbationTornado,
  regimeSplit,
  type RegimeRow,
  type TornadoRow,
} from "@/lib/lab/tests";
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
  if (id === "funding_reversal") {
    return (
      <svg {...common} aria-label="funding reversal sketch">
        <line x1="0" y1="36" x2={w} y2="36" stroke={CHART.axis} strokeDasharray="4 3" />
        {[14, 34, 54, 74, 94, 114, 134, 154, 174, 194].map((x, i) => {
          const heights = [6, 9, 5, 8, 30, 10, 7, 9, 6, 8];
          const hgt = heights[i];
          return (
            <rect
              key={x}
              x={x}
              y={36 - hgt}
              width="7"
              height={hgt}
              fill={hgt > 20 ? CHART.negative : CHART.axis}
              opacity={hgt > 20 ? 0.9 : 0.5}
            />
          );
        })}
        <path d="M98,10 L112,10 L105,20 Z" fill={CHART.strategy} />
        <text x="118" y="16" fontSize="8" fill={CHART.axis}>
          fade
        </text>
      </svg>
    );
  }
  if (id === "intraday_seasonality") {
    return (
      <svg {...common} aria-label="intraday seasonality sketch">
        {Array.from({ length: 24 }, (_, hr) => {
          const x = 4 + hr * 9;
          const active = hr === 14;
          return (
            <rect
              key={hr}
              x={x}
              y={active ? 14 : 30}
              width="7"
              height={active ? 44 : 28}
              rx="1"
              fill={active ? CHART.strategy : CHART.axis}
              opacity={active ? 0.85 : 0.25}
            />
          );
        })}
        <text x="130" y="10" fontSize="8" fill={CHART.axis}>
          14:00 UTC
        </text>
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
  bootstrap: { lo: number; hi: number; median: number };
  stress2xReturn: number;
  twin: { symbol: string; totalReturn: number } | null;
  tornado: TornadoRow[];
  regimes: RegimeRow[];
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

interface CandleRow {
  time: number;
  o: number;
  h: number;
  l: number;
  c: number;
  hl: [number, number];
}

/** Real candlestick: the Bar's [low, high] box gives the wick's pixel span;
 * open/close map linearly inside it. Green when the bar closed up. */
function CandleShape(props: {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  payload?: CandleRow;
}) {
  const { x, y, width, height, payload } = props;
  // On a numeric X axis recharts gives bars no band width; derive one.
  const w = width && width > 0 ? width : 3;
  if (x == null || y == null || !height || !payload) return <g />;
  const { o, h, l, c } = payload;
  const range = h - l;
  if (range <= 0) return <g />;
  const yOf = (v: number) => y + ((h - v) / range) * height;
  const up = c >= o;
  const color = up ? "rgb(45 212 191)" : "rgb(248 113 113)";
  const cx = x + w / 2;
  const bodyTop = yOf(Math.max(o, c));
  const bodyH = Math.max(1, Math.abs(yOf(o) - yOf(c)));
  const bodyW = Math.max(1.5, w * 0.7);
  return (
    <g>
      <line x1={cx} y1={y} x2={cx} y2={y + height} stroke={color} strokeWidth={1} />
      <rect x={cx - bodyW / 2} y={bodyTop} width={bodyW} height={bodyH} fill={color} />
    </g>
  );
}

function SignalsPanel({
  result,
  bars,
  t,
}: {
  result: RunResult;
  bars: { t: Float64Array; o: Float64Array; h: Float64Array; l: Float64Array; c: Float64Array };
  t: Dictionary;
}) {
  const intl = useIntlLocale();
  const n = result.ledger.t.length;
  const [center, setCenter] = useState(Math.max(0, n - Math.floor(SIGNAL_WINDOW / 2)));

  const { rows, markers } = useMemo(() => {
    const half = Math.floor(SIGNAL_WINDOW / 2);
    const from = Math.max(0, Math.min(center - half, n - SIGNAL_WINDOW));
    const to = Math.min(n, from + SIGNAL_WINDOW);
    const rows = [] as {
      time: number;
      o: number;
      h: number;
      l: number;
      c: number;
      hl: [number, number];
    }[];
    for (let i = from; i < to; i++) {
      rows.push({
        time: bars.t[i],
        o: bars.o[i],
        h: bars.h[i],
        l: bars.l[i],
        c: bars.c[i],
        hl: [bars.l[i], bars.h[i]],
      });
    }
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
            formatter={(value: unknown, name: string, item: { payload?: CandleRow }) => {
              if (name !== "OHLC" || !item?.payload) return [String(value), name];
              const r = item.payload;
              return [`O ${r.o} · H ${r.h} · L ${r.l} · C ${r.c}`, "OHLC"];
            }}
            contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--border)" }}
          />
          <Bar dataKey="hl" isAnimationActive={false} shape={CandleShape} name="OHLC" />
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

function TornadoPanel({ result, t }: { result: RunResult; t: Dictionary }) {
  const rows = result.tornado
    .flatMap((row) => [
      row.down != null ? { label: `${row.key} −1`, delta: row.down } : null,
      row.up != null ? { label: `${row.key} +1`, delta: row.up } : null,
    ])
    .filter((r): r is { label: string; delta: number } => r != null)
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));
  if (!rows.length) return null;
  const max = Math.max(...rows.map((r) => Math.abs(r.delta)), 1e-9);

  return (
    <Card>
      <CardHeader title={t.lab.tornadoTitle} subtitle={t.lab.tornadoSubtitle} />
      <ul className="space-y-2.5">
        {rows.map((row) => (
          <li key={row.label} className="flex items-center gap-3 text-sm">
            <span className="w-40 shrink-0 truncate font-mono text-xs text-muted">{row.label}</span>
            <div className="relative h-3 flex-1 rounded bg-surface-2">
              <div className="absolute inset-y-0 left-1/2 w-px bg-border" aria-hidden />
              <div
                className="absolute inset-y-0 rounded"
                style={{
                  left: row.delta < 0 ? `${50 - (Math.abs(row.delta) / max) * 48}%` : "50%",
                  width: `${(Math.abs(row.delta) / max) * 48}%`,
                  background: row.delta >= 0 ? "rgb(45 212 191 / 0.8)" : "rgb(248 113 113 / 0.8)",
                }}
              />
            </div>
            <span
              className={`tabular w-20 shrink-0 text-right font-mono text-xs ${signClass(row.delta)}`}
            >
              {fmtSignedPercent(row.delta, 1)}
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-xs leading-relaxed text-muted">{t.lab.tornadoNote}</p>
    </Card>
  );
}

function RegimePanel2({ result, t }: { result: RunResult; t: Dictionary }) {
  if (!result.regimes.length) return null;
  const label: Record<string, string> = {
    low: t.lab.regimeLow,
    mid: t.lab.regimeMid,
    high: t.lab.regimeHigh,
  };
  return (
    <Card>
      <CardHeader title={t.lab.regimeTitle} subtitle={t.lab.regimeSubtitle} />
      <div className="overflow-x-auto">
        <table className="w-full min-w-[440px] text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-muted">
              <th className="py-2 pr-4 font-medium">{t.lab.regimeCol}</th>
              <th className="py-2 pr-4 text-right font-medium">{t.explorer.metric.total_return}</th>
              <th className="py-2 pr-4 text-right font-medium">{t.explorer.metric.sharpe}</th>
              <th className="py-2 pr-4 text-right font-medium">{t.lab.regimeBars}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {result.regimes.map((row) => (
              <tr key={row.regime}>
                <td className="py-2 pr-4">{label[row.regime]}</td>
                <td className={`tabular py-2 pr-4 text-right ${signClass(row.totalReturn)}`}>
                  {fmtSignedPercent(row.totalReturn, 2)}
                </td>
                <td className="tabular py-2 pr-4 text-right">{fmtNumber(row.sharpe, 2)}</td>
                <td className="tabular py-2 pr-4 text-right">{fmtInt(row.nBars)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-4 text-xs leading-relaxed text-muted">{t.lab.regimeNote}</p>
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
    {
      name: t.lab.testBootstrap,
      desc: t.lab.testBootstrapDesc,
      pass: result.bootstrap.lo > 0,
      value: `IC95 [${fmtNumber(result.bootstrap.lo, 2)}, ${fmtNumber(result.bootstrap.hi, 2)}]`,
    },
    {
      name: t.lab.testStress,
      desc: t.lab.testStressDesc,
      pass: result.stress2xReturn > 0,
      value: fmtSignedPercent(result.stress2xReturn, 2),
    },
    {
      name: t.lab.testTwin,
      desc: t.lab.testTwinDesc,
      pass: result.twin != null && result.twin.totalReturn > 0,
      value: result.twin
        ? `${result.twin.symbol.replace("USDT", "")}: ${fmtSignedPercent(result.twin.totalReturn, 2)}`
        : "—",
    },
  ];
  const passed = tests.filter((test) => test.pass).length;

  return (
    <Card>
      <CardHeader
        title={`${t.lab.testsTitle} — ${passed}/${tests.length}`}
        subtitle={t.lab.testsSubtitle}
      />
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

function HistoryPanel({ t }: { t: Dictionary }) {
  const { entries, clear } = useHistory();
  if (!entries.length) return null;
  const bestSharpe = Math.max(...entries.map((e) => e.oosSharpe));

  return (
    <Card>
      <CardHeader
        title={t.lab.history.title}
        subtitle={t.lab.history.subtitle}
        right={
          <button
            type="button"
            onClick={clear}
            className="rounded-md border border-border px-3 py-1 text-xs text-muted hover:text-fg"
          >
            {t.lab.history.clear}
          </button>
        }
      />
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-muted">
              <th className="py-2 pr-4 font-medium">{t.lab.history.colFamily}</th>
              <th className="py-2 pr-4 font-medium">{t.lab.history.colParams}</th>
              <th className="py-2 pr-4 text-right font-medium">{t.lab.history.colReturn}</th>
              <th className="py-2 pr-4 text-right font-medium">Sharpe</th>
              <th className="py-2 pr-4 text-right font-medium">Max DD</th>
              <th className="py-2 pr-4 text-right font-medium">p</th>
              <th className="py-2 pr-0 text-right font-medium">{t.lab.history.colTests}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {entries.map((entry) => {
              const isBest = entry.oosSharpe === bestSharpe && entries.length > 1;
              return (
                <tr key={entry.ts} className={isBest ? "bg-accent/5" : undefined}>
                  <td className="py-2 pr-4">
                    <span className="font-medium">{entry.strategyId}</span>{" "}
                    <span className="text-xs text-muted">{entry.symbol.replace("USDT", "")}</span>
                    {isBest && (
                      <span className="ml-2 rounded border border-accent/40 bg-accent/10 px-1.5 py-0.5 text-[10px] text-accent">
                        {t.lab.history.best}
                      </span>
                    )}
                  </td>
                  <td className="max-w-[260px] truncate py-2 pr-4 font-mono text-[11px] text-muted">
                    {paramSummary(entry.params)}
                  </td>
                  <td className={`tabular py-2 pr-4 text-right ${signClass(entry.oosReturn)}`}>
                    {fmtSignedPercent(entry.oosReturn, 1)}
                  </td>
                  <td className="tabular py-2 pr-4 text-right">{fmtNumber(entry.oosSharpe, 2)}</td>
                  <td className="tabular py-2 pr-4 text-right text-negative">
                    {fmtSignedPercent(entry.maxDd, 1)}
                  </td>
                  <td className="tabular py-2 pr-4 text-right">{fmtNumber(entry.pValue, 3)}</td>
                  <td className="tabular py-2 pr-0 text-right">
                    {entry.passed}/{entry.totalTests}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-4 text-xs leading-relaxed text-muted">{t.lab.history.note}</p>
    </Card>
  );
}

const _historyEntryType: HistoryEntry | null = null;
void _historyEntryType;

/* ------------------------------------------------------------------------ */
/* Page                                                                      */
/* ------------------------------------------------------------------------ */

export default function LaboratorioPage() {
  const t = useI18n();
  const intl = useIntlLocale();
  const [symbol, setSymbol] = useState("BTCUSDT");
  const { data, error, isLoading } = useLabData(symbol);
  const twinSymbol = symbol === "BTCUSDT" ? "ETHUSDT" : "BTCUSDT";
  const { data: twinData } = useLabData(twinSymbol);

  const [strategyId, setStrategyId] = useState<StrategyId>("momentum");
  const def: StrategyDef = STRATEGIES.find((s) => s.id === strategyId) ?? STRATEGIES[0];

  const [values, setValues] = useState<Record<string, number | string>>(() =>
    Object.fromEntries(STRATEGIES[0].params.map((p) => [p.key, p.default]))
  );
  const [feeBps, setFeeBps] = useState(4);
  const [slipBps, setSlipBps] = useState(1);
  const [splitPct, setSplitPct] = useState(70);
  const [stopAtr, setStopAtr] = useState<number | null>(null);
  const [tpAtr, setTpAtr] = useState<number | null>(null);
  const [trailAtr, setTrailAtr] = useState<number | null>(null);
  const [maxBars, setMaxBars] = useState<number | null>(null);
  const [trendGate, setTrendGate] = useState(false);
  const [allowedRegimes, setAllowedRegimes] = useState<Regime[]>(["low", "mid", "high"]);
  const [running, setRunning] = useState(false);
  const { add: addAttempts } = useAttempts();
  const { add: addHistory } = useHistory();
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
        let side = def.run(data.bars, values, { funding: data.funding });
        // Composable gates and exit overlays (blocks B1/B2): gates first,
        // exits after, so an exit episode is defined on the gated stream.
        if (trendGate) side = applyTrendGate(side, data.bars, 200);
        if (allowedRegimes.length < 3) {
          side = applyRegimeGate(side, regimeLabels(data.bars), allowedRegimes);
        }
        side = applyExitOverlay(side, data.bars, {
          stopAtr,
          takeProfitAtr: tpAtr,
          trailingAtr: trailAtr,
          maxBars,
          atrWindow: 24,
        });
        const ledger = runBacktest(data.bars, side, costs, data.funding);
        const trades = extractTrades(ledger, data.bars);
        const bh = buyAndHold(data.bars, costs, data.funding);
        const n = ledger.net.length;
        const splitIdx = Math.max(1, Math.min(n - 2, Math.floor((splitPct / 100) * n)));
        const bhTrades = extractTrades(bh, data.bars);
        const nullTest = circularShiftTest(ledger, costs, splitIdx, n, N_SHIFTS, 42);
        addAttempts(1);

        // Extended battery (phase 8c): bootstrap CI, 2x cost stress, twin
        // asset, parameter tornado, and the causal volatility-regime split.
        const bootstrap = bootstrapSharpeCI(ledger.net, splitIdx, n, 200, 42);
        const stressLedger = runBacktest(
          data.bars,
          side,
          { feeBpsPerSide: feeBps * 2, slippageBpsPerSide: slipBps * 2 },
          data.funding
        );
        const stressMetrics = computeMetrics(stressLedger, [], splitIdx, n);
        let twin: { symbol: string; totalReturn: number } | null = null;
        if (twinData) {
          const twinSide = def.run(twinData.bars, values, { funding: twinData.funding });
          const twinLedger = runBacktest(twinData.bars, twinSide, costs, twinData.funding);
          const tn = twinLedger.net.length;
          const tSplit = Math.max(1, Math.min(tn - 2, Math.floor((splitPct / 100) * tn)));
          twin = {
            symbol: twinSymbol,
            totalReturn: computeMetrics(twinLedger, [], tSplit, tn).total_return,
          };
        }
        const oosReturn = computeMetrics(ledger, [], splitIdx, n).total_return;
        const tornado = perturbationTornado(
          def,
          values,
          data.bars,
          data.funding,
          costs,
          splitIdx,
          n,
          oosReturn
        );
        const regimes = regimeSplit(data.bars, ledger, splitIdx, n);

        const outMetrics = computeMetrics(ledger, trades, splitIdx, n);
        const bhOutMetrics = computeMetrics(bh, bhTrades, splitIdx, n);
        const passedCount = [
          outMetrics.total_return > 0,
          outMetrics.sharpe > 0,
          outMetrics.total_return > bhOutMetrics.total_return,
          nullTest.pValue < 0.05,
          bootstrap.lo > 0,
          stressMetrics.total_return > 0,
          twin != null && twin.totalReturn > 0,
        ].filter(Boolean).length;
        addHistory({
          ts: Date.now(),
          strategyId,
          symbol,
          params: { ...values },
          oosReturn: outMetrics.total_return,
          oosSharpe: outMetrics.sharpe,
          maxDd: outMetrics.max_drawdown,
          pValue: nullTest.pValue,
          passed: passedCount,
          totalTests: 7,
        });
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
          bootstrap,
          stress2xReturn: stressMetrics.total_return,
          twin,
          tornado,
          regimes,
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

            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                {t.lab.overlay.title}
              </p>
              <div className="mt-1.5 space-y-2">
                {(
                  [
                    [t.lab.overlay.stop, stopAtr, setStopAtr, 2, 0.25],
                    [t.lab.overlay.takeProfit, tpAtr, setTpAtr, 4, 0.25],
                    [t.lab.overlay.trailing, trailAtr, setTrailAtr, 3, 0.25],
                    [t.lab.overlay.maxBars, maxBars, setMaxBars, 48, 1],
                  ] as const
                ).map(([label, value, setter, def0, step]) => (
                  <label key={label} className="flex items-center gap-2 text-xs text-muted">
                    <input
                      type="checkbox"
                      checked={value != null}
                      onChange={(e) => setter(e.target.checked ? def0 : null)}
                      className="accent-[var(--accent)]"
                    />
                    <span className="w-36 shrink-0">{label}</span>
                    <input
                      type="number"
                      value={value ?? def0}
                      step={step}
                      min={step}
                      disabled={value == null}
                      onChange={(e) => setter(Number(e.target.value))}
                      className="w-20 rounded-md border border-border bg-surface-2 px-2 py-1 text-xs text-fg disabled:opacity-40"
                    />
                  </label>
                ))}
                <label className="flex items-center gap-2 text-xs text-muted">
                  <input
                    type="checkbox"
                    checked={trendGate}
                    onChange={(e) => setTrendGate(e.target.checked)}
                    className="accent-[var(--accent)]"
                  />
                  {t.lab.overlay.trendGate}
                </label>
                <div className="flex items-center gap-3 text-xs text-muted">
                  <span className="shrink-0">{t.lab.overlay.regimes}:</span>
                  {(["low", "mid", "high"] as const).map((r) => (
                    <label key={r} className="flex items-center gap-1">
                      <input
                        type="checkbox"
                        checked={allowedRegimes.includes(r)}
                        onChange={(e) =>
                          setAllowedRegimes((prev) =>
                            e.target.checked ? [...prev, r] : prev.filter((x) => x !== r)
                          )
                        }
                        className="accent-[var(--accent)]"
                      />
                      {t.lab.overlay[r]}
                    </label>
                  ))}
                </div>
                <p className="text-[10px] leading-relaxed text-muted/70">{t.lab.overlay.note}</p>
              </div>
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

      <HistoryPanel t={t} />

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
          <TornadoPanel result={result} t={t} />
          <RegimePanel2 result={result} t={t} />
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
