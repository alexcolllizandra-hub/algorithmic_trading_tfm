"use client";

import Link from "next/link";
import { Area, AreaChart, ResponsiveContainer, YAxis } from "recharts";

import { LANDING_CHART } from "@/components/landing/charts/palette";
import { useLandingCopy } from "@/components/landing/copy";
import { Reveal } from "@/components/landing/Reveal";
import { fmtInt } from "@/lib/format";
import { useMarketSeries, useProvenance, useSummary } from "@/lib/site-data";

/** The real BTC price series, dimmed to the point of being texture rather than data. */
function Backdrop() {
  const { data } = useMarketSeries();
  const btc = data?.series.find((entry) => entry.symbol === "BTCUSDT");

  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-0 h-[62%] opacity-[0.55]">
      {btc && (
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={btc.price} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="hero-fill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={LANDING_CHART.accent} stopOpacity={0.16} />
                <stop offset="100%" stopColor={LANDING_CHART.accent} stopOpacity={0} />
              </linearGradient>
            </defs>
            <YAxis scale="log" domain={["auto", "auto"]} hide />
            <Area
              type="monotone"
              dataKey="c"
              stroke={LANDING_CHART.accent}
              strokeOpacity={0.45}
              strokeWidth={1.25}
              fill="url(#hero-fill)"
              isAnimationActive={false}
              dot={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
      <div className="absolute inset-0 bg-gradient-to-t from-bg via-bg/45 to-transparent" />
    </div>
  );
}

function HeroStats() {
  const { data: summary } = useSummary();
  const { data: provenance } = useProvenance();
  const c = useLandingCopy();

  const bars = summary?.items.reduce((total, item) => total + item.bars, 0) ?? null;
  const development = summary?.items.filter((item) => item.partition === "development") ?? [];
  const coverage = development.length
    ? development.reduce((total, item) => total + item.coverage_pct, 0) / development.length
    : null;
  const start = development[0]?.start?.slice(0, 4) ?? null;

  const stats = [
    { value: bars == null ? "—" : fmtInt(bars), label: c.hero.stats.bars },
    { value: start ? `${start}–2026` : "—", label: c.hero.stats.years },
    {
      value: coverage == null ? "—" : `${coverage.toFixed(1)}%`,
      label: c.hero.stats.coverage,
    },
    {
      value: provenance?.holdout_start?.slice(0, 7) ?? "—",
      label: c.hero.stats.holdout,
    },
  ];

  return (
    <dl className="grid grid-cols-2 gap-x-6 gap-y-7 border-t border-border/70 pt-8 md:grid-cols-4">
      {stats.map((stat) => (
        <div key={stat.label}>
          <dt className="sr-only">{stat.label}</dt>
          <dd className="tabular text-2xl font-semibold tracking-tight text-fg md:text-[1.75rem]">
            {stat.value}
          </dd>
          <p className="mt-1 text-sm leading-snug text-muted">{stat.label}</p>
        </div>
      ))}
    </dl>
  );
}

export function Hero() {
  const c = useLandingCopy();

  return (
    <section className="relative isolate overflow-hidden">
      <div className="grid-backdrop pointer-events-none absolute inset-0" aria-hidden />
      <div
        className="pointer-events-none absolute left-1/2 top-[-18rem] h-[36rem] w-[64rem] -translate-x-1/2 rounded-full opacity-[0.14] blur-3xl"
        style={{
          background: `radial-gradient(closest-side, ${LANDING_CHART.accent}, transparent)`,
        }}
        aria-hidden
      />
      <Backdrop />

      <div className="relative mx-auto w-full max-w-6xl px-6 pb-24 pt-20 md:pb-32 md:pt-28">
        <Reveal>
          <p className="rule-label text-accent">{c.hero.kicker}</p>
        </Reveal>

        <Reveal delay={0.05}>
          <h1 className="mt-6 max-w-4xl text-balance text-4xl font-semibold leading-[1.08] tracking-tight md:text-6xl">
            {c.hero.titleA}
            <span className="text-gradient">{c.hero.titleGradient}</span>
            {c.hero.titleB}
          </h1>
        </Reveal>

        <Reveal delay={0.1}>
          <p className="mt-6 max-w-2xl text-pretty text-lg leading-relaxed text-muted md:text-xl">
            {c.hero.sub}
          </p>
        </Reveal>

        <Reveal delay={0.15}>
          <div className="mt-10 flex flex-col gap-3 sm:flex-row sm:items-center">
            <a
              href="#datos"
              className="inline-flex items-center justify-center gap-2 rounded-md bg-accent px-5 py-3 text-sm font-semibold text-accent-fg transition-transform hover:-translate-y-0.5"
            >
              {c.hero.ctaData}
              <span aria-hidden>{"↓"}</span>
            </a>
            <a
              href="#marco"
              className="inline-flex items-center justify-center gap-2 rounded-md border border-border bg-surface/70 px-5 py-3 text-sm font-medium backdrop-blur transition-colors hover:border-accent/50 hover:text-accent"
            >
              {c.hero.ctaPlain}
            </a>
            <Link
              href="/panel"
              className="inline-flex items-center justify-center px-1 py-3 text-sm text-muted transition-colors hover:text-fg sm:px-4"
            >
              {c.hero.ctaPanel} {"→"}
            </Link>
          </div>
        </Reveal>

        <Reveal delay={0.2}>
          <div className="mt-16 md:mt-20">
            <HeroStats />
          </div>
        </Reveal>
      </div>
    </section>
  );
}
