"use client";

// Every hypothesis the study tested, drawn together. The chart is the
// denominator made visible: publishing only the best curve and hiding the
// other fourteen is exactly the practice this project exists to counter.

import { useMemo } from "react";
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

import { LANDING_CHART } from "@/components/landing/charts/palette";
import { useLandingExtra } from "@/components/landing/charts/extra";
import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";

function ZooTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { dataKey?: string; value?: number }[];
}) {
  if (!active || !payload?.length) return null;
  const best = [...payload].sort((a, b) => (b.value ?? 0) - (a.value ?? 0));
  return (
    <div className="rounded-md border border-border bg-surface-2 px-3 py-2 text-xs">
      <p className="font-medium">{best.length} familias</p>
      <p className="tabular mt-0.5 text-muted">
        mejor {Number(best[0]?.value).toFixed(2)}× · peor{" "}
        {Number(best[best.length - 1]?.value).toFixed(2)}×
      </p>
    </div>
  );
}

export function FamilyZoo() {
  const { data, error } = useLandingExtra();

  const { rows, stats } = useMemo(() => {
    if (!data) return { rows: [], stats: null };
    const families = data.families;
    const length = Math.max(...families.map((f) => f.curve.length));
    const merged = Array.from({ length }, (_, i) => {
      const row: Record<string, number> = { i };
      for (const f of families) {
        const value = f.curve[Math.min(i, f.curve.length - 1)];
        row[f.family] = value;
      }
      return row;
    });
    const finals = families.map((f) => ({
      family: f.family,
      value: f.curve[f.curve.length - 1],
    }));
    const sorted = [...finals].sort((a, b) => a.value - b.value);
    return {
      rows: merged,
      stats: {
        n: families.length,
        worst: sorted[0],
        best: sorted[sorted.length - 1],
        positive: finals.filter((f) => f.value > 1).length,
      },
    };
  }, [data]);

  if (error) return null;

  return (
    <Section id="familias">
      <SectionHeading
        eyebrow="El denominador, dibujado"
        title="Quince familias, todas a la vista"
        lead="Cada línea es la equity media (diez semillas) de una familia de estrategias sobre BTC fuera de muestra. Publicar solo la mejor y callar las demás es el truco habitual del sector; aquí está el mazo completo, porque el número de intentos es parte del resultado."
      />

      <Reveal>
        <div className="mt-14 rounded-card border border-border bg-surface p-6 md:p-7">
          {data ? (
            <ResponsiveContainer width="100%" height={340}>
              <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 8, left: 4 }}>
                <CartesianGrid stroke={LANDING_CHART.grid} strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="i" hide />
                <YAxis
                  stroke={LANDING_CHART.axis}
                  tick={{ fontSize: 11 }}
                  width={44}
                  tickFormatter={(v) => `${Number(v).toFixed(1)}×`}
                  domain={["auto", "auto"]}
                />
                <Tooltip content={<ZooTooltip />} />
                <ReferenceLine
                  y={1}
                  stroke={LANDING_CHART.reference}
                  strokeDasharray="4 3"
                  label={{
                    value: "punto de partida",
                    position: "insideBottomLeft",
                    fill: LANDING_CHART.axis,
                    fontSize: 10,
                  }}
                />
                {data.families.map((f) => (
                  <Line
                    key={f.family}
                    type="monotone"
                    dataKey={f.family}
                    stroke={LANDING_CHART.secondary}
                    strokeOpacity={0.45}
                    strokeWidth={1.3}
                    dot={false}
                    isAnimationActive={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[340px] animate-pulse rounded-md bg-surface-2" aria-hidden />
          )}
          <p className="mt-4 text-xs leading-relaxed text-muted">
            Ventana walk-forward de test concatenada (2022–2025), motor random_search, media de diez
            semillas por familia. Curvas decimadas para el dibujo; cada punto conserva su valor
            exacto.
          </p>
        </div>
      </Reveal>

      {stats && (
        <Reveal delay={0.05}>
          <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { v: String(stats.n), l: "familias con estudio multi-semilla completo" },
              { v: `${stats.positive}/${stats.n}`, l: "terminan por encima del punto de partida" },
              {
                v: `${stats.best.value.toFixed(2)}×`,
                l: `la mejor curva media (${stats.best.family})`,
              },
              {
                v: `${stats.worst.value.toFixed(2)}×`,
                l: `la peor curva media (${stats.worst.family})`,
              },
            ].map((s) => (
              <div key={s.l} className="rounded-md border border-border bg-surface-2 p-4">
                <p className="tabular text-2xl font-semibold tracking-tight">{s.v}</p>
                <p className="mt-1 text-xs leading-relaxed text-muted">{s.l}</p>
              </div>
            ))}
          </div>
        </Reveal>
      )}

      <Reveal delay={0.1}>
        <p className="mt-8 max-w-3xl leading-relaxed text-muted">
          Que algunas curvas acaben arriba no contradice el veredicto: con quince intentos, el azar
          ya garantiza ganadores aparentes. La pregunta correcta no es «¿cuál subió?» sino «¿sube
          más de lo que subiría por suerte?» — y esa se responde justo debajo.{" "}
          <a href="/estrategias" className="font-medium text-accent hover:underline">
            Explora las quince, semilla a semilla →
          </a>
        </p>
      </Reveal>
    </Section>
  );
}
