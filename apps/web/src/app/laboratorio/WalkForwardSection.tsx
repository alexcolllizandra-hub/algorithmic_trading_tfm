"use client";

// Multi-seed walk-forward section of the lab (phases 8a/8b): the study's
// protocol, miniaturised and runnable by anyone. Fold geometry comes from a
// committed study run; the search runs in a Web Worker with a progress bar;
// the result is the honest one — per-seed OOS curves (a fan, not a line)
// and per-fold test returns. Every evaluation feeds the session attempts
// counter shown alongside.

import { useEffect, useMemo, useRef, useState } from "react";
import useSWR from "swr";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardHeader } from "@/components/ui/Card";
import { useI18n } from "@/lib/i18n";
import { fmtNumber, fmtSignedPercent, signClass } from "@/lib/format";
import { useAttempts } from "@/lib/lab/attempts";
import type { LabDataset } from "@/lib/lab/data";
import type { CostModel } from "@/lib/lab/engine";
import type { StrategyId } from "@/lib/lab/strategies";
import { expectedMaxSharpe, type FoldsFile, type WalkForwardResult } from "@/lib/lab/walkforward";
import type { WfResponse } from "@/lib/lab/wf.worker";

const CHART = {
  grid: "rgb(var(--border))",
  axis: "rgb(var(--muted))",
  accent: "rgb(var(--accent))",
  negative: "rgb(248 113 113)",
};

const SEED_POOL = [42, 137, 271, 828, 1414];

const loadFolds = async (path: string): Promise<FoldsFile> => {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${response.status} ${path}`);
  return response.json();
};

export function WalkForwardSection({
  data,
  strategyId,
  costs,
}: {
  data: LabDataset | undefined;
  strategyId: StrategyId;
  costs: CostModel;
}) {
  const t = useI18n();
  const { data: foldsFile } = useSWR<FoldsFile>("/data/lab/folds.json", loadFolds, {
    revalidateOnFocus: false,
  });
  const { attempts, add } = useAttempts();

  const [budget, setBudget] = useState(50);
  const [nSeeds, setNSeeds] = useState(3);
  const [progress, setProgress] = useState<{ pct: number; seedIndex: number } | null>(null);
  const [results, setResults] = useState<WalkForwardResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const workerRef = useRef<Worker | null>(null);

  useEffect(() => () => workerRef.current?.terminate(), []);

  const run = () => {
    if (!data || !foldsFile) return;
    setResults(null);
    setError(null);
    setProgress({ pct: 0, seedIndex: 0 });

    const worker = new Worker(new URL("../../lib/lab/wf.worker.ts", import.meta.url));
    workerRef.current?.terminate();
    workerRef.current = worker;

    worker.onmessage = (event: MessageEvent<WfResponse>) => {
      const msg = event.data;
      if (msg.type === "progress") {
        const perSeed = 1 / msg.nSeeds;
        setProgress({
          pct: msg.seedIndex * perSeed + (msg.done / msg.total) * perSeed,
          seedIndex: msg.seedIndex,
        });
      } else if (msg.type === "done") {
        setResults(msg.results);
        setProgress(null);
        add(msg.results.reduce((total, r) => total + r.nEvaluations, 0));
        worker.terminate();
      } else {
        setError(msg.message);
        setProgress(null);
        worker.terminate();
      }
    };

    // Copies (not transfers): the page keeps using its own arrays.
    const buf = (arr: Float64Array) => arr.slice().buffer;
    worker.postMessage({
      type: "run",
      strategyId,
      bars: {
        t: buf(data.bars.t),
        o: buf(data.bars.o),
        h: buf(data.bars.h),
        l: buf(data.bars.l),
        c: buf(data.bars.c),
      },
      funding: { t: buf(data.funding.t), rate: buf(data.funding.rate) },
      folds: foldsFile.folds,
      costs,
      seeds: SEED_POOL.slice(0, nSeeds),
      budgetPerFold: budget,
    });
  };

  const fanRows = useMemo(() => {
    if (!results) return [];
    const longest = Math.max(...results.map((r) => r.oosCurve.length));
    const step = Math.max(1, Math.floor(longest / 500));
    const rows: Record<string, number>[] = [];
    for (let i = 0; i < longest; i += step) {
      const row: Record<string, number> = { i };
      for (const r of results) {
        row[`s${r.seed}`] = r.oosCurve[Math.min(i, r.oosCurve.length - 1)];
      }
      rows.push(row);
    }
    return rows;
  }, [results]);

  const foldRows = useMemo(() => {
    if (!results) return [];
    const byFold = new Map<number, { label: string; values: number[] }>();
    for (const r of results) {
      for (const f of r.folds) {
        const entry = byFold.get(f.fold) ?? { label: f.testStart.slice(0, 7), values: [] };
        entry.values.push(f.testReturn);
        byFold.set(f.fold, entry);
      }
    }
    return [...byFold.entries()]
      .sort((a, b) => a[0] - b[0])
      .map(([fold, e]) => ({
        fold,
        label: e.label,
        mean: e.values.reduce((a, b) => a + b, 0) / e.values.length,
      }));
  }, [results]);

  const nBars = data?.bars.t.length ?? 0;
  const chanceSharpe = expectedMaxSharpe(Math.max(1, attempts), Math.max(2, nBars));
  const bestOos = results ? Math.max(...results.map((r) => r.oosSharpe)) : null;

  return (
    <Card>
      <CardHeader title={t.lab.wf.title} subtitle={t.lab.wf.subtitle} />

      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <div className="space-y-4">
          <label className="block text-xs text-muted">
            {t.lab.wf.budget}: <span className="tabular font-medium text-fg">{budget}</span>
            <input
              type="range"
              min={10}
              max={100}
              step={10}
              value={budget}
              onChange={(event) => setBudget(Number(event.target.value))}
              className="mt-1 w-full accent-accent"
            />
          </label>
          <label className="block text-xs text-muted">
            {t.lab.wf.seeds}: <span className="tabular font-medium text-fg">{nSeeds}</span>
            <input
              type="range"
              min={1}
              max={5}
              value={nSeeds}
              onChange={(event) => setNSeeds(Number(event.target.value))}
              className="mt-1 w-full accent-accent"
            />
          </label>
          <button
            type="button"
            onClick={run}
            disabled={!data || !foldsFile || progress != null}
            className="w-full rounded-md bg-accent px-4 py-2.5 text-sm font-semibold text-white transition-opacity disabled:opacity-50"
          >
            {progress != null ? t.lab.wf.running : t.lab.wf.run}
          </button>

          {progress != null && (
            <div>
              <div className="h-2 overflow-hidden rounded-full bg-surface-2">
                <div
                  className="h-2 rounded-full bg-accent transition-all"
                  style={{ width: `${Math.round(progress.pct * 100)}%` }}
                />
              </div>
              <p className="mt-1.5 text-[11px] text-muted">
                {t.lab.wf.seedProgress
                  .replace("{i}", String(progress.seedIndex + 1))
                  .replace("{n}", String(nSeeds))}{" "}
                · {Math.round(progress.pct * 100)}%
              </p>
            </div>
          )}
          {error && <p className="text-xs text-negative">{error}</p>}

          {foldsFile && (
            <p className="text-[11px] leading-relaxed text-muted/80">
              {t.lab.wf.foldsNote
                .replace("{n}", String(foldsFile.n_folds))
                .replace("{run}", foldsFile.source_run.split("/").pop() ?? "")}
            </p>
          )}

          {/* The attempts counter: selection bias applied to the visitor. */}
          <div className="rounded-md border border-warn/40 bg-warn/5 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-warn">
              {t.lab.attempts.title}
            </p>
            <p className="tabular mt-2 text-2xl font-semibold">{attempts.toLocaleString()}</p>
            <p className="mt-1 text-[11px] leading-relaxed text-muted">
              {t.lab.attempts.body.replace("{sharpe}", fmtNumber(chanceSharpe, 2))}
            </p>
            {bestOos != null && (
              <p className="mt-2 text-[11px] leading-relaxed text-muted">
                {t.lab.attempts.compare
                  .replace("{best}", fmtNumber(bestOos, 2))
                  .replace("{chance}", fmtNumber(chanceSharpe, 2))}
              </p>
            )}
          </div>
        </div>

        <div className="min-w-0 space-y-6">
          {results ? (
            <>
              <div>
                <p className="rule-label mb-3 text-accent">{t.lab.wf.fanTitle}</p>
                <ResponsiveContainer width="100%" height={240}>
                  <LineChart data={fanRows} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                    <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="i" hide />
                    <YAxis
                      stroke={CHART.axis}
                      tick={{ fontSize: 11 }}
                      width={48}
                      tickFormatter={(v) => `${Number(v).toFixed(2)}×`}
                      domain={["auto", "auto"]}
                    />
                    <ReferenceLine y={1} stroke={CHART.axis} strokeDasharray="4 3" />
                    <Tooltip
                      formatter={(value: number) => `${Number(value).toFixed(3)}×`}
                      contentStyle={{
                        background: "rgb(var(--surface-2))",
                        border: "1px solid rgb(var(--border))",
                      }}
                    />
                    {results.map((r) => (
                      <Line
                        key={r.seed}
                        dataKey={`s${r.seed}`}
                        name={`seed ${r.seed}`}
                        dot={false}
                        stroke={CHART.accent}
                        strokeOpacity={0.6}
                        strokeWidth={1.4}
                        isAnimationActive={false}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
                <ul className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">
                  {results.map((r) => (
                    <li key={r.seed} className="tabular">
                      seed {r.seed}:{" "}
                      <span className={signClass(r.oosTotalReturn)}>
                        {fmtSignedPercent(r.oosTotalReturn, 1)}
                      </span>{" "}
                      · Sharpe {fmtNumber(r.oosSharpe, 2)}
                    </li>
                  ))}
                </ul>
              </div>

              <div>
                <p className="rule-label mb-3 text-accent">{t.lab.wf.foldsTitle}</p>
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={foldRows} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                    <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" vertical={false} />
                    <XAxis
                      dataKey="label"
                      stroke={CHART.axis}
                      tick={{ fontSize: 9 }}
                      interval={1}
                    />
                    <YAxis
                      stroke={CHART.axis}
                      tick={{ fontSize: 11 }}
                      width={44}
                      tickFormatter={(v) => `${(Number(v) * 100).toFixed(0)}%`}
                    />
                    <Tooltip
                      formatter={(value: number) => `${(Number(value) * 100).toFixed(1)}%`}
                      contentStyle={{
                        background: "rgb(var(--surface-2))",
                        border: "1px solid rgb(var(--border))",
                      }}
                      cursor={{ fill: "rgb(127 127 127 / 0.06)" }}
                    />
                    <ReferenceLine y={0} stroke={CHART.axis} />
                    <Bar dataKey="mean" isAnimationActive={false} radius={[2, 2, 0, 0]}>
                      {foldRows.map((row) => (
                        <Cell
                          key={row.fold}
                          fill={row.mean >= 0 ? "rgb(45 212 191)" : CHART.negative}
                          fillOpacity={0.85}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <p className="rounded-md border border-warn/40 bg-warn/10 px-4 py-3 text-xs leading-relaxed text-warn">
                {t.lab.wf.disclaimer}
              </p>
            </>
          ) : (
            <p className="text-sm leading-relaxed text-muted">{t.lab.wf.explainer}</p>
          )}
        </div>
      </div>
    </Card>
  );
}
