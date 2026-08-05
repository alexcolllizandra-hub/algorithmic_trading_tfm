"use client";

import type { TimelineFold, TimelineResponse } from "@/lib/api-types";
import { fmtDate } from "@/lib/format";
import { es } from "@/lib/i18n/es";

const COLORS = {
  development: "#3b82f6",
  pilot: "#8b5cf6",
  train: "#22c55e",
  validation: "#eab308",
  test: "#f97316",
  holdout: "#ef4444",
  unused: "#64748b",
};

function parseTs(value: string | null | undefined): number | null {
  if (!value) return null;
  const t = Date.parse(value);
  return Number.isNaN(t) ? null : t;
}

function pct(min: number, max: number, t: number): number {
  if (max <= min) return 0;
  return ((t - min) / (max - min)) * 100;
}

const AXIS_W = 760;

function Span({
  x,
  w,
  color,
  label,
  title,
  offsetX = 0,
}: {
  x: number;
  w: number;
  color: string;
  label?: string;
  title: string;
  offsetX?: number;
}) {
  if (w <= 0) return null;
  const px = offsetX + (x / 100) * AXIS_W;
  const pw = (w / 100) * AXIS_W;
  return (
    <g>
      <rect x={px} y={0} width={pw} height={16} fill={color} opacity={0.85} rx={2}>
        <title>{title}</title>
      </rect>
      {w > 8 && label && pw > 36 && (
        <text x={px + pw / 2} y={11} textAnchor="middle" className="fill-white text-[8px]">
          {label}
        </text>
      )}
    </g>
  );
}

function foldSegments(
  fold: TimelineFold,
  tMin: number,
  tMax: number
): { train: [number, number]; val: [number, number]; test: [number, number] } {
  const toPct = (start: string | null, end: string | null): [number, number] => {
    const s = parseTs(start);
    const e = parseTs(end);
    if (s == null || e == null) return [0, 0];
    return [pct(tMin, tMax, s), pct(tMin, tMax, e) - pct(tMin, tMax, s)];
  };
  return {
    train: toPct(fold.train_start, fold.train_end),
    val: toPct(fold.val_start, fold.val_end),
    test: toPct(fold.test_start, fold.test_end),
  };
}

export function TimelineChart({ data }: { data: TimelineResponse }) {
  const holdoutStart = parseTs(data.holdout_start);
  const devStart = parseTs(data.development_start);
  const devEnd = parseTs(data.development_end) ?? holdoutStart;
  const pilotStart = parseTs(data.pilot_used_start);
  const pilotEnd = parseTs(data.pilot_used_end);

  const tMin = devStart ?? pilotStart ?? holdoutStart ?? Date.now();
  const tMax = holdoutStart ?? devEnd ?? tMin + 1;

  const devW =
    devStart != null && devEnd != null ? pct(tMin, tMax, devEnd) - pct(tMin, tMax, devStart) : 0;
  const devX = devStart != null ? pct(tMin, tMax, devStart) : 0;

  const pilotW =
    pilotStart != null && pilotEnd != null
      ? pct(tMin, tMax, pilotEnd) - pct(tMin, tMax, pilotStart)
      : 0;
  const pilotX = pilotStart != null ? pct(tMin, tMax, pilotStart) : 0;

  const holdoutW = holdoutStart != null ? 100 - pct(tMin, tMax, holdoutStart) : 0;
  const holdoutX = holdoutStart != null ? pct(tMin, tMax, holdoutStart) : 100;

  const foldRowHeight = 22;
  const foldBaseY = 60;

  return (
    <div className="w-full overflow-x-auto">
      <svg
        viewBox={`0 0 800 ${foldBaseY + data.folds.length * foldRowHeight + 40}`}
        className="w-full min-w-[640px]"
      >
        <text x={0} y={14} className="fill-fg text-[11px] font-medium">
          {es.timeline.title}
        </text>
        <text x={0} y={26} className="fill-muted text-[9px]">
          {fmtDate(data.development_start)} — holdout {fmtDate(data.holdout_start)}
        </text>

        <g transform="translate(0, 32)">
          <line
            x1={0}
            y1={20}
            x2={AXIS_W}
            y2={20}
            stroke="currentColor"
            className="text-border"
            strokeWidth={1}
          />
          <g transform="translate(0, 24)">
            <Span
              x={devX}
              w={devW}
              color={COLORS.development}
              label={es.timeline.development}
              title={`${es.timeline.development}: ${fmtDate(data.development_start)} → ${fmtDate(data.development_end)}`}
            />
            <Span
              x={pilotX}
              w={pilotW}
              color={COLORS.pilot}
              label={es.timeline.pilotUsed}
              title={`${es.timeline.pilotUsed}: ${fmtDate(data.pilot_used_start)} → ${fmtDate(data.pilot_used_end)} (${data.pilot_used_pct_of_dev ?? "—"}% dev)`}
            />
            <Span
              x={holdoutX}
              w={holdoutW}
              color={COLORS.holdout}
              label={es.timeline.holdout}
              title={`${es.timeline.holdout}: desde ${fmtDate(data.holdout_start)}`}
            />
          </g>
        </g>

        {data.folds.map((fold, i) => {
          const y = foldBaseY + i * foldRowHeight;
          const seg = foldSegments(fold, tMin, tMax);
          return (
            <g key={fold.index} transform={`translate(0, ${y})`}>
              <text x={0} y={12} className="fill-muted text-[9px]">
                Fold {fold.index}
              </text>
              <g transform="translate(40, 0)">
                <Span
                  x={seg.train[0]}
                  w={seg.train[1]}
                  color={COLORS.train}
                  label={es.timeline.train}
                  title={`${es.timeline.train}: ${fmtDate(fold.train_start)} → ${fmtDate(fold.train_end)}`}
                  offsetX={0}
                />
                <Span
                  x={seg.val[0]}
                  w={seg.val[1]}
                  color={COLORS.validation}
                  label={es.timeline.validation}
                  title={`${es.timeline.validation}: ${fmtDate(fold.val_start)} → ${fmtDate(fold.val_end)}`}
                />
                <Span
                  x={seg.test[0]}
                  w={seg.test[1]}
                  color={COLORS.test}
                  label={es.timeline.test}
                  title={`${es.timeline.test}: ${fmtDate(fold.test_start)} → ${fmtDate(fold.test_end)} · purge ${fold.purge_bars ?? 0} · embargo ${fold.embargo_bars ?? 0}`}
                />
              </g>
            </g>
          );
        })}

        <g transform={`translate(0, ${foldBaseY + data.folds.length * foldRowHeight + 8})`}>
          {[
            [es.timeline.development, COLORS.development],
            [es.timeline.pilotUsed, COLORS.pilot],
            [es.timeline.train, COLORS.train],
            [es.timeline.validation, COLORS.validation],
            [es.timeline.test, COLORS.test],
            [es.timeline.holdout, COLORS.holdout],
          ].map(([label, color], i) => (
            <g key={String(label)} transform={`translate(${i * 120}, 0)`}>
              <rect width={10} height={10} fill={color as string} rx={1} />
              <text x={14} y={9} className="fill-muted text-[9px]">
                {label}
              </text>
            </g>
          ))}
        </g>
      </svg>
    </div>
  );
}
