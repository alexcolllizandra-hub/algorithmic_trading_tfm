"use client";

// The single most important chart on the site: what a strategy scored when it
// was CHOSEN, against what it went on to EARN. Drawn as plain SVG because it is
// 700 static points and a straight line — a charting library would add weight
// without adding anything a reader can see.

import { LANDING_CHART } from "@/components/landing/charts/palette";

const W = 560;
const H = 440;
const PAD = { top: 16, right: 16, bottom: 46, left: 52 };
const LO = -6;
const HI = 8;

function sx(v: number): number {
  const clamped = Math.max(LO, Math.min(HI, v));
  return PAD.left + ((clamped - LO) / (HI - LO)) * (W - PAD.left - PAD.right);
}

function sy(v: number): number {
  const clamped = Math.max(LO, Math.min(HI, v));
  return H - PAD.bottom - ((clamped - LO) / (HI - LO)) * (H - PAD.top - PAD.bottom);
}

const TICKS = [-6, -4, -2, 0, 2, 4, 6, 8];

export function OptimismScatter({
  points,
  slope,
  meanVal,
  meanTest,
}: {
  points: [number, number][];
  slope: number;
  meanVal: number;
  meanTest: number;
}) {
  // The fitted line passes through the means with the given slope.
  const intercept = meanTest - slope * meanVal;
  const fitY = (x: number) => intercept + slope * x;

  return (
    <figure className="m-0">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full"
        role="img"
        aria-label={
          `Diagrama de dispersión de ${points.length} estrategias ganadoras. ` +
          `El eje horizontal es la puntuación con la que fueron elegidas y el vertical ` +
          `la que obtuvieron después. La nube queda muy por debajo de la diagonal: ` +
          `de media se elegían con ${meanVal.toFixed(2)} y obtenían ${meanTest.toFixed(2)}.`
        }
      >
        <defs>
          <clipPath id="optimism-clip">
            <rect
              x={PAD.left}
              y={PAD.top}
              width={W - PAD.left - PAD.right}
              height={H - PAD.top - PAD.bottom}
            />
          </clipPath>
        </defs>

        {TICKS.map((t) => (
          <g key={`grid-${t}`}>
            <line
              x1={sx(t)}
              y1={PAD.top}
              x2={sx(t)}
              y2={H - PAD.bottom}
              stroke={LANDING_CHART.grid}
              strokeWidth={1}
            />
            <line
              x1={PAD.left}
              y1={sy(t)}
              x2={W - PAD.right}
              y2={sy(t)}
              stroke={LANDING_CHART.grid}
              strokeWidth={1}
            />
            <text
              x={sx(t)}
              y={H - PAD.bottom + 16}
              textAnchor="middle"
              fontSize={10}
              fill={LANDING_CHART.axis}
            >
              {t}
            </text>
            <text
              x={PAD.left - 8}
              y={sy(t) + 3.5}
              textAnchor="end"
              fontSize={10}
              fill={LANDING_CHART.axis}
            >
              {t}
            </text>
          </g>
        ))}

        <g clipPath="url(#optimism-clip)">
          {/* Honest line: what an unbiased score would look like. */}
          <line
            x1={sx(LO)}
            y1={sy(LO)}
            x2={sx(HI)}
            y2={sy(HI)}
            stroke={LANDING_CHART.axis}
            strokeWidth={1.6}
            strokeDasharray="6 4"
          />

          {points.map(([v, t], i) => (
            <circle
              key={i}
              cx={sx(v)}
              cy={sy(t)}
              r={2.1}
              fill={LANDING_CHART.accent}
              opacity={0.34}
            />
          ))}

          {/* What actually happened. */}
          <line
            x1={sx(LO)}
            y1={sy(fitY(LO))}
            x2={sx(HI)}
            y2={sy(fitY(HI))}
            stroke="rgb(248 113 113)"
            strokeWidth={2.6}
          />
        </g>

        {/* Zero axes drawn on top so they read as reference, not as data. */}
        <line
          x1={PAD.left}
          y1={sy(0)}
          x2={W - PAD.right}
          y2={sy(0)}
          stroke={LANDING_CHART.axis}
          strokeWidth={1}
          opacity={0.55}
        />

        <text
          x={PAD.left + (W - PAD.left - PAD.right) / 2}
          y={H - 8}
          textAnchor="middle"
          fontSize={11}
          fill={LANDING_CHART.axis}
        >
          Nota con la que fue ELEGIDA
        </text>
        <text
          x={14}
          y={PAD.top + (H - PAD.top - PAD.bottom) / 2}
          textAnchor="middle"
          fontSize={11}
          fill={LANDING_CHART.axis}
          transform={`rotate(-90 14 ${PAD.top + (H - PAD.top - PAD.bottom) / 2})`}
        >
          Nota que SACÓ después
        </text>
      </svg>

      <figcaption className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-muted">
        <span className="flex items-center gap-2">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ background: LANDING_CHART.accent }}
            aria-hidden
          />
          {points.length} estrategias ganadoras
        </span>
        <span className="flex items-center gap-2">
          <svg width="22" height="8" aria-hidden>
            <line
              x1="0"
              y1="4"
              x2="22"
              y2="4"
              stroke={LANDING_CHART.axis}
              strokeWidth="1.6"
              strokeDasharray="5 3"
            />
          </svg>
          Si la nota fuera honesta
        </span>
        <span className="flex items-center gap-2">
          <svg width="22" height="8" aria-hidden>
            <line x1="0" y1="4" x2="22" y2="4" stroke="rgb(248 113 113)" strokeWidth="2.6" />
          </svg>
          Lo que pasó de verdad
        </span>
      </figcaption>
    </figure>
  );
}
