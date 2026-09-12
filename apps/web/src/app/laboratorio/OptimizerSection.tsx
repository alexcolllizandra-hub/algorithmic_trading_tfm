"use client";

// Step 4 of the lab: a random search over the family's study grid, scored on
// the in-sample window exactly like a naive optimiser would, and then shown
// against the out-of-sample window it never saw. The point is the gap: the
// in-sample winner is the right tail of N tries, so it is compared with the
// Sharpe that N no-skill tries would reach by chance, and the rank correlation
// between the two windows says whether the in-sample ranking predicts anything.

import { useMemo, useRef, useState } from "react";
import {
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardHeader } from "@/components/ui/Card";
import { useI18n } from "@/lib/i18n";
import { fmtInt, fmtNumber, fmtSignedPercent, signClass } from "@/lib/format";
import { useAttempts } from "@/lib/lab/attempts";
import type { LabDataset } from "@/lib/lab/data";
import { computeMetrics, runBacktest, type CostModel } from "@/lib/lab/engine";
import { paramSummary } from "@/lib/lab/history";
import type { StrategyDef } from "@/lib/lab/strategies";
import { expectedMaxSharpe, mulberry32, sampleCandidate } from "@/lib/lab/walkforward";

const CHART = {
  grid: "rgb(var(--border))",
  axis: "rgb(var(--muted))",
  accent: "rgb(var(--accent))",
  point: "rgb(127 127 127 / 0.55)",
  winner: "rgb(217 94 0)",
};

const BATCH = 5;
const TRIAL_OPTIONS = [25, 50, 100, 200];

export interface OptimizerRow {
  id: number;
  values: Record<string, number | string>;
  isSharpe: number;
  isReturn: number;
  oosSharpe: number;
  oosReturn: number;
  oosMaxDd: number;
  nTrades: number;
}

function paramHash(values: Record<string, number | string>): string {
  return Object.keys(values)
    .sort()
    .map((k) => `${k}=${values[k]}`)
    .join("|");
}

/** Spearman rank correlation; ties get their average rank. */
function spearman(xs: number[], ys: number[]): number {
  const n = xs.length;
  if (n < 3) return 0;
  const rank = (arr: number[]) => {
    const idx = arr.map((v, i) => [v, i] as const).sort((a, b) => a[0] - b[0]);
    const out = new Array<number>(n);
    let i = 0;
    while (i < n) {
      let j = i;
      while (j + 1 < n && idx[j + 1][0] === idx[i][0]) j++;
      const r = (i + j) / 2 + 1;
      for (let k = i; k <= j; k++) out[idx[k][1]] = r;
      i = j + 1;
    }
    return out;
  };
  const rx = rank(xs);
  const ry = rank(ys);
  const mx = rx.reduce((a, b) => a + b, 0) / n;
  const my = ry.reduce((a, b) => a + b, 0) / n;
  let num = 0;
  let dx = 0;
  let dy = 0;
  for (let i = 0; i < n; i++) {
    num += (rx[i] - mx) * (ry[i] - my);
    dx += (rx[i] - mx) ** 2;
    dy += (ry[i] - my) ** 2;
  }
  return dx > 0 && dy > 0 ? num / Math.sqrt(dx * dy) : 0;
}

function Tile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-md border border-border bg-surface-2 px-4 py-3">
      <p className="text-xs text-muted">{label}</p>
      <p className="tabular mt-1 text-xl font-semibold">{value}</p>
      {hint && <p className="mt-0.5 text-[11px] text-muted/80">{hint}</p>}
    </div>
  );
}

export function OptimizerSection({
  data,
  def,
  costs,
  splitPct,
  onLoad,
  onDone,
}: {
  data: LabDataset | undefined;
  def: StrategyDef;
  costs: CostModel;
  splitPct: number;
  onLoad: (values: Record<string, number | string>) => void;
  onDone?: (rows: OptimizerRow[]) => void;
}) {
  const t = useI18n();
  const { add: addAttempts } = useAttempts();
  const [nTrials, setNTrials] = useState(100);
  const [seed, setSeed] = useState(42);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const [rows, setRows] = useState<OptimizerRow[]>([]);
  const [family, setFamily] = useState<string | null>(null);
  const cancelRef = useRef(false);

  const run = () => {
    if (!data || running) return;
    const bars = data.bars;
    const n = bars.t.length;
    const splitIdx = Math.max(1, Math.min(n - 2, Math.floor((splitPct / 100) * n)));
    const rand = mulberry32(seed);
    const seen = new Set<string>();
    const targets: Record<string, number | string>[] = [];
    // The grid can be smaller than nTrials; the guard bounds the rejection loop.
    for (let guard = 0; targets.length < nTrials && guard < nTrials * 25; guard++) {
      const v = sampleCandidate(def.params, rand);
      const h = paramHash(v);
      if (seen.has(h)) continue;
      seen.add(h);
      targets.push(v);
    }
    cancelRef.current = false;
    setRunning(true);
    setRows([]);
    setFamily(def.id);
    setProgress({ done: 0, total: targets.length });
    const out: OptimizerRow[] = [];
    let i = 0;
    const step = () => {
      if (cancelRef.current) {
        setRunning(false);
        return;
      }
      const end = Math.min(i + BATCH, targets.length);
      for (; i < end; i++) {
        const side = def.run(bars, targets[i], { funding: data.funding });
        const ledger = runBacktest(bars, side, costs, data.funding);
        const inS = computeMetrics(ledger, [], 0, splitIdx);
        const out_ = computeMetrics(ledger, [], splitIdx, n);
        out.push({
          id: i,
          values: targets[i],
          isSharpe: inS.sharpe,
          isReturn: inS.total_return,
          oosSharpe: out_.sharpe,
          oosReturn: out_.total_return,
          oosMaxDd: out_.max_drawdown,
          nTrades: out_.n_trades,
        });
      }
      setProgress({ done: i, total: targets.length });
      if (i < targets.length) {
        setTimeout(step, 0);
      } else {
        setRows(out);
        addAttempts(out.length);
        setRunning(false);
        onDone?.(out);
      }
    };
    // Yield one frame so the running state paints before the compute burst.
    setTimeout(step, 30);
  };

  const summary = useMemo(() => {
    if (!rows.length || !data) return null;
    const n = data.bars.t.length;
    const splitIdx = Math.max(1, Math.min(n - 2, Math.floor((splitPct / 100) * n)));
    const byIs = [...rows].sort((a, b) => b.isSharpe - a.isSharpe);
    const winner = byIs[0];
    return {
      winner,
      top: byIs.slice(0, 10),
      noise: expectedMaxSharpe(rows.length, splitIdx),
      rho: spearman(
        rows.map((r) => r.isSharpe),
        rows.map((r) => r.oosSharpe)
      ),
    };
  }, [rows, data, splitPct]);

  const points = useMemo(
    () => rows.map((r) => ({ x: r.isSharpe, y: r.oosSharpe, id: r.id })),
    [rows]
  );

  const o = t.lab.optimizer;
  const stale = family != null && family !== def.id;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader title={o.title} subtitle={o.subtitle} />
        <div className="flex flex-wrap items-end gap-4">
          <label className="block text-xs text-muted">
            {o.trials}
            <select
              value={nTrials}
              onChange={(e) => setNTrials(Number(e.target.value))}
              disabled={running}
              className="mt-1 block rounded-md border border-border bg-surface-2 px-3 py-2 text-sm text-fg"
            >
              {TRIAL_OPTIONS.map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-xs text-muted">
            {o.seed}
            <input
              type="number"
              value={seed}
              min={0}
              step={1}
              disabled={running}
              onChange={(e) => setSeed(Number(e.target.value))}
              className="mt-1 block w-28 rounded-md border border-border bg-surface-2 px-3 py-2 text-sm text-fg"
            />
          </label>
          {running ? (
            <button
              type="button"
              onClick={() => {
                cancelRef.current = true;
              }}
              className="rounded-md border border-border px-4 py-2 text-sm text-muted hover:text-fg"
            >
              {o.cancel}
            </button>
          ) : (
            <button
              type="button"
              onClick={run}
              disabled={!data}
              className="rounded-md px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
              style={{ background: CHART.accent }}
            >
              {o.run}
            </button>
          )}
          <span className="text-xs text-muted">
            {t.lab.strategyLabel}: <span className="font-mono text-fg">{def.id}</span>
          </span>
        </div>
        {running && (
          <div className="mt-4">
            <div className="h-2 w-full overflow-hidden rounded bg-surface-2">
              <div
                className="h-full transition-[width]"
                style={{
                  width: `${progress.total ? (100 * progress.done) / progress.total : 0}%`,
                  background: CHART.accent,
                }}
              />
            </div>
            <p className="mt-1 text-xs text-muted">
              {o.running}{" "}
              {o.progress
                .replace("{done}", fmtInt(progress.done))
                .replace("{total}", fmtInt(progress.total))}
            </p>
          </div>
        )}
        <p className="mt-3 text-[11px] leading-relaxed text-muted/80">{o.overlaysNote}</p>
        {!rows.length && !running && <p className="mt-3 text-sm text-muted">{o.empty}</p>}
        {stale && !running && (
          <p className="mt-3 text-sm text-warn">{o.stale.replace("{family}", family ?? "")}</p>
        )}
      </Card>

      {summary && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            <Tile label={o.tileEvaluated} value={fmtInt(rows.length)} />
            <Tile label={o.tileBestIs} value={fmtNumber(summary.winner.isSharpe, 2)} />
            <Tile
              label={o.tileBestOos}
              value={fmtNumber(summary.winner.oosSharpe, 2)}
              hint={fmtSignedPercent(summary.winner.oosReturn, 1)}
            />
            <Tile
              label={o.tileNoise}
              value={fmtNumber(summary.noise, 2)}
              hint={o.noiseNote.replace("{n}", fmtInt(rows.length))}
            />
            <Tile label={o.tileRho} value={fmtNumber(summary.rho, 2)} />
          </div>

          <Card>
            <CardHeader title={o.scatterTitle} subtitle={o.scatterSubtitle} />
            <ResponsiveContainer width="100%" height={320}>
              <ScatterChart margin={{ top: 12, right: 16, bottom: 24, left: 8 }}>
                <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" />
                <XAxis
                  type="number"
                  dataKey="x"
                  name={o.xAxis}
                  stroke={CHART.axis}
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v: number) => fmtNumber(v, 1)}
                  label={{ value: o.xAxis, position: "insideBottom", offset: -12, fontSize: 11 }}
                />
                <YAxis
                  type="number"
                  dataKey="y"
                  name={o.yAxis}
                  stroke={CHART.axis}
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v: number) => fmtNumber(v, 1)}
                  width={48}
                  label={{ value: o.yAxis, angle: -90, position: "insideLeft", fontSize: 11 }}
                />
                <ReferenceLine x={0} stroke={CHART.axis} />
                <ReferenceLine y={0} stroke={CHART.axis} />
                <Tooltip
                  cursor={{ strokeDasharray: "3 3" }}
                  contentStyle={{
                    background: "rgb(var(--surface-2))",
                    border: "1px solid rgb(var(--border))",
                    fontSize: 12,
                  }}
                  formatter={(value: number) => fmtNumber(value, 2)}
                />
                <Scatter data={points} isAnimationActive={false}>
                  {points.map((p) => (
                    <Cell
                      key={p.id}
                      fill={p.id === summary.winner.id ? CHART.winner : CHART.point}
                      r={p.id === summary.winner.id ? 7 : 4}
                    />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
            <p className="mt-2 text-xs text-muted">
              <span
                className="mr-1 inline-block h-2.5 w-2.5 rounded-full align-middle"
                style={{ background: CHART.winner }}
              />
              {o.winner}
            </p>
          </Card>

          <Card>
            <CardHeader title={o.tableTitle} />
            <div className="overflow-x-auto">
              <table className="w-full min-w-[820px] text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-muted">
                    <th className="py-2 pr-3 font-medium">{o.colRank}</th>
                    <th className="py-2 pr-3 font-medium">{o.colParams}</th>
                    <th className="py-2 pr-3 text-right font-medium">{o.colIs}</th>
                    <th className="py-2 pr-3 text-right font-medium">{o.colIsRet}</th>
                    <th className="py-2 pr-3 text-right font-medium">{o.colOos}</th>
                    <th className="py-2 pr-3 text-right font-medium">{o.colOosRet}</th>
                    <th className="py-2 pr-3 text-right font-medium">{o.colDd}</th>
                    <th className="py-2 pr-3 text-right font-medium">{o.colTrades}</th>
                    <th className="py-2 pr-0 text-right font-medium" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {summary.top.map((r, i) => (
                    <tr key={r.id} className={i === 0 ? "bg-accent/5" : undefined}>
                      <td className="tabular py-2 pr-3 text-muted">{i + 1}</td>
                      <td className="max-w-[280px] truncate py-2 pr-3 font-mono text-[11px] text-muted">
                        {paramSummary(r.values)}
                      </td>
                      <td className="tabular py-2 pr-3 text-right">{fmtNumber(r.isSharpe, 2)}</td>
                      <td className={`tabular py-2 pr-3 text-right ${signClass(r.isReturn)}`}>
                        {fmtSignedPercent(r.isReturn, 1)}
                      </td>
                      <td className={`tabular py-2 pr-3 text-right ${signClass(r.oosSharpe)}`}>
                        {fmtNumber(r.oosSharpe, 2)}
                      </td>
                      <td className={`tabular py-2 pr-3 text-right ${signClass(r.oosReturn)}`}>
                        {fmtSignedPercent(r.oosReturn, 1)}
                      </td>
                      <td className="tabular py-2 pr-3 text-right text-negative">
                        {fmtSignedPercent(r.oosMaxDd, 1)}
                      </td>
                      <td className="tabular py-2 pr-3 text-right">{fmtInt(r.nTrades)}</td>
                      <td className="py-2 pr-0 text-right">
                        <button
                          type="button"
                          onClick={() => onLoad(r.values)}
                          className="rounded border border-border px-2 py-0.5 text-xs text-accent hover:border-accent/50"
                        >
                          {o.load}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-4 text-xs leading-relaxed text-muted">{o.note}</p>
          </Card>
        </>
      )}
    </div>
  );
}
