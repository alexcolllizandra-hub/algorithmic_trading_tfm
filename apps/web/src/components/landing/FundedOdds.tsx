"use client";

// Funded-account evaluations, priced honestly: the study's best (rejected)
// strategy against a literal coin flip with the same trade timing and costs,
// under the published rules of two real crypto prop firms. Numbers from
// notebook 07's table; rule sources and retrieval date live in the export.

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { LANDING_CHART } from "@/components/landing/charts/palette";
import { useLandingExtra } from "@/components/landing/charts/extra";
import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";

const FIRM_LABEL: Record<string, string> = {
  breakout_1step_classic: "Breakout (1-step Classic)",
  hyrotrader_2step: "HyroTrader (2-step)",
};

function OddsTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { name?: string; value?: number }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border border-border bg-surface-2 px-3 py-2 text-xs">
      <p className="font-medium">{label}</p>
      {payload.map((entry) => (
        <p key={entry.name} className="tabular mt-0.5 text-muted">
          {entry.name}: {((entry.value ?? 0) * 100).toFixed(1)}%
        </p>
      ))}
    </div>
  );
}

export function FundedOdds() {
  const { data, error } = useLandingExtra();
  if (error) return null;
  const funded = data?.funded;

  const rows =
    funded?.firms.map((firm) => ({
      firm: FIRM_LABEL[firm.id] ?? firm.id,
      estrategia: firm.strategy_phase1,
      moneda: firm.coin_flip_phase1,
      estrategiaAmbas: firm.strategy_both,
      monedaAmbas: firm.coin_flip_both,
    })) ?? [];

  return (
    <Section id="fondeadas">
      <SectionHeading
        eyebrow="Cuentas fondeadas, medidas"
        title="El examen que también aprueba una moneda"
        lead="Aplicamos las reglas publicadas de dos empresas reales de cuentas fondeadas de cripto a mil trayectorias de la mejor estrategia del estudio — que es ruido certificado — y a una moneda al aire con sus mismos tiempos y costes. Ninguna de las dos sabe nada. Las dos aprueban una parte del tiempo."
      />

      <div className="mt-14 grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <Reveal>
          <div className="rounded-card border border-border bg-surface p-6 md:p-7">
            {funded ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
                  <CartesianGrid
                    stroke={LANDING_CHART.grid}
                    strokeDasharray="3 3"
                    vertical={false}
                  />
                  <XAxis dataKey="firm" stroke={LANDING_CHART.axis} tick={{ fontSize: 11 }} />
                  <YAxis
                    stroke={LANDING_CHART.axis}
                    tick={{ fontSize: 11 }}
                    width={44}
                    tickFormatter={(v) => `${(Number(v) * 100).toFixed(0)}%`}
                    domain={[0, 0.25]}
                  />
                  <Tooltip content={<OddsTooltip />} cursor={{ fill: "rgb(255 255 255 / 0.03)" }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar
                    dataKey="estrategia"
                    name="estrategia · pasa fase 1"
                    fill={LANDING_CHART.accent}
                    isAnimationActive={false}
                  />
                  <Bar
                    dataKey="moneda"
                    name="moneda al aire · pasa fase 1"
                    fill={LANDING_CHART.secondary}
                    fillOpacity={0.55}
                    isAnimationActive={false}
                  />
                  <Bar
                    dataKey="estrategiaAmbas"
                    name="estrategia · ambas fases"
                    fill={LANDING_CHART.holdout}
                    isAnimationActive={false}
                  />
                  <Bar
                    dataKey="monedaAmbas"
                    name="moneda · ambas fases"
                    fill={LANDING_CHART.reference}
                    fillOpacity={0.55}
                    isAnimationActive={false}
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] animate-pulse rounded-md bg-surface-2" aria-hidden />
            )}
            <p className="mt-4 text-xs leading-relaxed text-muted">
              {funded
                ? `${funded.n_paths.toLocaleString("es-ES")} trayectorias por brazo. Reglas mapeadas de las páginas públicas de cada firma (fuentes y fecha en el artefacto); las reglas cualitativas no modeladas — consistencia, stop obligatorio, días mínimos — solo harían más difícil aprobar, así que estas cifras son techos optimistas.`
                : ""}
            </p>
          </div>
        </Reveal>

        <Reveal delay={0.06}>
          <div className="flex h-full flex-col justify-center rounded-card border border-border bg-surface p-6 md:p-8">
            <p className="rule-label text-accent">En simple</p>
            <p className="mt-3 text-lg leading-relaxed">
              Aprobar una evaluación de fondeo{" "}
              <strong className="font-semibold">no demuestra que sepas operar.</strong>
            </p>
            <p className="mt-4 leading-relaxed text-muted">
              Una estrategia sin ventaja demostrable supera la fase 1 entre el 14% y el 18% de las
              veces; una moneda con sus mismos costes, entre el 9% y el 13%. La diferencia es del
              tamaño de su propio error de muestreo. Con miles de aspirantes pagando la inscripción,
              el azar fabrica «traders verificados» todas las semanas — y ese es el mecanismo,
              medido, por el que la industria de señales y evaluaciones produce convencidos.
            </p>
            <p className="mt-4 text-sm leading-relaxed text-muted">
              Cambiar las reglas cambia los porcentajes; no cambia de qué lado del azar vive la
              estrategia.
            </p>
          </div>
        </Reveal>
      </div>
    </Section>
  );
}
