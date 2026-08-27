"use client";

// The efficient-market argument, measured instead of asserted.
//
// Both series come from `public/data/evidence.json`, written by
// `scripts/export_web_evidence.py` from the same development-partition ledgers
// the study used. Nothing here is simulated.

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

import { LANDING_CHART } from "@/components/landing/charts/palette";
import type { TurnoverPoint } from "@/lib/evidence";

/**
 * Round-trip cost, in basis points, at which the Sharpe ratio reaches zero.
 *
 * Found by linear interpolation between the two grid points that bracket the
 * crossing. Returns null when the curve never crosses, so the caller can say
 * nothing rather than extrapolate past the measured range.
 */
export function breakEvenBps(rows: { round_trip_bps: number | null; sharpe: number | null }[]) {
  const points = rows
    .filter(
      (r): r is { round_trip_bps: number; sharpe: number } =>
        r.round_trip_bps != null && r.sharpe != null
    )
    .sort((a, b) => a.round_trip_bps - b.round_trip_bps);

  for (let i = 1; i < points.length; i += 1) {
    const previous = points[i - 1];
    const current = points[i];
    if (previous.sharpe > 0 && current.sharpe <= 0) {
      const span = previous.sharpe - current.sharpe;
      if (span === 0) return current.round_trip_bps;
      const fraction = previous.sharpe / span;
      return (
        previous.round_trip_bps + fraction * (current.round_trip_bps - previous.round_trip_bps)
      );
    }
  }
  return null;
}

function CostTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { value?: number }[];
  label?: number | string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border border-border bg-surface-2 px-3 py-2 text-xs">
      <p className="font-medium">{Number(label).toFixed(0)} bps por vuelta</p>
      <p className="tabular mt-0.5 text-muted">Sharpe {Number(payload[0]?.value).toFixed(3)}</p>
    </div>
  );
}

function WedgeTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload?: TurnoverPoint }[];
}) {
  const row = payload?.[0]?.payload;
  if (!active || !row) return null;
  return (
    <div className="rounded-md border border-border bg-surface-2 px-3 py-2 text-xs">
      <p className="font-medium">
        Medias {row.fast} / {row.slow} h
      </p>
      <p className="tabular mt-0.5 text-muted">Rotación {row.turnover?.toFixed(0)}</p>
      <p className="tabular text-muted">Bruto {row.gross?.toFixed(3)}</p>
      <p className="tabular text-muted">Neto {row.net?.toFixed(3)}</p>
    </div>
  );
}

export function CostErosionChart({
  rows,
}: {
  rows: { round_trip_bps: number | null; sharpe: number | null }[];
}) {
  const data = rows
    .filter((r) => r.round_trip_bps != null && r.sharpe != null)
    .sort((a, b) => (a.round_trip_bps ?? 0) - (b.round_trip_bps ?? 0));
  const crossing = breakEvenBps(rows);

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 24, left: 4 }}>
        <CartesianGrid stroke={LANDING_CHART.grid} strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="round_trip_bps"
          type="number"
          domain={["dataMin", "dataMax"]}
          stroke={LANDING_CHART.axis}
          tick={{ fontSize: 11 }}
          tickFormatter={(v) => `${v}`}
          label={{
            value: "coste por vuelta (bps)",
            position: "insideBottom",
            offset: -14,
            fill: LANDING_CHART.axis,
            fontSize: 11,
          }}
        />
        <YAxis
          stroke={LANDING_CHART.axis}
          tick={{ fontSize: 11 }}
          width={46}
          tickFormatter={(v) => Number(v).toFixed(1)}
        />
        <Tooltip content={<CostTooltip />} />
        <ReferenceLine y={0} stroke={LANDING_CHART.axis} strokeDasharray="4 3" />
        {crossing != null && (
          <ReferenceLine
            x={crossing}
            stroke="rgb(248 113 113)"
            strokeDasharray="4 3"
            label={{
              value: `${crossing.toFixed(0)} bps`,
              position: "top",
              fill: "rgb(248 113 113)",
              fontSize: 11,
            }}
          />
        )}
        <Line
          type="monotone"
          dataKey="sharpe"
          stroke={LANDING_CHART.accent}
          strokeWidth={2.5}
          dot={{ r: 3, fill: LANDING_CHART.accent }}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function TurnoverWedgeChart({ grid }: { grid: TurnoverPoint[] }) {
  const data = grid.filter((p) => p.turnover != null && p.gross != null && p.net != null);

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ScatterChart margin={{ top: 8, right: 16, bottom: 24, left: 4 }}>
        <CartesianGrid stroke={LANDING_CHART.grid} strokeDasharray="3 3" />
        <XAxis
          dataKey="turnover"
          type="number"
          domain={["dataMin", "dataMax"]}
          stroke={LANDING_CHART.axis}
          tick={{ fontSize: 11 }}
          label={{
            value: "rotación (operaciones)",
            position: "insideBottom",
            offset: -14,
            fill: LANDING_CHART.axis,
            fontSize: 11,
          }}
        />
        <YAxis
          type="number"
          stroke={LANDING_CHART.axis}
          tick={{ fontSize: 11 }}
          width={46}
          tickFormatter={(v) => Number(v).toFixed(1)}
        />
        <ZAxis range={[46, 46]} />
        <Tooltip content={<WedgeTooltip />} cursor={{ strokeDasharray: "3 3" }} />
        <ReferenceLine y={0} stroke={LANDING_CHART.axis} strokeDasharray="4 3" />
        <Scatter
          data={data}
          dataKey="gross"
          fill={LANDING_CHART.secondary}
          isAnimationActive={false}
        />
        <Scatter data={data} dataKey="net" fill="rgb(248 113 113)" isAnimationActive={false} />
      </ScatterChart>
    </ResponsiveContainer>
  );
}
